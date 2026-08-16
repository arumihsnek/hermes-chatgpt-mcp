from __future__ import annotations

import json
import logging
import os
from urllib.parse import parse_qs, urlencode, urlparse, urlsplit, urlunsplit

from mcp.server.auth.settings import AuthSettings
from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import ToolAnnotations
from starlette.requests import Request
from starlette.middleware.cors import CORSMiddleware
from starlette.routing import request_response
from starlette.responses import HTMLResponse, JSONResponse, RedirectResponse, Response

from .adapter import HermesReadOnlyAdapter, TaskNotFoundError
from .auth import AuthService, BearerTokenVerifier, OAuthError
from .boards import BoardHandle, BoardResolutionError, HermesBoardResolver, SingleBoardResolver
from .command import HermesCreateAdapter
from .config import Settings
from .schemas import (
    ActivityInput,
    ActivityView,
    BoardCapabilities,
    BoardListView,
    BoardQuery,
    BoardSummary,
    BoardView,
    CreateTaskInput,
    CreateTaskResult,
    DispatchView,
    GraphInput,
    TaskDetail,
    TaskGraphView,
    TaskInput,
    TaskListView,
    ListTasksInput,
)

logger = logging.getLogger("hermes_chatgpt_mcp")


def _json_error(error: OAuthError, *, status: int = 400) -> JSONResponse:
    return JSONResponse(
        {"error": error.code, "error_description": str(error)},
        status_code=status,
        headers={"Cache-Control": "no-store"},
    )


async def _bounded_json(request: Request, *, limit: int = 16_000) -> dict:
    content_length = request.headers.get("content-length")
    if content_length and (not content_length.isdigit() or int(content_length) > limit):
        raise OAuthError("request body too large", code="invalid_request")
    body = await request.body()
    if len(body) > limit:
        raise OAuthError("request body too large", code="invalid_request")
    try:
        value = json.loads(body)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise OAuthError("invalid JSON", code="invalid_request") from exc
    if not isinstance(value, dict):
        raise OAuthError("JSON object required", code="invalid_request")
    return value


async def _bounded_form(request: Request, *, limit: int = 16_000) -> dict[str, str]:
    body = await request.body()
    if len(body) > limit:
        raise OAuthError("request body too large", code="invalid_request")
    try:
        values = parse_qs(body.decode("utf-8", errors="strict"), keep_blank_values=True, max_num_fields=32)
    except (UnicodeDecodeError, ValueError) as exc:
        raise OAuthError("invalid form", code="invalid_request") from exc
    return {key: items[0] for key, items in values.items() if items}


def _redirect_with_code(redirect_uri: str, *, code: str, state: str) -> str:
    parsed = urlsplit(redirect_uri)
    query = parse_qs(parsed.query, keep_blank_values=True)
    query["code"] = [code]
    if state:
        query["state"] = [state]
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urlencode(query, doseq=True), ""))


def _strictify_tools(mcp: FastMCP) -> None:
    """Make FastMCP's generated top-level argument models reject extras.

    FastMCP 1.28.1 defaults the generated function-argument model to
    ``extra=ignore``. The nested public Pydantic request models are already
    strict; this pinned-SDK adjustment closes the outer envelope too.
    """
    for tool in mcp._tool_manager._tools.values():  # type: ignore[attr-defined]
        model = tool.fn_metadata.arg_model
        model.model_config["extra"] = "forbid"
        model.model_rebuild(force=True)
        tool.parameters = model.model_json_schema()


def create_app(
    adapter: HermesReadOnlyAdapter | None = None,
    *,
    command_adapter: HermesCreateAdapter | None = None,
    board_resolver: HermesBoardResolver | SingleBoardResolver | None = None,
    settings: Settings | None = None,
    auth_service: AuthService | None = None,
):
    settings = settings or Settings.from_env()
    if board_resolver is None:
        if adapter is not None:
            if command_adapter is None:
                command_adapter = HermesCreateAdapter(adapter.store)
            board_resolver = SingleBoardResolver(adapter, command_adapter, settings)
        else:
            board_resolver = HermesBoardResolver(settings)
    auth_service = auth_service or AuthService(settings)
    auth_settings = AuthSettings(
        issuer_url=settings.public_base_url,
        resource_server_url=settings.public_base_url,
        required_scopes=[AuthService.scope],
    )
    public_host = urlparse(settings.public_base_url).netloc
    public_hostname = urlparse(settings.public_base_url).hostname or ""
    mcp = FastMCP(
        "hermes-chatgpt-mcp",
        instructions=(
            "Hermes Kanban queries plus one explicitly authorized create_task operation. "
            "This server cannot update, delete, dispatch, claim, assign, move, start, complete, "
            "review, approve, reject, retry, import, or sync tasks."
        ),
        token_verifier=BearerTokenVerifier(auth_service),
        auth=auth_settings,
        host=settings.host,
        port=settings.port,
        streamable_http_path="/mcp",
        json_response=True,
        stateless_http=True,
        transport_security=TransportSecuritySettings(
            allowed_hosts=list(dict.fromkeys([public_host, public_hostname, "localhost", "127.0.0.1"]))
        ),
    )
    readonly = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False)
    create_annotations = ToolAnnotations(
        title="Create Hermes task",
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    )

    def tool_error(code: str, message: str) -> ToolError:
        return ToolError(json.dumps({"code": code, "message": message}, separators=(",", ":")))

    def resolve_board(board: str | None, *, operation: str) -> BoardHandle:
        try:
            return board_resolver.resolve(board, operation=operation)  # type: ignore[arg-type]
        except BoardResolutionError as exc:
            raise tool_error(exc.code, exc.message) from exc
        except Exception as exc:
            logger.error("Hermes board resolution failed: %s", type(exc).__name__)
            raise tool_error("BACKEND_ERROR", "Hermes board resolution failed") from exc

    async def run_query(callback, *args, **kwargs):
        try:
            return callback(*args, **kwargs)
        except TaskNotFoundError as exc:
            raise tool_error("TASK_NOT_FOUND", "task was not found on the selected board") from exc
        except (ValueError, FileNotFoundError, LookupError) as exc:
            raise tool_error("BACKEND_ERROR", "invalid or unavailable Hermes query") from exc
        except Exception as exc:  # pragma: no cover - exercised by integration failures
            logger.error("Hermes read query failed: %s", type(exc).__name__)
            raise tool_error("BACKEND_ERROR", "Hermes query failed") from exc

    async def run_command(callback, *args, **kwargs):
        try:
            return callback(*args, **kwargs)
        except (ValueError, FileNotFoundError, LookupError) as exc:
            raise tool_error("CONFLICT", "Hermes rejected the task creation request") from exc
        except Exception as exc:  # pragma: no cover - exercised by integration failures
            logger.error("Hermes create command failed: %s", type(exc).__name__)
            raise tool_error("BACKEND_ERROR", "Hermes task creation failed") from exc

    def require_scope(scope: str) -> None:
        token = get_access_token()
        if token is None or scope not in token.scopes:
            raise tool_error("SCOPE_REQUIRED", f"scope required: {scope}")

    def has_create_scope() -> bool:
        token = get_access_token()
        return token is not None and AuthService.create_scope in token.scopes

    def board_summary(handle: BoardHandle) -> BoardSummary:
        view = board_resolver.query_adapter(handle).get_board()
        return BoardSummary(
            slug=handle.slug,
            name=handle.name,
            description=handle.description,
            project_id=handle.project_id,
            created_at=handle.created_at,
            is_default=handle.is_default,
            task_counts=view.task_counts,
            capabilities=BoardCapabilities(
                read=True,
                create=has_create_scope() and board_resolver.create_allowed(handle.slug),
            ),
        )

    @mcp.tool(
        name="list_boards",
        description="Discover the bounded Hermes boards authorized by this MCP deployment.",
        annotations=readonly,
        structured_output=True,
    )
    async def list_boards() -> BoardListView:
        try:
            items = [board_summary(handle) for handle in board_resolver.list_handles()]
            return BoardListView(items=items, default_board=board_resolver.default_slug)
        except ToolError:
            raise
        except Exception as exc:
            logger.error("Hermes board listing failed: %s", type(exc).__name__)
            raise tool_error("BACKEND_ERROR", "Hermes board listing failed") from exc

    @mcp.tool(
        name="get_board",
        description="Read the configured Hermes Kanban board summary and status counts.",
        annotations=readonly,
        structured_output=True,
    )
    async def get_board(request: BoardQuery) -> BoardView:
        handle = resolve_board(request.board, operation="read")
        return await run_query(board_resolver.query_adapter(handle).get_board)

    @mcp.tool(
        name="list_tasks",
        description="List bounded Hermes tasks using canonical status, assignee, tenant, and session filters.",
        annotations=readonly,
        structured_output=True,
    )
    async def list_tasks(request: ListTasksInput) -> TaskListView:
        handle = resolve_board(request.board, operation="read")
        return await run_query(
            board_resolver.query_adapter(handle).list_tasks,
            assignee=request.assignee,
            status=request.status.value if request.status else None,
            tenant=request.tenant,
            session_id=request.session_id,
            include_archived=request.include_archived,
            limit=request.limit,
            order_by=request.order_by.value,
        )

    @mcp.tool(
        name="get_task",
        description="Read one complete Hermes task/card, its direct graph context, runs, and safe attachment metadata.",
        annotations=readonly,
        structured_output=True,
    )
    async def get_task(request: TaskInput) -> TaskDetail:
        handle = resolve_board(request.board, operation="read")
        return await run_query(board_resolver.query_adapter(handle).get_task, request.task_id)

    @mcp.tool(
        name="get_task_graph",
        description="Read a bounded dependency graph around a Hermes task root.",
        annotations=readonly,
        structured_output=True,
    )
    async def get_task_graph(request: GraphInput) -> TaskGraphView:
        handle = resolve_board(request.board, operation="read")
        return await run_query(
            board_resolver.query_adapter(handle).get_task_graph,
            request.task_id,
            depth=request.depth,
            max_nodes=request.max_nodes,
        )

    @mcp.tool(
        name="get_dispatch",
        description="Read Hermes dispatch eligibility as deterministic READY, BLOCKED, REVIEW, or COMPLETED state with reasons.",
        annotations=readonly,
        structured_output=True,
    )
    async def get_dispatch(request: TaskInput) -> DispatchView:
        handle = resolve_board(request.board, operation="read")
        return await run_query(board_resolver.query_adapter(handle).get_dispatch, request.task_id)

    @mcp.tool(
        name="get_activity",
        description="Read bounded Hermes ledger events, comments, run outcomes, logs, and evidence metadata.",
        annotations=readonly,
        structured_output=True,
    )
    async def get_activity(request: ActivityInput) -> ActivityView:
        handle = resolve_board(request.board, operation="read")
        return await run_query(
            board_resolver.query_adapter(handle).get_activity,
            request.task_id,
            max_items=request.max_items,
            log_bytes=request.log_bytes,
        )

    @mcp.tool(
        name="create_task",
        description=(
            "Create exactly one Hermes Kanban task through Hermes' canonical command path. "
            "This is the only mutating tool and requires hermes:create in addition to hermes:read."
        ),
        annotations=create_annotations,
        structured_output=True,
    )
    async def create_task(request: CreateTaskInput) -> CreateTaskResult:
        require_scope(AuthService.create_scope)
        handle = resolve_board(request.board, operation="create")
        with board_resolver.creation_lock(handle.slug):
            return await run_command(
                board_resolver.command_adapter(handle).create_task,
                title=request.title,
                body=request.body,
                parent_ids=request.parent_ids,
                assignee=request.assignee,
                priority=request.priority,
                tenant=request.tenant,
                session_id=request.session_id,
                triage=request.triage,
                idempotency_key=request.idempotency_key,
            )

    @mcp.custom_route("/healthz", methods=["GET"], include_in_schema=False)
    async def healthz(request: Request) -> Response:
        return JSONResponse({"status": "ok"})

    @mcp.custom_route("/.well-known/oauth-authorization-server", methods=["GET"], include_in_schema=False)
    async def oauth_metadata(request: Request) -> Response:
        base = settings.public_base_url
        return JSONResponse(
            {
                "issuer": base,
                "authorization_endpoint": f"{base}/oauth/authorize",
                "token_endpoint": f"{base}/oauth/token",
                "registration_endpoint": f"{base}/oauth/register",
                "response_types_supported": ["code"],
                "grant_types_supported": ["authorization_code", "refresh_token"],
                "code_challenge_methods_supported": ["S256"],
                "token_endpoint_auth_methods_supported": ["none"],
                "scopes_supported": list(AuthService.supported_scopes),
            },
            headers={"Cache-Control": "public, max-age=300"},
        )

    @mcp.custom_route("/oauth/register", methods=["POST"], include_in_schema=False)
    async def oauth_register(request: Request) -> Response:
        try:
            payload = await _bounded_json(request)
            return JSONResponse(auth_service.register_client(payload), status_code=201, headers={"Cache-Control": "no-store"})
        except OAuthError as exc:
            return _json_error(exc)

    @mcp.custom_route("/oauth/authorize", methods=["GET"], include_in_schema=False)
    async def oauth_authorize_get(request: Request) -> Response:
        query = {key: request.query_params.get(key, "") for key in ("client_id", "redirect_uri", "response_type", "scope", "state", "code_challenge", "code_challenge_method", "resource")}
        try:
            if query["resource"] and query["resource"].rstrip("/") != settings.public_base_url:
                raise OAuthError("invalid resource", code="invalid_target")
            auth_service.validate_authorization_request(
                client_id=query["client_id"],
                redirect_uri=query["redirect_uri"],
                response_type=query["response_type"],
                scope=query["scope"],
                code_challenge=query["code_challenge"],
                code_challenge_method=query["code_challenge_method"],
            )
            return HTMLResponse(auth_service.authorization_form(query=query), headers={"Cache-Control": "no-store"})
        except OAuthError as exc:
            return _json_error(exc)

    @mcp.custom_route("/oauth/authorize", methods=["POST"], include_in_schema=False)
    async def oauth_authorize_post(request: Request) -> Response:
        try:
            form = await _bounded_form(request)
            if not hmac_compare(form.get("username", ""), settings.oauth_username) or not hmac_compare(form.get("password", ""), settings.oauth_password):
                return HTMLResponse("Authorization failed", status_code=401, headers={"Cache-Control": "no-store"})
            if form.get("resource") and form["resource"].rstrip("/") != settings.public_base_url:
                raise OAuthError("invalid resource", code="invalid_target")
            auth_service.validate_authorization_request(
                client_id=form.get("client_id", ""),
                redirect_uri=form.get("redirect_uri", ""),
                response_type=form.get("response_type", ""),
                scope=form.get("scope", ""),
                code_challenge=form.get("code_challenge", ""),
                code_challenge_method=form.get("code_challenge_method", ""),
            )
            code = auth_service.create_authorization_code(
                client_id=form["client_id"],
                redirect_uri=form["redirect_uri"],
                scope=form["scope"],
                code_challenge=form["code_challenge"],
            )
            return RedirectResponse(_redirect_with_code(form["redirect_uri"], code=code, state=form.get("state", "")), status_code=303)
        except OAuthError as exc:
            return _json_error(exc)

    @mcp.custom_route("/oauth/token", methods=["POST"], include_in_schema=False)
    async def oauth_token(request: Request) -> Response:
        try:
            form = await _bounded_form(request)
            grant_type = form.get("grant_type", "")
            if grant_type == "authorization_code":
                result = auth_service.exchange_code_bundle(
                    code=form.get("code", ""),
                    client_id=form.get("client_id", ""),
                    redirect_uri=form.get("redirect_uri", ""),
                    code_verifier=form.get("code_verifier", ""),
                )
            elif grant_type == "refresh_token":
                result = auth_service.refresh_bundle(refresh_token=form.get("refresh_token", ""), client_id=form.get("client_id", ""))
            else:
                raise OAuthError("unsupported grant type", code="unsupported_grant_type")
            return JSONResponse(result, headers={"Cache-Control": "no-store"})
        except OAuthError as exc:
            return _json_error(exc)

    _strictify_tools(mcp)
    app = mcp.streamable_http_app()

    # FastMCP 1.28.1 derives protected-resource ``scopes_supported`` from the
    # resource-wide required scopes. The resource requires hermes:read for
    # every MCP request, while create_task has the additional hermes:create
    # capability. Replace only the generated metadata handler so discovery
    # advertises both without globally requiring the write scope.
    protected_resource_path = "/.well-known/oauth-protected-resource"

    async def protected_resource_metadata(request: Request) -> Response:
        return JSONResponse(
            {
                "resource": settings.public_base_url,
                "authorization_servers": [settings.public_base_url],
                "scopes_supported": list(AuthService.supported_scopes),
                "bearer_methods_supported": ["header"],
            },
            headers={"Cache-Control": "public, max-age=300"},
        )

    for route in app.routes:
        if getattr(route, "path", None) == protected_resource_path:
            route.endpoint = protected_resource_metadata
            route.app = CORSMiddleware(
                request_response(protected_resource_metadata),
                allow_origins=["*"],
                allow_methods=["GET", "OPTIONS"],
                allow_headers=["MCP-Protocol-Version"],
            )
            break
    app.state.hermes_mcp_auth = auth_service
    app.state.hermes_mcp = mcp
    app.state.hermes_mcp_settings = settings
    return app


def hmac_compare(left: str, right: str) -> bool:
    import hmac

    return hmac.compare_digest(left.encode("utf-8"), right.encode("utf-8"))


def main() -> None:
    import uvicorn

    settings = Settings.from_env()
    app = create_app(settings=settings)
    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        log_level=os.environ.get("MCP_LOG_LEVEL", "info").lower(),
    )


if __name__ == "__main__":  # pragma: no cover
    main()
