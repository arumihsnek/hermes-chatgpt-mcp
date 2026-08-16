from __future__ import annotations

import hashlib
import json
import logging
import re
import secrets
from urllib.parse import urlsplit


logger = logging.getLogger("hermes_chatgpt_mcp.oauth")
EVENT_NAME = "hermes_oauth_diagnostic"

_SUPPORTED_SCOPES = ("hermes:read", "hermes:create", "offline_access")
_FINGERPRINT_FIELDS = {
    "client_fp",
    "code_fp",
    "flow_fp",
    "grant_fp",
    "refresh_fp",
    "new_refresh_fp",
    "token_fp",
}
_SCOPE_FIELDS = {
    "allowed_scopes",
    "effective_scopes",
    "granted_scopes",
    "original_scopes",
    "requested_scopes",
}
_SAFE_TEXT_FIELDS = {
    "code_challenge_method",
    "error_code",
    "grant_type",
    "grant_types",
    "outcome",
    "redirect",
    "resource",
    "response_type",
    "stage",
}
_SAFE_BOARD_FIELDS = {"board", "board_access"}
_SAFE_BOOL_FIELDS = {"client_reused", "grant_reused", "new_registration"}
_SAFE_INT_FIELDS = {"http_status"}
_SAFE_FIELD_NAMES = _FINGERPRINT_FIELDS | _SCOPE_FIELDS | _SAFE_TEXT_FIELDS | _SAFE_BOARD_FIELDS | _SAFE_BOOL_FIELDS | _SAFE_INT_FIELDS
_SAFE_TOKEN = re.compile(r"^[A-Za-z0-9_.:,-]{1,96}$")


def fingerprint(value: object) -> str:
    """Return a short one-way identifier suitable for diagnostic correlation."""

    return hashlib.sha256(str(value).encode("utf-8")).hexdigest()[:12]


def scope_summary(value: object, supported_scopes: tuple[str, ...] = _SUPPORTED_SCOPES) -> str:
    """Describe only known scope names and never echo arbitrary scope input."""

    raw = str(value or "").split()
    if not raw:
        return "<empty>"
    if len(raw) > 16 or any(len(item) > 64 for item in raw):
        return "<too_many>"
    known = [scope for scope in supported_scopes if scope in raw]
    if len(set(raw)) != len(known):
        known.append("<unsupported>")
    return " ".join(known) or "<unsupported>"


def redirect_identity(value: object) -> str:
    """Return scheme/host/path only; query, fragment, and userinfo are discarded."""

    try:
        parsed = urlsplit(str(value or ""))
        hostname = parsed.hostname
        if not parsed.scheme or not hostname:
            return "<invalid>"
        port = ""
        if parsed.port is not None:
            port = f":{parsed.port}"
        path = parsed.path or "/"
        return f"{parsed.scheme}://{hostname}{port}{path}"[:160]
    except (TypeError, ValueError):
        return "<invalid>"


def request_fingerprint(*values: object) -> str:
    """Correlate one authorization request without storing its raw parameters."""

    return fingerprint("\x1f".join(str(value or "") for value in values))


def _safe_fingerprint(value: object) -> str:
    text = str(value)
    if re.fullmatch(r"[0-9a-f]{12}", text):
        return text
    return fingerprint(text)


def _safe_text(value: object) -> str:
    text = str(value)
    return text if _SAFE_TOKEN.fullmatch(text) else "<invalid>"


def emit(settings: object, stage: str, **fields: object) -> str | None:
    """Emit a bounded, opt-in OAuth event; return its safe event identifier."""

    if not getattr(settings, "oauth_diagnostics", False):
        return None
    event: dict[str, object] = {
        "event": EVENT_NAME,
        "event_id": secrets.token_hex(6),
        "stage": _safe_text(stage),
    }
    for key, value in fields.items():
        if key not in _SAFE_FIELD_NAMES or value is None:
            continue
        if key in _FINGERPRINT_FIELDS:
            event[key] = _safe_fingerprint(value)
        elif key in _SCOPE_FIELDS:
            event[key] = scope_summary(value)
        elif key in _SAFE_BOOL_FIELDS:
            event[key] = bool(value)
        elif key in _SAFE_INT_FIELDS:
            try:
                event[key] = int(value)
            except (TypeError, ValueError):
                event[key] = -1
        elif key in {"redirect", "resource"}:
            event[key] = redirect_identity(value)
        else:
            event[key] = _safe_text(value)
    logger.info("%s", json.dumps(event, separators=(",", ":"), sort_keys=True))
    return str(event["event_id"])
