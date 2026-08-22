# hermes_chatgpt_mcp/ui_write_contract.py
# Frozen D1R write-security contract implementation
# DO NOT MODIFY without D1 independent review and a new frozen SHA.

from __future__ import annotations

import calendar
import re
import secrets
import time
from dataclasses import dataclass, field
from typing import Any


# ============================================================================
# §1 Capability Token Schema
# ============================================================================

UI_RESOURCE_URI_V2 = "ui://hermes/kanban/v2"
REQUIRED_SCOPE_CLAIM = "hermes:read hermes:create"
ALLOWED_OPERATIONS = ("create_task",)


@dataclass(frozen=True)
class UiCapability:
    capability_id: str
    subject: str
    surface: str
    resource_uri: str
    board: str
    tenant: str
    operations: tuple[str, ...]
    scope: str
    issued_at: str
    expires_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "capability_id": self.capability_id,
            "subject": self.subject,
            "surface": self.surface,
            "resource_uri": self.resource_uri,
            "board": self.board,
            "tenant": self.tenant,
            "operations": list(self.operations),
            "scope": self.scope,
            "issued_at": self.issued_at,
            "expires_at": self.expires_at,
        }


class UiCapabilityIssuer:
    """
    Issues and validates UI-origin capability tokens.

    CONTRACT §1.2: The issued token MUST include the exact scope claim
    "hermes:read hermes:create". No additional scopes. Omission or deviation
    returns UI_ORIGIN_UNVERIFIED and no write is performed.
    """

    def __init__(
        self,
        *,
        default_ttl_seconds: int = 3600,
        clock: Any = None,  # for testing: callable() -> float timestamp
    ) -> None:
        self._default_ttl = default_ttl_seconds
        self._clock = clock or time.time

    def issue(
        self,
        *,
        subject: str,
        board: str,
        tenant: str,
        surface: str = "stable",
        ttl_seconds: int | None = None,
        scope: str = REQUIRED_SCOPE_CLAIM,
        operations: tuple[str, ...] = ALLOWED_OPERATIONS,
    ) -> UiCapability:
        """
        Issue a new UI capability token.

        The issued token carries exactly the required scope claim per CONTRACT §1.2.
        """
        # Never silently narrow or widen an explicitly requested capability.
        # A caller attempting to issue an unsupported scope/operation receives
        # a hard failure rather than an apparently valid weaker token.
        if scope != REQUIRED_SCOPE_CLAIM:
            raise ValueError("unsupported UI capability scope")
        if tuple(operations) != ALLOWED_OPERATIONS:
            raise ValueError("unsupported UI capability operation")
        if not subject or not board or not tenant:
            raise ValueError("UI capability requires subject, board, and tenant")
        if surface != "stable":
            raise ValueError("unsupported UI capability surface")

        now = self._clock()
        issued_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now))
        ttl = ttl_seconds if ttl_seconds is not None else self._default_ttl
        if ttl <= 0:
            raise ValueError("UI capability TTL must be positive")
        expires_at = time.strftime(
            "%Y-%m-%dT%H:%M:%SZ", time.gmtime(now + ttl)
        )
        capability_id = secrets.token_urlsafe(16)

        return UiCapability(
            capability_id=capability_id,
            subject=subject,
            surface=surface,
            resource_uri=UI_RESOURCE_URI_V2,
            board=board,
            tenant=tenant,
            operations=ALLOWED_OPERATIONS,
            scope=REQUIRED_SCOPE_CLAIM,
            issued_at=issued_at,
            expires_at=expires_at,
        )

    def validate(
        self,
        token: UiCapability | dict[str, Any],
        *,
        expected_subject: str | None = None,
        expected_board: str | None = None,
        expected_tenant: str | None = None,
        expected_capability_id: str | None = None,
    ) -> tuple[bool, str | None]:
        """
        Validate a UI capability token.

        Returns (is_valid, error_code). Error codes:
        - EXPIRED
        - RESOURCE_URI_MISMATCH
        - SCOPE_MISSING_OR_INVALID
        - OPERATIONS_MISMATCH
        - CONTEXT_MISMATCH (board/tenant/subject/capability_id)
        """
        try:
            if isinstance(token, dict):
                raw_operations = token.get("operations")
                token = UiCapability(
                    capability_id=token["capability_id"],
                    subject=token["subject"],
                    surface=token["surface"],
                    resource_uri=token["resource_uri"],
                    board=token["board"],
                    tenant=token["tenant"],
                    operations=tuple(raw_operations) if isinstance(raw_operations, list | tuple) else (),
                    scope=token["scope"],
                    issued_at=token["issued_at"],
                    expires_at=token["expires_at"],
                )
            expires_ts = calendar.timegm(time.strptime(token.expires_at, "%Y-%m-%dT%H:%M:%SZ"))
        except (KeyError, TypeError, ValueError):
            return False, "MALFORMED_CAPABILITY"

        now = self._clock()
        if expires_ts <= now:
            return False, "EXPIRED"

        if token.resource_uri != UI_RESOURCE_URI_V2:
            return False, "RESOURCE_URI_MISMATCH"

        if token.scope != REQUIRED_SCOPE_CLAIM:
            return False, "SCOPE_MISSING_OR_INVALID"

        if tuple(token.operations) != ALLOWED_OPERATIONS:
            return False, "OPERATIONS_MISMATCH"

        if token.surface != "stable":
            return False, "SURFACE_MISMATCH"
        expected_values = {
            "subject": expected_subject,
            "board": expected_board,
            "tenant": expected_tenant,
            "capability_id": expected_capability_id,
        }
        for field_name, expected in expected_values.items():
            if expected is not None and getattr(token, field_name) != expected:
                return False, "CONTEXT_MISMATCH"

        return True, None


# ============================================================================
# §2 Payload Sanitization
# ============================================================================

# Value-level redaction patterns (applied to string values under ANY key)
_BEARER_PATTERN = re.compile(
    r"\b(Bearer|bearer)\s+([A-Za-z0-9\-._~+/]+=*)", re.IGNORECASE
)
_AUTH_HEADER_PATTERN = re.compile(
    r"\bAuthorization\s*:\s*(?!\[REDACTED\])([^\s\n]+)", re.IGNORECASE
)
_SECRET_PATTERN = re.compile(
    r"(?i)(api[_-]?key|secret|token|password|passwd)"
    r"(?:\s*[:=]\s*|\s+(?=[A-Za-z0-9._~+/=-]{16,}(?:\s|$)))"
    r"([^\s]{8,})"
)
_INTERNAL_PATH_PATTERN = re.compile(
    r"(/home/|/root/|/opt/|/var/|/etc/|/private/|/tmp/|/workspace/)"
)
_DSN_PATTERN = re.compile(
    r"\b(postgres|mysql|mongodb|redis|sqlite)://[^\s]+", re.IGNORECASE
)

# Key-name filtering (supplementary defense-in-depth)
_SENSITIVE_KEY_PATTERN = re.compile(
    r"(?i)(authorization|password|secret|token|api[_-]?key|private[_-]?key|bearer)"
)


def _redact_value(value: str) -> str:
    """Apply value-level redaction patterns to a single string."""
    # Bearer tokens
    value = _BEARER_PATTERN.sub(r"\1 [REDACTED]", value)
    # Authorization headers
    value = _AUTH_HEADER_PATTERN.sub(r"Authorization: [REDACTED]", value)
    # Secrets/API keys in key=value or key: value form
    value = _SECRET_PATTERN.sub(r"\1=[REDACTED]", value)
    # Internal absolute paths
    value = _INTERNAL_PATH_PATTERN.sub(r"[INTERNAL_PATH]/", value)
    # DSNs / connection strings
    value = _DSN_PATTERN.sub(r"[REDACTED]://", value)
    return value


def sanitize_ui_payload(payload: Any) -> Any:
    """
    Sanitize a payload crossing the UI boundary.

    CONTRACT §2.2: Redact secret/token/bearer/internal-path material embedded
    in string VALUES under benign keys, not only sensitive key names.

    CONTRACT §2.3: Non-destructive for ordinary card text. Redaction applies
    only to structural patterns, not substring matches.

    CONTRACT §2.4: Key-name filtering is supplementary; primary guarantee is
    value-level redaction.
    """
    if isinstance(payload, str):
        return _redact_value(payload)

    if isinstance(payload, dict):
        result = {}
        for key, value in payload.items():
            # Key-name defense-in-depth
            if isinstance(key, str) and _SENSITIVE_KEY_PATTERN.search(key):
                result[key] = "[REDACTED]"
            else:
                result[key] = sanitize_ui_payload(value)
        return result

    if isinstance(payload, list):
        return [sanitize_ui_payload(item) for item in payload]

    # Primitive types (int, float, bool, None) pass through unchanged
    return payload


# ============================================================================
# §3 UI Write Policy (reference implementation; server enforces)
# ============================================================================

UI_ALLOWED_OPERATIONS = {"create_task"}

UI_FORBIDDEN_OPERATIONS = frozenset(
    {
        # Human Gate
        "request_review",
        "request_changes",
        "reopen_review",
        "force",
        # Mutations beyond creation
        "add_comment",
        "assign_task",
        "reassign_tasks",
        "set_model",
        "edit_task",
        "link_tasks",
        "unlink_tasks",
        "complete_tasks",
        "promote_tasks",
        "block_tasks",
        "unblock_tasks",
        "schedule_tasks",
        "reclaim_task",
        "claim",
        "dispatch",
        # Board/infrastructure
        "create_board",
        "archive_tasks",
        "boards-rm",
        "boards-switch",
        "boards-rename",
        "boards-set-default-workdir",
        "init",
        "repair",
        "gc",
        "decompose",
        "swarm",
        "attach",
        "attach-rm",
        "heartbeat",
        "specify",
        "daemon",
        "notify-subscribe",
        "notify-unsubscribe",
    }
)

UI_ALLOWED_CREATE_FIELDS = frozenset(
    {"title", "body", "parent_ids", "expected_board_revision", "idempotency_key"}
)

UI_FORBIDDEN_CREATE_FIELDS = frozenset(
    {"board", "tenant", "assignee", "priority", "session_id", "triage", "created_by", "origin"}
)


def check_operation_allowed(operation: str) -> tuple[bool, str | None]:
    """Return (allowed, error_code)."""
    if operation in UI_ALLOWED_OPERATIONS:
        return True, None
    if operation in UI_FORBIDDEN_OPERATIONS:
        return False, "GATE_FORBIDDEN_FROM_UI"
    return False, "UI_OPERATION_FORBIDDEN"


def check_create_fields(fields: set[str]) -> tuple[bool, str | None]:
    """Return (allowed, error_code). Extra fields are forbidden."""
    extra = fields - UI_ALLOWED_CREATE_FIELDS
    if extra:
        return False, "UI_FIELD_FORBIDDEN"
    return True, None


# ============================================================================
# §4 Revision and Idempotency (schema reference; implementation in server)
# ============================================================================

@dataclass
class UiMutationReceipt:
    operation: str
    scope_key: str
    idempotency_key: str
    request_fingerprint: str
    canonical_task_id: str
    outcome: str  # "created" | "idempotent_replay"
    origin: str
    board_revision_after: int
    created_at: float
    expires_at: float = field(default=0.0)

    @staticmethod
    def make_scope_key(board: str, tenant: str, subject: str) -> str:
        return f"{board}|{tenant}|{subject}"


# ============================================================================
# §5 Provenance (constants for server)
# ============================================================================

UI_PROVENANCE_ACTOR = "mcp_ui"
UI_ORIGIN_VALUE = "ui"


# ============================================================================
# §6 Versioning
# ============================================================================

UI_RESOURCE_URI_V1 = "ui://hermes/kanban/v1"
UI_WRITE_ENABLED_DEFAULT = False