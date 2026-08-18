from __future__ import annotations

import json
import logging
import os
from typing import Literal
from urllib.parse import parse_qs, urlencode, urlparse, urlsplit, urlunsplit

from mcp.server.auth.settings import AuthSettings
from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import ToolAnnotations
from starlette.requests import Request
from starlette.middleware.cors import CORSMiddleware
from starlette.routing import Route, request_response
from starlette.responses import HTMLResponse, JSONResponse, RedirectResponse, Response

from .adapter import HermesReadOnlyAdapter, TaskNotFoundError
from .auth import BETA_AUTH_POLICY, STABLE_AUTH_POLICY, AuthService, BearerTokenVerifier, OAuthError
from .boards import (
    BoardHandle,
    BoardResolutionError,
    HermesBoardResolver,
    SingleBoardResolver,
    _canonical_board_slug,
)
from .command import HermesCreateAdapter
from .config import Settings
from .diagnostics import emit, fingerprint, redirect_identity, request_fingerprint, scope_summary
from .schemas import (
    AddCommentInput,
    AddCommentResult,
    ActivityInput,
    ActivityView,
    AssignTaskInput,
    AssignTaskResult,
    BetaBoardCapabilities,
    BetaBoardListView,
    BetaBoardSummary,
    BoardCapabilities,
    BoardListView,
    BoardQuery,
    BoardSummary,
    BoardView,
    CreateBoardInput,
    CreateBoardResult,
    CreateTaskInput,
    CreateTaskResult,
    DispatchView,
    GraphInput,
    GlobalCapabilities,
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
    surface: Literal["stable", "beta"] | None = None,
):
    settings = settings or Settings.from_env()
    configured_surface = settings.surface
    if configured_surface not in {"stable", "beta"}:
        raise ValueError("settings.surface must be stable or beta")
    if surface is not None:
        if surface not in {"stable", "beta"}:
            raise ValueError("surface must be stable or beta")
        if surface != configured_surface:
            raise ValueError("surface override must match settings.surface")
    effective_surface = configured_surface if surface is None else surface
    expected_policy = BETA_AUTH_POLICY if effective_surface == "beta" else STABLE_AUTH_POLICY
    auth_service = auth_service or AuthService(settings)
    if auth_service.policy != expected_policy:
        raise ValueError("auth_service policy does not match effective surface")
    beta = effective_surface == "beta"
    if board_resolver is None:
        if adapter is not None:
            if command_adapter is None:
                command_adapter = HermesCreateAdapter(adapter.store)
            board_resolver = SingleBoardResolver(adapter, command_adapter, settings)
        else:
            board_resolver = HermesBoardResolver(settings)
    auth_settings = AuthSettings(
        issuer_url=settings.public_base_url,
        resource_server_url=settings.public_base_url,
        required_scopes=[auth_service.read_scope],
    )
    public_host = urlparse(settings.public_base_url).netloc
    public_hostname = urlparse(settings.public_base_url).hostname or ""
    mcp = FastMCP(
        "hermes-chatgpt-mcp",
        instructions=(
            "Hermes Kanban queries plus explicitly authorized narrow board and card commands."
            if beta
            else (
                "Hermes Kanban queries plus one explicitly authorized create_task operation. "
                "This server cannot update, delete, dispatch, claim, assign, move, start, complete, "
                "review, approve, reject, retry, import, or sync tasks."
            )
        ),
        token_verifier=BearerTokenVerifier(auth_service),
        auth=auth_settings,
        host=settings.host,
        port=settings.port,
        streamable_http_path="/mcp",
        json_response=True,
        stateless_http=False,
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
    board_admin_annotations = ToolAnnotations(
        title="Create Hermes board",
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    )
    manage_annotations = ToolAnnotations(
        title="Manage Hermes card",
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=False,
        openWorldHint=False,
    )

    def tool_error(code: str, message: str) -> ToolError:
        return ToolError(json.dumps({"code": code, "message": message}, separators=(",", ":")))

    def resolve_board(
        board: str | None,
        *,
        operation: Literal["read", "create", "manage"],
    ) -> BoardHandle:
        try:
            if operation in {"create", "manage"}:
                if beta:
                    # Beta surface: card writes are global across all boards;
                    # the requested board (or the default) is used directly.
                    return board_resolver.resolve(board, operation=operation)
                required_scope = (
                    auth_service.create_scope if operation == "create" else auth_service.manage_scope
                )
                granted_board = write_grant_board(required_scope)
                if granted_board is None:
                    raise tool_error(
                        "BOARD_WRITE_SELECTION_REQUIRED",
                        "write access requires one explicitly authorized board",
                    )
                if board is not None and board != granted_board:
                    raise tool_error(
                        "BOARD_SESSION_MISMATCH",
                        "write access is authorized for one different board",
                    )
                board = granted_board
            return board_resolver.resolve(board, operation=operation)
        except ToolError:
            raise
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

    async def run_beta_command(callback, *args, task_command: bool = False, **kwargs):
        try:
            return callback(*args, **kwargs)
        except TaskNotFoundError as exc:
            raise tool_error("TASK_NOT_FOUND", "task was not found on the selected board") from exc
        except ValueError as exc:
            if task_command and str(exc).startswith("unknown task "):
                raise tool_error("TASK_NOT_FOUND", "task was not found on the selected board") from exc
            raise tool_error("CONFLICT", "Hermes rejected the command request") from exc
        except RuntimeError as exc:
            if task_command and "currently running (claimed)" in str(exc):
                raise tool_error("CONFLICT", "Hermes rejected the command request") from exc
            logger.error("Hermes beta command failed: %s", type(exc).__name__)
            raise tool_error("BACKEND_ERROR", "Hermes command failed") from exc
        except (FileNotFoundError, LookupError) as exc:
            raise tool_error("CONFLICT", "Hermes rejected the command request") from exc
        except Exception as exc:  # pragma: no cover - exercised by integration failures
            logger.error("Hermes beta command failed: %s", type(exc).__name__)
            raise tool_error("BACKEND_ERROR", "Hermes command failed") from exc

    def require_scope(scope: str) -> None:
        token = get_access_token()
        if token is None or scope not in token.scopes:
            raise tool_error("SCOPE_REQUIRED", f"scope required: {scope}")

    def has_admin_scope() -> bool:
        """True when the token carries the global hermes:board:create scope."""
        token = get_access_token()
        return token is not None and auth_service.board_create_scope in token.scopes

    def has_command_scope(scope: str, board: str | None = None) -> bool:
        token = get_access_token()
        if token is None or scope not in token.scopes:
            return False
        if board is None or beta or has_admin_scope():
            # Betas allows card writes on ANY board (global); a stable token is
            # confined to its single granted board.
            return True
        return write_grant_board(scope) == board

    def write_grant_board(required_scope: str | None = None) -> str | None:
        token = get_access_token()
        if token is None or (required_scope is not None and required_scope not in token.scopes):
            return None
        claims = auth_service.verified_claims(token.token) or {}
        board = claims.get("board")
        if claims.get("board_access") != "write" or not isinstance(board, str):
            return None
        return board

    def board_summary(handle: BoardHandle, *, beta: bool) -> BoardSummary | BetaBoardSummary:
        view = board_resolver.query_adapter(handle).get_board()
        can_create = (
            has_command_scope(auth_service.create_scope, handle.slug)
            and board_resolver.create_allowed(handle.slug)
        )
        if beta:
            return BetaBoardSummary(
                slug=handle.slug,
                name=handle.name,
                description=handle.description,
                project_id=handle.project_id,
                created_at=handle.created_at,
                is_default=handle.is_default,
                task_counts=view.task_counts,
                capabilities=BetaBoardCapabilities(
                    read=True,
                    create=can_create,
                    manage=has_command_scope(auth_service.manage_scope, handle.slug),
                ),
            )
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
                create=can_create,
            ),
        )

    def list_board_items() -> tuple[list[BoardSummary | BetaBoardSummary], str]:
        items = [board_summary(handle, beta=beta) for handle in board_resolver.list_handles()]
        default_board = (
            board_resolver.current_default_slug()
            if isinstance(board_resolver, HermesBoardResolver)
            else board_resolver.default_slug
        )
        return items, default_board

    if beta:
        @mcp.tool(
            name="list_boards",
            description="Discover bounded Hermes boards and beta command capabilities.",
            annotations=readonly,
            structured_output=True,
        )
        async def list_boards() -> BetaBoardListView:
            try:
                items, default_board = list_board_items()
                return BetaBoardListView(
                    items=items,  # type: ignore[arg-type]
                    default_board=default_board,
                    global_capabilities=GlobalCapabilities(
                        create_board=(
                            settings.board_create_enabled
                            and has_command_scope(auth_service.board_create_scope)
                        )
                    ),
                )
            except ToolError:
                raise
            except Exception as exc:
                logger.error("Hermes board listing failed: %s", type(exc).__name__)
                raise tool_error("BACKEND_ERROR", "Hermes board listing failed") from exc
    else:
        @mcp.tool(
            name="list_boards",
            description="Discover the bounded Hermes boards authorized by this MCP deployment.",
            annotations=readonly,
            structured_output=True,
        )
        async def list_boards() -> BoardListView:
            try:
                items, default_board = list_board_items()
                return BoardListView(items=items, default_board=default_board)  # type: ignore[arg-type]
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
        view = await run_query(board_resolver.query_adapter(handle).get_board)
        can_create = (
            has_command_scope(auth_service.create_scope, handle.slug)
            and board_resolver.create_allowed(handle.slug)
        )
        view.capabilities = BetaBoardCapabilities(
            read=True,
            create=can_create,
            manage=(
                has_command_scope(auth_service.manage_scope, handle.slug)
                if beta
                else False
            ),
        )
        return view

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
            + (
                "This is the only mutating tool on the stable surface and requires "
                "hermes:create in addition to hermes:read."
                if not beta
                else "This beta command requires hermes:create in addition to hermes:read."
            )
        ),
        annotations=create_annotations,
        structured_output=True,
    )
    async def create_task(request: CreateTaskInput) -> CreateTaskResult:
        require_scope(auth_service.create_scope)
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

    if beta:
        @mcp.tool(
            name="create_board",
            description="Create one canonical Hermes board; requires hermes:board:create.",
            annotations=board_admin_annotations,
            structured_output=True,
        )
        async def create_board(request: CreateBoardInput) -> CreateBoardResult:
            require_scope(auth_service.board_create_scope)
            if not settings.board_create_enabled:
                raise tool_error("BOARD_CREATE_DISABLED", "board creation is disabled")
            try:
                canonical_slug = _canonical_board_slug(request.slug)
            except ValueError as exc:
                raise tool_error("CONFLICT", "invalid board slug") from exc
            with board_resolver.creation_lock(canonical_slug):
                return await run_beta_command(
                    board_resolver.board_admin_adapter().create_board,
                    canonical_slug,
                    name=request.name,
                    description=request.description,
                    icon=request.icon,
                    color=request.color,
                )

        @mcp.tool(
            name="add_comment",
            description="Add one provenance-bound task comment; requires hermes:manage.",
            annotations=manage_annotations,
            structured_output=True,
        )
        async def add_comment(request: AddCommentInput) -> AddCommentResult:
            require_scope(auth_service.manage_scope)
            handle = resolve_board(request.board, operation="manage")
            return await run_beta_command(
                board_resolver.management_adapter(handle).add_comment,
                request.task_id,
                request.body,
                task_command=True,
            )

        @mcp.tool(
            name="assign_task",
            description="Assign one task through Hermes; requires hermes:manage.",
            annotations=manage_annotations,
            structured_output=True,
        )
        async def assign_task(request: AssignTaskInput) -> AssignTaskResult:
            require_scope(auth_service.manage_scope)
            handle = resolve_board(request.board, operation="manage")
            return await run_beta_command(
                board_resolver.management_adapter(handle).assign_task,
                request.task_id,
                request.assignee,
                task_command=True,
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
                "revocation_endpoint": f"{base}/oauth/revoke",
                "registration_endpoint": f"{base}/oauth/register",
                "response_types_supported": ["code"],
                "grant_types_supported": ["authorization_code", "refresh_token"],
                "code_challenge_methods_supported": ["S256"],
                "token_endpoint_auth_methods_supported": ["none"],
                "scopes_supported": list(auth_service.supported_scopes),
            },
            headers={"Cache-Control": "public, max-age=300"},
        )

    @mcp.custom_route("/oauth/register", methods=["POST"], include_in_schema=False)
    async def oauth_register(request: Request) -> Response:
        try:
            payload = await _bounded_json(request)
            redirect_uris = payload.get("redirect_uris") if isinstance(payload, dict) else None
            redirect = redirect_identity(redirect_uris[0]) if isinstance(redirect_uris, list) and redirect_uris else None
            emit(
                settings,
                "dcr.request",
                requested_scopes=payload.get("scope") if isinstance(payload, dict) else None,
                redirect=redirect,
                grant_types=",".join(str(value) for value in (payload.get("grant_types") or [])) if isinstance(payload, dict) else None,
                outcome="received",
            )
            result = auth_service.register_client(payload)
            emit(
                settings,
                "dcr.response",
                client_fp=fingerprint(result["client_id"]),
                granted_scopes=result.get("scope"),
                redirect=redirect_identity(result["redirect_uris"][0]),
                grant_types=",".join(result.get("grant_types", [])),
                new_registration=True,
                client_reused=False,
                http_status=201,
                outcome="success",
            )
            return JSONResponse(result, status_code=201, headers={"Cache-Control": "no-store"})
        except OAuthError as exc:
            emit(settings, "dcr.response", error_code=exc.code, http_status=400, outcome="error")
            return _json_error(exc)

    @mcp.custom_route("/oauth/authorize", methods=["GET"], include_in_schema=False)
    async def oauth_authorize_get(request: Request) -> Response:
        query = {key: request.query_params.get(key, "") for key in ("client_id", "redirect_uri", "response_type", "scope", "state", "code_challenge", "code_challenge_method", "resource")}
        flow_fp = request_fingerprint(query["client_id"], query["redirect_uri"], query["scope"], query["code_challenge"])
        emit(
            settings,
            "authorize.request",
            client_fp=fingerprint(query["client_id"]),
            flow_fp=flow_fp,
            requested_scopes=query["scope"],
            redirect=redirect_identity(query["redirect_uri"]),
            response_type=query["response_type"],
            code_challenge_method=query["code_challenge_method"],
            resource=redirect_identity(query["resource"]),
            outcome="received",
        )
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
            client = auth_service.client(query["client_id"])
            form_query = dict(query)
            form_query["scope"] = query["scope"] or client.scope
            options = [
                {"slug": handle.slug, "name": handle.name}
                for handle in board_resolver.list_handles()
            ]
            emit(settings, "authorize.request", flow_fp=flow_fp, http_status=200, outcome="accepted")
            default_board = (
                board_resolver.current_default_slug()
                if isinstance(board_resolver, HermesBoardResolver)
                else board_resolver.default_slug
            )
            return HTMLResponse(
                auth_service.authorization_form(
                    query=form_query,
                    board_options=options,
                    default_board=default_board,
                ),
                headers={"Cache-Control": "no-store"},
            )
        except OAuthError as exc:
            emit(settings, "authorize.request", flow_fp=flow_fp, error_code=exc.code, http_status=400, outcome="error")
            return _json_error(exc)

    @mcp.custom_route("/oauth/authorize", methods=["POST"], include_in_schema=False)
    async def oauth_authorize_post(request: Request) -> Response:
        try:
            form = await _bounded_form(request)
            if not hmac_compare(form.get("username", ""), settings.oauth_username) or not hmac_compare(form.get("password", ""), settings.oauth_password):
                return HTMLResponse("Authorization failed", status_code=401, headers={"Cache-Control": "no-store"})
            flow_fp = request_fingerprint(form.get("client_id", ""), form.get("redirect_uri", ""), form.get("scope", ""), form.get("code_challenge", ""))
            emit(
                settings,
                "authorize.consent",
                client_fp=fingerprint(form.get("client_id", "")),
                flow_fp=flow_fp,
                requested_scopes=form.get("scope"),
                redirect=redirect_identity(form.get("redirect_uri", "")),
                response_type=form.get("response_type", ""),
                code_challenge_method=form.get("code_challenge_method", ""),
                resource=redirect_identity(form.get("resource", "")),
                outcome="credentials_accepted",
            )
            if form.get("resource") and form["resource"].rstrip("/") != settings.public_base_url:
                raise OAuthError("invalid resource", code="invalid_target")
            client = auth_service.validate_authorization_request(
                client_id=form.get("client_id", ""),
                redirect_uri=form.get("redirect_uri", ""),
                response_type=form.get("response_type", ""),
                scope=form.get("scope", ""),
                code_challenge=form.get("code_challenge", ""),
                code_challenge_method=form.get("code_challenge_method", ""),
            )
            requested_scope = form.get("scope") or client.scope
            extra_scope_values: list[str] = []
            for name in ("scope_extra_manage", "scope_extra_admin"):
                value = form.get(name)
                if value:
                    extra_scope_values.append(value)
            if extra_scope_values:
                # Widen the grant with scopes the resource owner explicitly
                # ticked at consent time (narrow clients like ChatGPT only
                # register with read+create; the human may grant more).
                requested_scope = auth_service._scope_string(
                    " ".join([requested_scope, *extra_scope_values]),
                    allowed=set(auth_service.supported_scopes),
                )
            requested_set = set(requested_scope.split())
            access_mode = form.get("access_mode", "read")
            selected_board: str | None = None
            write_grant = False
            command_scopes = {
                auth_service.create_scope,
                *({auth_service.manage_scope} if beta else set()),
            }
            admin_scope = auth_service.board_create_scope
            wants_admin = admin_scope in requested_set
            if wants_admin:
                # One admin consent can carry read + hermes:board:create plus any
                # requested command scopes (hermes:create / hermes:manage). Card
                # writes become global (no single-board claim), so a single admin
                # token can create a board and immediately work on it.
                requested_scope = " ".join(
                    scope for scope in auth_service.supported_scopes if scope in requested_set
                )
            elif access_mode == "write":
                if not command_scopes.intersection(requested_scope.split()):
                    raise OAuthError(
                        (
                            "client did not request a board command scope; re-register the MCP client"
                            if beta
                            else "client did not request hermes:create; re-register the MCP client"
                        ),
                        code="invalid_scope",
                    )
                selected_board = form.get("board") or None
                try:
                    board_resolver.resolve(selected_board, operation="read")
                except BoardResolutionError as exc:
                    raise OAuthError("invalid board selection", code="invalid_request") from exc
                write_grant = True
            elif access_mode == "read":
                requested_scope = " ".join(
                    scope for scope in auth_service.supported_scopes
                    if scope in requested_scope.split() and scope not in command_scopes
                )
            else:
                raise OAuthError("invalid access mode", code="invalid_request")
            code = auth_service.create_authorization_code(
                client_id=form["client_id"],
                redirect_uri=form["redirect_uri"],
                scope=requested_scope,
                code_challenge=form["code_challenge"],
                board=selected_board,
                write_grant=write_grant,
            )
            emit(
                settings,
                "authorize.response",
                client_fp=fingerprint(form["client_id"]),
                flow_fp=flow_fp,
                code_fp=fingerprint(code),
                granted_scopes=requested_scope,
                board=selected_board,
                board_access="write" if write_grant else None,
                redirect=redirect_identity(form["redirect_uri"]),
                http_status=303,
                outcome="approved",
            )
            return RedirectResponse(_redirect_with_code(form["redirect_uri"], code=code, state=form.get("state", "")), status_code=303)
        except OAuthError as exc:
            emit(settings, "authorize.response", error_code=exc.code, http_status=400, outcome="error")
            return _json_error(exc)

    @mcp.custom_route("/oauth/token", methods=["POST"], include_in_schema=False)
    async def oauth_token(request: Request) -> Response:
        form: dict[str, str] = {}
        try:
            form = await _bounded_form(request)
            grant_type = form.get("grant_type", "")
            emit(
                settings,
                "token.request",
                client_fp=fingerprint(form.get("client_id", "")),
                code_fp=fingerprint(form.get("code", "")) if grant_type == "authorization_code" else None,
                refresh_fp=fingerprint(form.get("refresh_token", "")) if grant_type == "refresh_token" else None,
                requested_scopes=form.get("scope"),
                grant_type=grant_type,
                outcome="received",
            )
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
            emit(
                settings,
                "token.response",
                client_fp=fingerprint(form.get("client_id", "")),
                code_fp=fingerprint(form.get("code", "")) if grant_type == "authorization_code" else None,
                refresh_fp=fingerprint(form.get("refresh_token", "")) if grant_type == "refresh_token" else None,
                token_fp=fingerprint(result.get("access_token", "")),
                new_refresh_fp=fingerprint(result["refresh_token"]) if result.get("refresh_token") else None,
                granted_scopes=result.get("scope"),
                effective_scopes=result.get("scope"),
                grant_type=grant_type,
                http_status=200,
                outcome="success",
            )
            return JSONResponse(result, headers={"Cache-Control": "no-store"})
        except OAuthError as exc:
            emit(
                settings,
                "token.response",
                client_fp=fingerprint(form.get("client_id", "")) if form else None,
                code_fp=fingerprint(form.get("code", "")) if form.get("code") else None,
                refresh_fp=fingerprint(form.get("refresh_token", "")) if form.get("refresh_token") else None,
                grant_type=form.get("grant_type", "") if form else None,
                error_code=exc.code,
                http_status=400,
                outcome="error",
            )
            return _json_error(exc)

    @mcp.custom_route("/oauth/revoke", methods=["POST"], include_in_schema=False)
    async def oauth_revoke(request: Request) -> Response:
        form: dict[str, str] = {}
        try:
            form = await _bounded_form(request)
            auth_service.revoke_token(
                form.get("token", ""),
                client_id=form.get("client_id") or None,
            )
            return Response(status_code=200, headers={"Cache-Control": "no-store"})
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
                "scopes_supported": list(auth_service.supported_scopes),
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

    # ChatGPT connectors use the declared server URL (the root, which is also
    # the OAuth issuer/resource) as the streamable HTTP session endpoint after
    # OAuth. Alias the root so the same transport serves POST / and POST /mcp;
    # GET / keeps its non-MCP purpose. /mcp remains the canonical path.
    mcp_route = next(
        (route for route in app.routes if getattr(route, "path", None) == "/mcp"),
        None,
    )
    if mcp_route is not None:
        app.routes.append(Route("/", endpoint=mcp_route.endpoint, methods=["POST"]))

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
        access_log=False,
    )


if __name__ == "__main__":  # pragma: no cover
    main()
