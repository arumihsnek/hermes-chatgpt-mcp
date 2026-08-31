from __future__ import annotations

import json
import hashlib
import logging
import os
import time
from typing import Literal
from urllib.parse import parse_qs, urlencode, urlparse, urlsplit, urlunsplit

from mcp.server.auth.settings import AuthSettings
from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import ToolAnnotations
from starlette.requests import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.routing import Route, request_response
from starlette.responses import HTMLResponse, JSONResponse, RedirectResponse, Response

from .adapter import HermesReadOnlyAdapter, RunNotFoundError, TaskNotFoundError
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
from .provenance import API_VERSION, get_candidate_provenance
from .release import load_build_metadata
from .human_gate_ui import build_human_gate_ui_html
from .ui_mutation import UiMutationAdapter, UiMutationError
from .ui_write_contract import UiCapabilityIssuer
from .ui import (
    HUMAN_GATE_RESOURCE_URI,
    KANBAN_UI_MIME_TYPE,
    KANBAN_UI_MAX_BYTES,
    KANBAN_UI_RESOURCE_URI,
    KANBAN_UI_RESOURCE_URI_V2,
    KANBAN_UI_RESOURCE_URI_INTERACTIVE_R1,
    KANBAN_UI_RESOURCE_URI_INTERACTIVE_R14,
    KANBAN_UI_RESOURCE_URI_INTERACTIVE_R16,
    KANBAN_UI_RESOURCE_URI_INTERACTIVE_R162,
    build_kanban_ui_html,
    build_kanban_ui_v2_html,
    build_kanban_ui_interactive_r1_html,
)


def _build_primary_kanban_ui(*, interactive: bool) -> str:
    """Return the UI served at the original cache-stable Kanban resource URI.

    Existing ChatGPT connector sessions can retain the original get_board ->
    resource URI binding.  Keeping the primary URI mode-aware lets those
    sessions receive Interactive R1 without requiring connector rediscovery.
    """
    return build_kanban_ui_interactive_r1_html() if interactive else build_kanban_ui_html()


def _widget_resource_meta(*, public_base_url: str, version: str) -> dict[str, object]:
    """Return MCP Apps template metadata required by ChatGPT.

    The Kanban widgets are self-contained: they use the MCP Apps postMessage
    bridge for tool calls and load no external scripts, styles, images, frames,
    or fetch/XHR endpoints.  Therefore both CSP allowlists are intentionally
    empty.  The widget domain is the deployment's own HTTPS origin so stable
    and canary remain isolated without hard-coding either environment.
    """
    parsed = urlparse(public_base_url)
    domain = f"{parsed.scheme}://{parsed.netloc}"
    return {
        "ui": {
            "domain": domain,
            "csp": {
                "connectDomains": [],
                "resourceDomains": [],
            },
        },
        "version": version,
    }


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
    DiagnosticsInput,
    DiagnosticsResult,
    LinkTasksInput,
    UnlinkTasksInput,
    SetModelInput,
    ReclaimInput,
    ReassignInput,
    CompleteInput,
    EditTaskInput,
    UpdateTaskInput,
    SoftRetireEdgeInput,
    BlockInput,
    ScheduleInput,
    UnblockInput,
    RequestReviewInput,
    RequestChangesInput,
    ReopenReviewInput,
    PromoteInput,
    ArchiveInput,
    LinkTasksResult,
    UnlinkTasksResult,
    SetModelResult,
    ReclaimResult,
    ReassignResult,
    CompleteResult,
    EditTaskResult,
    UpdateTaskResult,
    SoftRetireEdgeResult,
    BlockResult,
    ScheduleResult,
    UnblockResult,
    RequestReviewResult,
    RequestChangesResult,
    ReopenReviewResult,
    PromoteResult,
    ArchiveResult,
    AttachmentsInput,
    AttachmentsResult,
    AttachmentInfo,
    RemoveBoardInput,
    RemoveBoardResult,
    SwitchBoardInput,
    SwitchBoardResult,
    RenameBoardInput,
    RenameBoardResult,
    SetDefaultWorkdirInput,
    SetDefaultWorkdirResult,
    StatsResult,
    NotifySubscribeInput,
    NotifySubscribeResult,
    NotifyListInput,
    NotifyListResult,
    NotifySubscriptionInfo,
    NotifyUnsubscribeInput,
    NotifyUnsubscribeResult,
    ContextInput,
    ContextResult,
    SpecifyInput,
    SpecifyResult,
    DecomposeInput,
    DecomposeResult,
    GcResult,
    GcInput,
    RepairResult,
    TaskLogInput,
    TaskLogResult,
    TaskRunsInput,
    TaskRunsResult,
    HeartbeatInput,
    HeartbeatResult,
    AssigneesInput,
    AssigneesResult,
    TailInput,
    WatchInput,
    CanonicalActionResult,
    InitInput,
    SwarmInput,
    ClaimInput,
    AttachInput,
    DispatchInput,
    StreamInput,
    BoardAdminInput,
    AttachRemoveInput,
    HumanGateInput,
    HumanGateView,
    HumanGateDecisionInput,
    HumanGateDecisionResult,
    CanaryInput,
    CanaryResult,
    ControlStatusInput,
    ControlStatusResult,
    InitResult,
    SwarmResult,
    DaemonResult,
    DaemonInput,
    WatchResult,
    GetRunInput,
    ListRunsInput,
    ActiveWorkersInput,
    BoundedLogInput,
    RuntimeStatusInput,
    TaskRunsResult,
    ActiveWorkersResult,
    TaskLogResult,
    RuntimeStatusResult,
    TaskRunRecord,
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


def _session_fingerprint(value: str | None) -> str | None:
    """Return a stable, non-reversible correlation value for an MCP session."""
    if not value:
        return None
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


class _McpObservabilityMiddleware(BaseHTTPMiddleware):
    """Log transport facts without recording credentials or request content."""

    async def dispatch(self, request: Request, call_next):
        if request.url.path != "/mcp" or request.method != "POST":
            return await call_next(request)
        response = await call_next(request)
        logger.info(
            "mcp_transport request_path=%s protocol_version=%s session_fp=%s status=%s",
            request.url.path,
            request.headers.get("mcp-protocol-version", ""),
            _session_fingerprint(request.headers.get("mcp-session-id")),
            response.status_code,
        )
        return response


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
    if settings.chatgpt_compat_mode and effective_surface != "beta":
        raise ValueError("MCP_CHATGPT_COMPAT_MODE requires MCP_SURFACE=beta")
    build_metadata = load_build_metadata(settings.build_metadata_file)
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
                required_scope = auth_service.create_scope if operation == "create" else auth_service.manage_scope
                if beta and not has_admin_scope():
                    granted_board = write_grant_board(required_scope)
                    if granted_board is None:
                        raise tool_error("BOARD_WRITE_SELECTION_REQUIRED", "write access requires one explicitly authorized board")
                    if board is not None and _canonical_board_slug(board) != granted_board:
                        raise tool_error("BOARD_SESSION_MISMATCH", "write access is authorized for one different board")
                    board = granted_board
                elif not beta:
                    granted_board = write_grant_board(required_scope)
                    if granted_board is None:
                        raise tool_error("BOARD_WRITE_SELECTION_REQUIRED", "write access requires one explicitly authorized board")
                    if board is not None and _canonical_board_slug(board) != granted_board:
                        raise tool_error("BOARD_SESSION_MISMATCH", "write access is authorized for one different board")
                    board = granted_board
                return board_resolver.resolve(board, operation=operation)
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
        except RunNotFoundError as exc:
            raise tool_error("RUN_NOT_FOUND", "run was not found on the selected board") from exc
        except (ValueError, FileNotFoundError, LookupError) as exc:
            raise tool_error("BACKEND_ERROR", "invalid or unavailable Hermes query") from exc
        except Exception as exc:  # pragma: no cover - exercised by integration failures
            logger.error("Hermes read query failed: %s", type(exc).__name__)
            raise tool_error("BACKEND_ERROR", "Hermes query failed") from exc

    async def run_command(callback, *args, **kwargs):
        try:
            return callback(*args, **kwargs)
        except (ValueError, FileNotFoundError, LookupError) as exc:
            raise tool_error("CONFLICT", str(exc)) from exc
        except Exception as exc:  # pragma: no cover - exercised by integration failures
            logger.error("Hermes create command failed: %s", type(exc).__name__)
            raise tool_error("BACKEND_ERROR", "Hermes task creation failed") from exc

    async def run_beta_command(callback, *args, task_command: bool = False, **kwargs):
        try:
            return callback(*args, **kwargs)
        except BoardResolutionError as exc:
            raise tool_error(exc.code, exc.message) from exc
        except TaskNotFoundError as exc:
            raise tool_error("TASK_NOT_FOUND", "task was not found on the selected board") from exc
        except ValueError as exc:
            message = str(exc)
            if task_command and message.startswith("unknown task "):
                raise tool_error("TASK_NOT_FOUND", "task was not found on the selected board") from exc
            if "base64" in message:
                code = "INVALID_BASE64"
            elif "hash mismatch" in message:
                code = "HASH_MISMATCH"
            elif "unsupported hash" in message:
                code = "UNSUPPORTED_TRANSPORT"
            elif "exceeds" in message:
                code = "ATTACHMENT_TOO_LARGE"
            elif "MIME" in message:
                code = "MIME_MISMATCH"
            elif "path is outside" in message or "filename" in message:
                code = "UNSAFE_ATTACHMENT_FILENAME"
            else:
                code = "CONFLICT"
            raise tool_error(code, message) from exc
        except RuntimeError as exc:
            if task_command and "currently running (claimed)" in str(exc):
                raise tool_error("CONFLICT", "Hermes rejected the command request") from exc
            logger.error("Hermes beta command failed: %s", type(exc).__name__)
            raise tool_error("BACKEND_ERROR", "Hermes command failed") from exc
        except (FileNotFoundError, LookupError) as exc:
            if isinstance(exc, LookupError) and "unknown task" in str(exc).lower():
                raise tool_error("TASK_NOT_FOUND", str(exc)) from exc
            raise tool_error("CONFLICT", "Hermes rejected the command request") from exc
        except Exception as exc:  # pragma: no cover - exercised by integration failures
            logger.error("Hermes beta command failed: %s", type(exc).__name__)
            raise tool_error("BACKEND_ERROR", "Hermes command failed") from exc

    def require_scope(scope: str) -> None:
        token = get_access_token()
        if token is None or scope not in token.scopes:
            raise tool_error("SCOPE_REQUIRED", f"scope required: {scope}")

    def has_admin_scope() -> bool:
        """True when the token carries the separately consented admin scope."""
        token = get_access_token()
        return token is not None and auth_service.admin_scope in token.scopes

    def has_command_scope(scope: str, board: str | None = None) -> bool:
        token = get_access_token()
        if token is None or scope not in token.scopes:
            return False
        if board is None:
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
        meta={"ui": {"resourceUri": (KANBAN_UI_RESOURCE_URI_INTERACTIVE_R1 if settings.ui_interactive_r1 else KANBAN_UI_RESOURCE_URI)}},
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

    if settings.ui_interactive_r1:
        @mcp.tool(
            name="get_board_interactive_r14",
            description="Read the configured Hermes Kanban board and render the fresh Interactive R1.1 MCP App binding.",
            annotations=readonly,
            structured_output=True,
            meta={"ui": {"resourceUri": KANBAN_UI_RESOURCE_URI_INTERACTIVE_R14}, "ui_version": "interactive-r1.1-r14"},
        )
        async def get_board_interactive_r14(request: BoardQuery) -> BoardView:
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
            name="get_board_interactive_r16",
            description="Render the R1.6 interactive Hermes Kanban board with staged drag/drop and modal card management.",
            annotations=readonly,
            structured_output=True,
            meta={"ui": {"resourceUri": KANBAN_UI_RESOURCE_URI_INTERACTIVE_R16}, "ui_version": "interactive-r1.6-r16"},
        )
        async def get_board_interactive_r16(request: BoardQuery) -> BoardView:
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
            name="get_board_interactive_r162",
            description="Render the R1.6.2 mobile workbench with staged touch drag, persistent multi-selection, and mobile inspector.",
            annotations=readonly,
            structured_output=True,
            meta={"ui": {"resourceUri": KANBAN_UI_RESOURCE_URI_INTERACTIVE_R162}, "ui_version": "interactive-r1.6.2-r162"},
        )
        async def get_board_interactive_r162(request: BoardQuery) -> BoardView:
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
        name="get_run",
        description="Read one bounded canonical Hermes run by Run.id.",
        annotations=readonly,
        structured_output=True,
    )
    async def get_run(request: GetRunInput) -> TaskRunRecord:
        handle = resolve_board(request.board, operation="read")
        return await run_query(board_resolver.query_adapter(handle).get_run, request.run_id)

    @mcp.tool(
        name="list_runs",
        description="Read bounded chronological run history for one task.",
        annotations=readonly,
        structured_output=True,
    )
    async def list_runs(request: ListRunsInput) -> TaskRunsResult:
        handle = resolve_board(request.board, operation="read")
        return await run_query(board_resolver.query_adapter(handle).list_runs, request.task_id, limit=request.limit, include_active=request.include_active)

    if beta:
        @mcp.tool(
            name="active_workers",
            description="Read a bounded snapshot of currently running workers and run linkage.",
            annotations=readonly,
            structured_output=True,
        )
        async def active_workers(request: ActiveWorkersInput) -> ActiveWorkersResult:
            handle = resolve_board(request.board, operation="read")
            return await run_query(board_resolver.query_adapter(handle).active_workers, limit=request.limit)

        @mcp.tool(
            name="bounded_log",
            description="Read a bounded worker-log tail; never streams or exposes unbounded logs.",
            annotations=readonly,
            structured_output=True,
        )
        async def bounded_log(request: BoundedLogInput) -> TaskLogResult:
            handle = resolve_board(request.board, operation="read")
            return await run_query(board_resolver.query_adapter(handle).read_bounded_log, request.task_id, tail_bytes=request.tail_bytes, cursor=request.cursor)

        @mcp.tool(
            name="runtime_status",
            description="Read bounded board and host runtime status with configuration-safe daemon snapshot.",
            annotations=readonly,
            structured_output=True,
        )
        async def runtime_status(request: RuntimeStatusInput) -> RuntimeStatusResult:
            handle = resolve_board(request.board, operation="read")
            return await run_query(board_resolver.query_adapter(handle).runtime_status)

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
        from .probe_mode import enforce_probe_safe

        enforce_probe_safe(request, "create_task")
        with board_resolver.creation_lock(handle.slug):
            if settings.ui_write_enabled_v2:
                token = get_access_token()
                subject = token.subject if token is not None and token.subject else "mcp-client"
                capability = UiCapabilityIssuer().issue(
                    subject=subject, board=handle.slug, tenant=request.tenant or "default"
                )
                try:
                    result = UiMutationAdapter(
                        board_resolver.query_adapter(handle).store, capability
                    ).create_task(
                        title=request.title,
                        body=request.body,
                        parent_ids=request.parent_ids,
                        expected_board_revision=request.expected_board_revision,
                        idempotency_key=request.idempotency_key,
                    )
                except UiMutationError as exc:
                    raise tool_error(exc.code, str(exc)) from exc
                return CreateTaskResult(
                    created=result.mutation_status == "created",
                    idempotent_replay=result.mutation_status == "idempotent_replay",
                    task_id=result.canonical_task_id,
                    board=result.board,
                    title=request.title,
                    status="running",
                    tenant=result.tenant,
                    priority=request.priority,
                    parent_ids=list(request.parent_ids),
                    created_at=int(time.time()),
                    board_revision=result.board_revision_after,
                )
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
                skills=request.skills,
                model_override=request.model_override,
                provider_override=request.provider_override,
                workspace_kind=request.workspace_kind,
                workspace_path=request.workspace_path,
                branch_name=request.branch_name,
                max_runtime_seconds=request.max_runtime_seconds,
                max_retries=request.max_retries,
                goal_mode=request.goal_mode,
                goal_max_turns=request.goal_max_turns,
            )

    @mcp.resource(
        KANBAN_UI_RESOURCE_URI, name="hermes_kanban_ui", title="Hermes Kanban board",
        description="Read-only Hermes Kanban board view.", mime_type=KANBAN_UI_MIME_TYPE,
        meta=_widget_resource_meta(public_base_url=settings.public_base_url, version="v1"),
    )
    def kanban_ui() -> str:
        # ChatGPT may cache the original get_board -> resource URI binding for
        # the lifetime of a connector session.  When Interactive R1 is enabled,
        # keep that legacy URI as an alias for the interactive resource so an
        # already-connected client receives the upgraded UI without requiring a
        # connector rediscovery/reconnect.
        html = _build_primary_kanban_ui(interactive=settings.ui_interactive_r1)
        if len(html.encode("utf-8")) > KANBAN_UI_MAX_BYTES:
            raise ValueError("Kanban UI resource exceeds size limit")
        return html

    @mcp.resource(
        HUMAN_GATE_RESOURCE_URI, name="hermes_human_gate_ui", title="Hermes Human Gate readback",
        description="Non-authoritative Human Gate evidence and dashboard handoff.",
        mime_type=KANBAN_UI_MIME_TYPE,
        meta=_widget_resource_meta(public_base_url=settings.public_base_url, version="v1"),
    )
    def human_gate_ui() -> str:
        html = build_human_gate_ui_html()
        if len(html.encode("utf-8")) > KANBAN_UI_MAX_BYTES:
            raise ValueError("Human Gate UI resource exceeds size limit")
        return html

    if settings.ui_interactive_r1:
        @mcp.resource(
            KANBAN_UI_RESOURCE_URI_INTERACTIVE_R1,
            name="hermes_kanban_ui_interactive_r1",
            title="Hermes Kanban board (interactive R1)",
            description="Shared human+ChatGPT canonical Kanban controls with bounded reconciliation.",
            mime_type=KANBAN_UI_MIME_TYPE,
            meta=_widget_resource_meta(
                public_base_url=settings.public_base_url,
                version="interactive-r1",
            ),
        )
        def kanban_ui_interactive_r1() -> str:
            return build_kanban_ui_interactive_r1_html()

        @mcp.resource(
            KANBAN_UI_RESOURCE_URI_INTERACTIVE_R14,
            name="hermes_kanban_ui_interactive_r14",
            title="Hermes Kanban board (interactive R1.1 fresh binding)",
            description="Fresh-cache Interactive R1.1 binding for ChatGPT MCP Apps sessions.",
            mime_type=KANBAN_UI_MIME_TYPE,
            meta=_widget_resource_meta(
                public_base_url=settings.public_base_url,
                version="interactive-r1.1-r14",
            ),
        )
        def kanban_ui_interactive_r14() -> str:
            return build_kanban_ui_interactive_r1_html()

        @mcp.resource(
            KANBAN_UI_RESOURCE_URI_INTERACTIVE_R16,
            name="hermes_kanban_ui_interactive_r16",
            title="Hermes Kanban board (interactive R1.6)",
            description="R1.6 shared-control board with staged drag/drop, modal inspector, and full-width state toggles.",
            mime_type=KANBAN_UI_MIME_TYPE,
            meta=_widget_resource_meta(
                public_base_url=settings.public_base_url,
                version="interactive-r1.6-r16",
            ),
        )
        def kanban_ui_interactive_r16() -> str:
            return build_kanban_ui_interactive_r1_html()
        @mcp.resource(
            KANBAN_UI_RESOURCE_URI_INTERACTIVE_R162,
            name="hermes_kanban_ui_interactive_r162",
            title="Hermes Kanban board (interactive R1.6.2 mobile workbench)",
            description="R1.6.2 mobile workbench with touch drag, persistent multi-selection, dependency focus, and staged confirmation.",
            mime_type=KANBAN_UI_MIME_TYPE,
            meta=_widget_resource_meta(
                public_base_url=settings.public_base_url,
                version="interactive-r1.6.2-r162",
            ),
        )
        def kanban_ui_interactive_r162() -> str:
            return build_kanban_ui_interactive_r1_html()

    if settings.ui_write_enabled_v2:
        @mcp.resource(
            KANBAN_UI_RESOURCE_URI_V2, name="hermes_kanban_ui_v2",
            title="Hermes Kanban board (create)",
            description="Bounded create-task view; canonical readback is required.",
            mime_type=KANBAN_UI_MIME_TYPE,
            meta=_widget_resource_meta(public_base_url=settings.public_base_url, version="v2"),
        )
        def kanban_ui_v2() -> str:
            return build_kanban_ui_v2_html()

    if beta:
        @mcp.tool(
            name="create_board",
            description="Create one canonical Hermes board; requires hermes:board:create.",
            annotations=board_admin_annotations,
            structured_output=True,
        )
        async def create_board(request: CreateBoardInput) -> CreateBoardResult:
            require_scope(auth_service.board_create_scope)
            from .probe_mode import enforce_probe_safe

            enforce_probe_safe(request, "create_board")
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
            from .probe_mode import enforce_probe_safe

            handle = resolve_board(request.board, operation="manage")
            enforce_probe_safe(request, "add_comment")
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
            from .probe_mode import enforce_probe_safe

            handle = resolve_board(request.board, operation="manage")
            enforce_probe_safe(request, "assign_task")
            return await run_beta_command(
                board_resolver.management_adapter(handle).assign_task,
                request.task_id,
                request.assignee,
                task_command=True,
            )

        @mcp.tool(
            name="diagnostics",
            description="Run bounded diagnostics for the selected board.",
            annotations=readonly,
            structured_output=True,
        )
        async def diagnostics(request: DiagnosticsInput) -> DiagnosticsResult:
            handle = resolve_board(request.board, operation="read")
            return await run_query(board_resolver.management_adapter(handle).diagnostics, request.task_id)

        async def _manage(request, method_name: str, *args, **kwargs):
            require_scope(auth_service.manage_scope)
            from .probe_mode import enforce_probe_safe

            handle = resolve_board(request.board, operation="manage")
            # Probe enforcement runs after scope + resolution and before side effect.
            enforce_probe_safe(request, method_name)
            return await run_beta_command(getattr(board_resolver.management_adapter(handle), method_name), *args, task_command=False, **kwargs)

        @mcp.tool(name="link_tasks", description="Add parent dependencies.", annotations=manage_annotations, structured_output=True)
        async def link_tasks(request: LinkTasksInput) -> LinkTasksResult:
            return await _manage(request, "link", request.parent_id, request.child_id)

        @mcp.tool(name="unlink_tasks", description="Remove parent dependencies.", annotations=manage_annotations, structured_output=True)
        async def unlink_tasks(request: UnlinkTasksInput) -> UnlinkTasksResult:
            return await _manage(request, "unlink", request.parent_id, request.child_id)

        @mcp.tool(name="set_model", description="Set a task model/provider override.", annotations=manage_annotations, structured_output=True)
        async def set_model(request: SetModelInput) -> SetModelResult:
            return await _manage(request, "set_model", request.task_id, request.model, request.provider)

        @mcp.tool(name="reclaim_task", description="Reclaim a running task.", annotations=manage_annotations, structured_output=True)
        async def reclaim_task(request: ReclaimInput) -> ReclaimResult:
            return await _manage(request, "reclaim", request.task_id, request.reason)

        @mcp.tool(name="reassign_tasks", description="Bulk reassign tasks matching filters.", annotations=manage_annotations, structured_output=True)
        async def reassign_tasks(request: ReassignInput) -> ReassignResult:
            return await _manage(request, "reassign", request.task_id, request.profile, reclaim=request.reclaim, reason=request.reason)

        @mcp.tool(name="complete_tasks", description="Mark tasks complete.", annotations=manage_annotations, structured_output=True)
        async def complete_tasks(request: CompleteInput) -> CompleteResult:
            return await _manage(request, "complete", request.task_ids, request.result, request.summary, request.metadata)

        @mcp.tool(name="edit_task", description="Edit a completed task result.", annotations=manage_annotations, structured_output=True)
        async def edit_task(request: EditTaskInput) -> EditTaskResult:
            return await _manage(request, "edit", request.task_id, result=request.result, summary=request.summary, metadata=request.metadata)


        @mcp.tool(name="update_task", description="Edit safe metadata (title/body/priority) of a non-triage task.", annotations=manage_annotations, structured_output=True)
        async def update_task(request: UpdateTaskInput) -> UpdateTaskResult:
            return await _manage(request, "update_task", request.task_id, title=request.title, body=request.body, priority=request.priority)

        @mcp.tool(name="soft_retire_edge", description="Idempotently soft-retire one ACTIVE edge with replacement provenance.", annotations=manage_annotations, structured_output=True)
        async def soft_retire_edge(request: SoftRetireEdgeInput) -> SoftRetireEdgeResult:
            return await _manage(request, "soft_retire_edge", request.parent_id, request.child_id, replaced_by_parent_id=request.replaced_by_parent_id, recovery_relation_id=request.recovery_relation_id, retired_by=request.retired_by, edge_state=request.edge_state)

        @mcp.tool(name="block_tasks", description="Block tasks with a typed reason.", annotations=manage_annotations, structured_output=True)
        async def block_tasks(request: BlockInput) -> BlockResult:
            return await _manage(request, "block", request.task_ids, kind=request.kind, reason=request.reason)

        @mcp.tool(name="schedule_tasks", description="Park tasks in scheduled state.", annotations=manage_annotations, structured_output=True)
        async def schedule_tasks(request: ScheduleInput) -> ScheduleResult:
            return await _manage(request, "schedule", request.task_ids, request.reason)

        @mcp.tool(name="unblock_tasks", description="Unblock tasks.", annotations=manage_annotations, structured_output=True)
        async def unblock_tasks(request: UnblockInput) -> UnblockResult:
            return await _manage(request, "unblock", request.task_ids, request.reason)

        @mcp.tool(name="request_review", description="Move tasks to review.", annotations=manage_annotations, structured_output=True)
        async def request_review(request: RequestReviewInput) -> RequestReviewResult:
            return await _manage(request, "request_review", request.task_id, request.summary, request.reviewer, request.metadata, request.force)

        @mcp.tool(name="request_changes", description="Request changes on reviewed tasks.", annotations=manage_annotations, structured_output=True)
        async def request_changes(request: RequestChangesInput) -> RequestChangesResult:
            return await _manage(request, "request_changes", request.task_id, request.reason)

        @mcp.tool(name="reopen_review", description="Reopen reviewed tasks.", annotations=manage_annotations, structured_output=True)
        async def reopen_review(request: ReopenReviewInput) -> ReopenReviewResult:
            return await _manage(request, "reopen_review", request.task_ids, request.reason)

        @mcp.tool(name="promote_tasks", description="Promote tasks through workflow.", annotations=manage_annotations, structured_output=True)
        async def promote_tasks(request: PromoteInput) -> PromoteResult:
            return await _manage(request, "promote", request.task_id, request.reason, request.ids, request.force, request.dry_run)

        @mcp.tool(name="archive_tasks", description="Archive tasks.", annotations=manage_annotations, structured_output=True)
        async def archive_tasks(request: ArchiveInput) -> ArchiveResult:
            if request.rm:
                require_scope(auth_service.admin_scope)
            return await _manage(request, "archive", request.task_ids, rm=request.rm)

        @mcp.tool(name="archive_task", description="Archive tasks (singular alias).", annotations=manage_annotations, structured_output=True)
        async def archive_task(request: ArchiveInput) -> ArchiveResult:
            if request.rm:
                require_scope(auth_service.admin_scope)
            return await _manage(request, "archive", request.task_ids, rm=request.rm)

        # The remaining canonical leaves are registered with fixed action names.
        # Each handler below chooses its adapter method; no request can select an
        # arbitrary command or SQL operation.
        def register_canonical(name, model, callback, *, scope=auth_service.manage_scope, admin=False, result_model=CanonicalActionResult):
            required = auth_service.admin_scope if admin else scope

            # Reads stay probe-free.  Every authority-bearing tool fails closed
            # under probe mode, after scope + resolution and before side effect.
            read_scope_names = {
                "attachments",
                "stats",
                "log",
                "runs",
                "assignees",
                "context",
                "tail",
                "watch",
                "human-gate",
                "canary",
                "control-status",
            }

            async def tool(request):
                require_scope(required)
                board = getattr(request, "board", None)
                handle = resolve_board(board, operation="manage" if required != auth_service.read_scope else "read")
                if name not in read_scope_names:
                    from .probe_mode import enforce_probe_safe

                    enforce_probe_safe(request, name)
                return await run_beta_command(lambda: callback(handle, request), task_command=required != auth_service.read_scope)
            tool.__name__ = name.replace("-", "_")
            tool.__annotations__ = {"request": model, "return": result_model}
            mcp.tool(name=name, description=f"Canonical bounded Hermes action: {name}.", annotations=manage_annotations if not admin else board_admin_annotations, structured_output=True)(tool)

        def _call_management(handle, request):
            adapter = board_resolver.management_adapter(handle)
            return CanonicalActionResult(board=handle.slug, action="management", data={"accepted": True})

        # Read/write task leaves with canonical adapter calls.
        register_canonical("claim", ClaimInput, lambda h, r: CanonicalActionResult(board=h.slug, action="claim", data=board_resolver.management_adapter(h).claim(r.task_id, ttl_seconds=r.ttl_seconds)), admin=True)
        register_canonical("attach", AttachInput, lambda h, r: CanonicalActionResult(board=h.slug, action="attach", data=board_resolver.management_adapter(h).attach(
            r.task_id,
            local_path=r.local_path,
            filename=r.filename,
            content_type=r.content_type,
            content_base64=r.content_base64,
            hash_algo=r.hash_algo,
            hash_expected=r.hash_expected
        )), admin=True)
        register_canonical(
            "attachments",
            AttachmentsInput,
            lambda h, r: AttachmentsResult(
                task_id=r.task_id,
                attachments=[
                    AttachmentInfo(
                        id=int(item["id"]),
                        filename=str(item["filename"]),
                        content_type=item.get("content_type"),
                        size=int(item.get("size", 0)),
                        uploaded_by=item.get("uploaded_by"),
                        created_at=int(item.get("created_at", 0)),
                    )
                    for item in board_resolver.management_adapter(h).attachments(r.task_id)
                ],
            ),
            scope=auth_service.read_scope,
            result_model=AttachmentsResult,
        )
        register_canonical("attach-rm", AttachRemoveInput, lambda h, r: CanonicalActionResult(board=h.slug, action="attach-rm", data=board_resolver.management_adapter(h).attach_rm(r.attachment_id)), admin=True)
        register_canonical("stats", BoardQuery, lambda h, r: CanonicalActionResult(board=h.slug, action="stats", data=board_resolver.management_adapter(h).stats()), scope=auth_service.read_scope)
        register_canonical("log", TaskLogInput, lambda h, r: CanonicalActionResult(board=h.slug, action="log", data=board_resolver.management_adapter(h).log(r.task_id, r.limit)), scope=auth_service.read_scope)
        register_canonical("runs", TaskRunsInput, lambda h, r: CanonicalActionResult(board=h.slug, action="runs", data={"task_id": r.task_id, "runs": [getattr(x, "__dict__", {}) for x in board_resolver.management_adapter(h).runs(r.task_id, r.limit)]}), scope=auth_service.read_scope)
        register_canonical("heartbeat", HeartbeatInput, lambda h, r: CanonicalActionResult(board=h.slug, action="heartbeat", data=board_resolver.management_adapter(h).heartbeat(r.task_id, r.note)), admin=True)
        register_canonical("assignees", AssigneesInput, lambda h, r: CanonicalActionResult(board=h.slug, action="assignees", data={"assignees": board_resolver.management_adapter(h).assignees()}), scope=auth_service.read_scope)
        register_canonical("context", ContextInput, lambda h, r: CanonicalActionResult(board=h.slug, action="context", data=board_resolver.management_adapter(h).context(r.task_id)), scope=auth_service.read_scope)
        register_canonical("specify", SpecifyInput, lambda h, r: CanonicalActionResult(board=h.slug, action="specify", data=board_resolver.management_adapter(h).specify(r.task_id, body=r.body, properties=r.properties)), admin=True)
        register_canonical("tail", TailInput, lambda h, r: CanonicalActionResult(board=h.slug, action="tail", data=board_resolver.management_adapter(h).tail(r.task_id, cursor=r.cursor, limit=r.limit)), scope=auth_service.read_scope)
        def _watch_result(handle, request):
            data = board_resolver.management_adapter(handle).watch(task_id=request.task_id, cursor=request.cursor, limit=request.limit)
            return WatchResult(board=handle.slug, **data)
        register_canonical("watch", WatchInput, _watch_result, scope=auth_service.read_scope, result_model=WatchResult)

        # Global/system leaves are bounded snapshots or one-cycle calls. The
        # daemon leaf intentionally exposes a control snapshot, never a loop.
        register_canonical("init", InitInput, lambda h, r: InitResult(**board_resolver.management_adapter(h).init()), admin=True, result_model=InitResult)
        register_canonical("swarm", SwarmInput, lambda h, r: SwarmResult(**board_resolver.management_adapter(h).swarm(goal=r.goal, workers=r.workers, verifier=r.verifier, synthesizer=r.synthesizer, tenant=r.tenant, idempotency_key=r.idempotency_key, priority=r.priority, created_by=r.created_by)), admin=True, result_model=SwarmResult)
        register_canonical("dispatch", DispatchInput, lambda h, r: CanonicalActionResult(board=h.slug, action="dispatch", data=board_resolver.management_adapter(h).dispatch(dry_run=r.dry_run, max_spawn=r.max_spawn)), admin=True)
        register_canonical("daemon", DaemonInput, lambda h, r: DaemonResult(**board_resolver.management_adapter(h).daemon(action=r.action)), admin=True, result_model=DaemonResult)
        register_canonical("decompose", DecomposeInput, lambda h, r: CanonicalActionResult(board=h.slug, action="decompose", data=board_resolver.management_adapter(h).decompose(r.task_id, r.titles, r.bodies)), admin=True)
        register_canonical("gc", GcInput, lambda h, r: GcResult(**board_resolver.management_adapter(h).gc(dry_run=r.dry_run, event_retention_days=r.event_retention_days, log_retention_days=r.log_retention_days)), admin=True, result_model=GcResult)
        register_canonical("repair", InitInput, lambda h, r: RepairResult(**board_resolver.management_adapter(h).repair()), admin=True, result_model=RepairResult)
        register_canonical("notify-subscribe", NotifySubscribeInput, lambda h, r: NotifySubscribeResult(task_id=r.task_id, platform=r.platform, chat_id=r.chat_id, thread_id=r.thread_id, delivery=r.delivery, subscribed=board_resolver.management_adapter(h).notify_subscribe(r.task_id, "", platform=r.platform, chat_id=r.chat_id, thread_id=r.thread_id, delivery=r.delivery)["subscribed"]), admin=False, result_model=NotifySubscribeResult)
        def _notify_list_result(handle, request):
            entries = board_resolver.management_adapter(handle).notify_list(request.limit, request.task_id)
            return NotifyListResult(subscriptions=[NotifySubscriptionInfo(**entry) for entry in entries], count=len(entries))

        register_canonical("notify-list", NotifyListInput, lambda h, r: _notify_list_result(h, r), scope=auth_service.read_scope, result_model=NotifyListResult)
        register_canonical("notify-unsubscribe", NotifyUnsubscribeInput, lambda h, r: NotifyUnsubscribeResult(task_id=r.task_id, platform=r.platform, chat_id=r.chat_id, thread_id=r.thread_id, unsubscribed=board_resolver.management_adapter(h).notify_unsubscribe(r.task_id, "", platform=r.platform, chat_id=r.chat_id, thread_id=r.thread_id)["unsubscribed"]), admin=False, result_model=NotifyUnsubscribeResult)

        # Board leaves are explicit and fail closed; the existing list_boards,
        # create_board, and get_board tools remain the mapped list/create/show.
        register_canonical("boards-rm", RemoveBoardInput, lambda h, r: CanonicalActionResult(board=h.slug, action="boards rm", data=board_resolver.board_admin_adapter().remove_board(r.slug, confirm=r.confirm)), admin=True)
        register_canonical("boards-switch", SwitchBoardInput, lambda h, r: CanonicalActionResult(board=h.slug, action="boards switch", data=board_resolver.board_admin_adapter().switch_board(r.slug)), admin=True)
        register_canonical("boards-rename", RenameBoardInput, lambda h, r: CanonicalActionResult(board=h.slug, action="boards rename", data=board_resolver.board_admin_adapter().rename_board(r.slug, name=r.name, description=r.description)), admin=True)
        register_canonical("boards-set-default-workdir", SetDefaultWorkdirInput, lambda h, r: CanonicalActionResult(board=h.slug, action="boards set-default-workdir", data=board_resolver.board_admin_adapter().set_default_workdir(r.slug, r.workdir)), admin=True)

        # Wave 4: human gates + canary/status are bounded, auditable leaves that
        # delegate to hermes_chatgpt_mcp.control_plane — no new daemon loops.
        def _human_gate(handle, request):
            from .control_plane import build_gate_context, format_gate_markdown

            ctx = build_gate_context(  # type: ignore[arg-type]
                read_adapter=board_resolver.query_adapter(handle),
                board=handle.slug,
                task_id=request.task_id,
                surface="beta" if beta else "stable",
                residual_risk=request.residual_risk,
            )
            p = ctx.provenance
            e = ctx.evidence
            return HumanGateView(
                task_id=ctx.task_id,
                board=ctx.board,
                provenance={
                    "candidate_sha": p.candidate_sha,
                    "candidate_branch": p.candidate_branch,
                    "baseline_branch": p.baseline_branch,
                    "baseline_mcp_sha": p.baseline_mcp_sha,
                    "baseline_hermes_sha": p.baseline_hermes_sha,
                    "baseline_phase_s_sha": p.baseline_phase_s_sha,
                    "api_version": p.api_version,
                    "surface": p.surface,
                    "provenance_header": p.provenance_header,
                },
                evidence={
                    "task_title": e.task_title,
                    "task_status": e.task_status,
                    "latest_summary": e.latest_summary,
                    "result_excerpt": e.result_excerpt,
                    "parent_ids": e.parent_ids,
                    "child_ids": e.child_ids,
                    "dispatch_state": e.dispatch_state,
                    "dispatch_reasons": e.dispatch_reasons,
                    "truncated": e.truncated,
                },
                residual_risk=list(ctx.residual_risk),
                rollback=ctx.rollback,
                decision_options=list(ctx.decision_options),
                markdown=format_gate_markdown(ctx),
                generated_at=ctx.generated_at,
            )

        register_canonical("human-gate", HumanGateInput, _human_gate, scope=auth_service.read_scope, result_model=HumanGateView)

        def _human_gate_decide(handle, request):
            from .control_plane import validate_gate_actor, validate_gate_requester

            # Stale-candidate policy: a decision naming a superseded/retired
            # requester would approve evidence from a dead candidate — reject
            # before any write happens.
            validate_gate_requester(request.requester)
            # The deciding actor is the authenticated OAuth subject of the
            # caller; self-approval (requester == actor) fails closed.
            token = get_access_token()
            claims = auth_service.verified_claims(token.token) if token is not None else None
            raw_subject = claims.get("sub") if isinstance(claims, dict) else None
            actor = raw_subject if isinstance(raw_subject, str) else None
            validate_gate_actor(requester=request.requester, actor=actor)
            # Auditable: the decision is a canonical task comment on the gate task,
            # not an implicit FK flip.  The human's YES/NO stays in task_events.
            body = f"HUMAN_GATE {request.decision}: {request.task_id} on {handle.slug}"
            if request.reason:
                body += f"\nReason: {request.reason[:2000]}"
            if request.requester:
                body += f"\nRequester: {request.requester[:200]}"
            row = board_resolver.management_adapter(handle).add_comment(
                request.task_id, body
            )
            return HumanGateDecisionResult(
                board=handle.slug,
                task_id=request.task_id,
                decision=request.decision,
                recorded=True,
                comment_id=int(getattr(row, "comment_id", 0) or 0) or None,
            )

        register_canonical("human-gate-decide", HumanGateDecisionInput, _human_gate_decide, result_model=HumanGateDecisionResult)

        def _canary(handle, request):
            from .control_plane import build_canary_bundle

            bundle = build_canary_bundle(
                build_commit=request.build_commit, surface=request.surface, deployed_at=request.deployed_at
            )
            if not bundle.verified:
                raise ToolError("; ".join(bundle.errors))
            return CanaryResult(board=handle.slug, manifest=bundle.manifest, verified=True)

        register_canonical("canary", CanaryInput, _canary, scope=auth_service.read_scope, result_model=CanaryResult)

        def _control_status(handle, request):
            from .control_plane import drain_preview, pause_status, status_snapshot

            snap = status_snapshot(  # type: ignore[arg-type]
                read_adapter=board_resolver.query_adapter(handle),
                manage_adapter=board_resolver.management_adapter(handle),
                board=handle.slug,
                include_dispatch_dry_run=request.include_dispatch_dry_run,
            )
            return ControlStatusResult(
                board=snap.board,
                generated_at=snap.generated_at,
                daemon=snap.daemon,
                stats=snap.stats,
                dispatch_dry_run=snap.dispatch_dry_run,
                notify_count=snap.notify_count,
                control_plane=snap.control_plane,
                pause=pause_status(),
                drain_preview=drain_preview(manage_adapter=board_resolver.management_adapter(handle)),
            )

        register_canonical("control-status", ControlStatusInput, _control_status, scope=auth_service.read_scope, result_model=ControlStatusResult)

    prov = get_candidate_provenance(surface="beta" if beta else "stable")

    @mcp.custom_route("/healthz", methods=["GET"], include_in_schema=False)
    async def healthz(request: Request) -> Response:
        payload: dict[str, object] = {"status": "ok"}
        if beta:
            payload["build"] = build_metadata.public_dict()
        headers = {
            "X-V4-Provenance": prov.provenance_header("beta" if beta else "stable"),
            "X-API-Version": API_VERSION,
            "X-Baseline-Branch": prov.baseline.branch,
            "X-Baseline-MCP": prov.baseline.mcp_sha[:12],
        }
        return JSONResponse(payload, headers=headers)

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
            for name in ("scope_extra_manage", "scope_extra_board_create", "scope_extra_admin"):
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
            admin_scope = auth_service.admin_scope
            wants_admin = admin_scope in requested_set
            # Honor access_mode before grant validation. Read mode (including
            # the omitted/default case) strips command scopes even when the
            # resource owner separately consented to hermes:admin: an admin
            # grant is global and never carries a board claim. Write mode
            # requires a selected board bound to at least one command scope;
            # admin is retained as an independent elevated scope alongside it.
            if access_mode == "read":
                requested_scope = " ".join(
                    scope for scope in auth_service.supported_scopes
                    if scope in requested_set and scope not in command_scopes
                )
            elif access_mode == "write":
                if wants_admin:
                    # Admin is separately consented and never inferred from
                    # board creation. Strip the global admin scope from the
                    # command-scoped grant; it is re-added independently below
                    # and remains a global, board-claim-free scope.
                    command_set = requested_set - {admin_scope}
                    if not command_scopes.intersection(command_set):
                        raise OAuthError(
                            ("client did not request a board command scope; re-register the MCP client"
                             if beta
                             else "client did not request hermes:create; re-register the MCP client"),
                            code="invalid_scope",
                        )
                    selected_board = form.get("board") or None
                    try:
                        board_resolver.resolve(selected_board, operation="read")
                    except BoardResolutionError as exc:
                        raise OAuthError("invalid board selection", code="invalid_request") from exc
                    write_grant = True
                    requested_scope = " ".join(
                        scope for scope in auth_service.supported_scopes
                        if scope in requested_set
                    )
                else:
                    if not command_scopes.intersection(requested_scope.split()):
                        raise OAuthError(
                            ("client did not request a board command scope; re-register the MCP client"
                             if beta
                             else "client did not request hermes:create; re-register the MCP client"),
                            code="invalid_scope",
                        )
                    selected_board = form.get("board") or None
                    try:
                        board_resolver.resolve(selected_board, operation="read")
                    except BoardResolutionError as exc:
                        raise OAuthError("invalid board selection", code="invalid_request") from exc
                    write_grant = True
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

    if settings.chatgpt_compat_mode:
        # The API-style ChatGPT connector needs only this deliberately frozen
        # contract. Keep beta OAuth gates and handlers, but do not advertise
        # any of the wider beta control-plane leaves.
        # V4.1-Compat-Plus-r1: the connector projection is deliberately
        # narrower than the beta registry.  Keep this as a server-side
        # allowlist so authority-bearing beta leaves cannot become visible by
        # accident when new canonical tools are registered.
        allowed_tools = {
            # V4 stable rollback profile (11 tools).
            "list_boards", "get_board", "list_tasks", "get_task",
            "get_task_graph", "get_dispatch", "get_activity", "create_task",
            "create_board", "add_comment", "assign_task",
            # V4.1 reviewed read/manage additions (10 tools).
            "get_run", "list_runs", "active_workers", "bounded_log",
            "runtime_status", "attachments", "control-status", "canary",
            "diagnostics", "update_task",
        }
        # The interactive MCP App is opt-in. When the deployment explicitly
        # enables it, expose only the fresh R1.6 render tool through the
        # otherwise frozen ChatGPT compatibility projection. Keeping this
        # conditional preserves the exact legacy contract when the flag is off.
        if settings.ui_interactive_r1:
            allowed_tools.add("get_board_interactive_r162")
        mcp._tool_manager._tools = {  # type: ignore[attr-defined]
            name: tool
            for name, tool in mcp._tool_manager._tools.items()  # type: ignore[attr-defined]
            if name in allowed_tools
        }
    if not beta:
        # Wave-2 observability is beta-only; preserve the frozen stable 8-tool surface.
        mcp._tool_manager._tools = {  # type: ignore[attr-defined]
            name: tool
            for name, tool in mcp._tool_manager._tools.items()  # type: ignore[attr-defined]
            if name not in {"get_run", "list_runs", "active_workers", "bounded_log", "runtime_status"}
        }
    _strictify_tools(mcp)
    app = mcp.streamable_http_app()
    app.add_middleware(_McpObservabilityMiddleware)

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
