from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse


class ConfigurationError(ValueError):
    """Raised when the service cannot start safely from its configuration."""


_BOARD_SLUG = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")


def _env(name: str, default: str | None = None) -> str | None:
    value = os.environ.get(name)
    if value is None:
        return default
    value = value.strip()
    return value or default


def _positive_int(name: str, default: int, *, maximum: int) -> int:
    raw = _env(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ConfigurationError(f"{name} must be an integer") from exc
    if value < 1 or value > maximum:
        raise ConfigurationError(f"{name} must be between 1 and {maximum}")
    return value


def _boolean(name: str, default: bool = False) -> bool:
    raw = _env(name)
    if raw is None:
        return default
    normalized = raw.lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ConfigurationError(f"{name} must be a boolean")


def _surface() -> Literal["stable", "beta"]:
    value = _env("MCP_SURFACE", "stable")
    if value not in {"stable", "beta"}:
        raise ConfigurationError("MCP_SURFACE must be stable or beta")
    return value


def _board_set(name: str) -> tuple[str, ...] | None:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return None
    values = tuple(part.strip() for part in raw.split(","))
    if any(not value for value in values):
        raise ConfigurationError(f"{name} must not contain empty board slugs")
    if len(set(values)) != len(values):
        raise ConfigurationError(f"{name} must not contain duplicate board slugs")
    for value in values:
        if not _BOARD_SLUG.fullmatch(value):
            raise ConfigurationError(f"{name} contains an invalid board slug")
    return values


def _url(value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ConfigurationError("MCP_PUBLIC_BASE_URL must be an absolute HTTP(S) URL")
    if parsed.query or parsed.fragment:
        raise ConfigurationError("MCP_PUBLIC_BASE_URL must not contain a query or fragment")
    if parsed.scheme == "http" and parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise ConfigurationError("MCP_PUBLIC_BASE_URL must use HTTPS outside local development")
    return value.rstrip("/")


@dataclass(frozen=True)
class Settings:
    hermes_agent_root: Path
    hermes_kanban_home: Path | None
    default_board: str | None
    public_base_url: str
    host: str
    port: int
    oauth_username: str
    oauth_password: str
    oauth_signing_key: str
    max_page_size: int = 100
    max_graph_depth: int = 3
    max_graph_nodes: int = 100
    max_body_chars: int = 64_000
    max_log_bytes: int = 32_000
    max_activity_items: int = 200
    oauth_code_ttl_seconds: int = 300
    oauth_token_ttl_seconds: int = 3600
    oauth_state_file: Path | None = None
    kanban_read_boards: tuple[str, ...] | None = None
    kanban_create_boards: tuple[str, ...] | None = None
    max_board_count: int = 50
    oauth_diagnostics: bool = False
    surface: Literal["stable", "beta"] = "stable"
    board_create_enabled: bool = False
    build_metadata_file: Path | None = None

    @classmethod
    def from_env(cls) -> "Settings":
        root_raw = _env("HERMES_AGENT_ROOT", "/home/ubuntu/hermes-agent")
        assert root_raw is not None
        root = Path(root_raw).expanduser()
        if not root.is_dir():
            raise ConfigurationError("HERMES_AGENT_ROOT must point to a directory")

        public_base_url = _url(_env("MCP_PUBLIC_BASE_URL", "http://127.0.0.1:8789") or "")
        username = _env("MCP_OAUTH_USERNAME")
        password = _env("MCP_OAUTH_PASSWORD")
        signing_key = _env("MCP_OAUTH_SIGNING_KEY")
        if not username or not password or not signing_key:
            raise ConfigurationError(
                "MCP_OAUTH_USERNAME, MCP_OAUTH_PASSWORD, and MCP_OAUTH_SIGNING_KEY are required"
            )
        if len(password) < 16:
            raise ConfigurationError("MCP_OAUTH_PASSWORD must contain at least 16 characters")
        if len(signing_key) < 32:
            raise ConfigurationError("MCP_OAUTH_SIGNING_KEY must contain at least 32 characters")

        home_raw = _env("HERMES_KANBAN_HOME")
        state_raw = _env("MCP_OAUTH_STATE_FILE", "/var/lib/hermes-chatgpt-mcp/oauth-state.json")
        return cls(
            hermes_agent_root=root,
            hermes_kanban_home=Path(home_raw).expanduser() if home_raw else None,
            default_board=_env("HERMES_KANBAN_BOARD"),
            public_base_url=public_base_url,
            host=_env("MCP_HOST", "127.0.0.1") or "127.0.0.1",
            port=_positive_int("MCP_PORT", 8789, maximum=65535),
            oauth_username=username,
            oauth_password=password,
            oauth_signing_key=signing_key,
            max_page_size=_positive_int("MCP_MAX_PAGE_SIZE", 100, maximum=500),
            max_graph_depth=_positive_int("MCP_MAX_GRAPH_DEPTH", 3, maximum=8),
            max_graph_nodes=_positive_int("MCP_MAX_GRAPH_NODES", 100, maximum=500),
            max_body_chars=_positive_int("MCP_MAX_BODY_CHARS", 64_000, maximum=1_000_000),
            max_log_bytes=_positive_int("MCP_MAX_LOG_BYTES", 32_000, maximum=1_000_000),
            max_activity_items=_positive_int("MCP_MAX_ACTIVITY_ITEMS", 200, maximum=2_000),
            oauth_code_ttl_seconds=_positive_int("MCP_OAUTH_CODE_TTL", 300, maximum=900),
            oauth_token_ttl_seconds=_positive_int("MCP_OAUTH_TOKEN_TTL", 3600, maximum=86_400),
            oauth_state_file=Path(state_raw).expanduser() if state_raw else None,
            kanban_read_boards=_board_set("MCP_KANBAN_READ_BOARDS"),
            kanban_create_boards=_board_set("MCP_KANBAN_CREATE_BOARDS"),
            max_board_count=_positive_int("MCP_MAX_BOARD_COUNT", 50, maximum=50),
            oauth_diagnostics=_boolean("MCP_OAUTH_DIAGNOSTICS"),
            surface=_surface(),
            board_create_enabled=_boolean("MCP_BOARD_CREATE_ENABLED"),
            build_metadata_file=(
                Path(value).expanduser()
                if (value := _env("MCP_BUILD_METADATA_FILE"))
                else None
            ),
        )
