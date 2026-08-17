from __future__ import annotations

import os
from pathlib import Path

from .auth import BETA_AUTH_POLICY, AuthService
from .config import Settings
from .server import create_app


BETA_PUBLIC_BASE_URL = "https://kanban-beta.hermesinthenight.duckdns.org"
BETA_OAUTH_STATE_FILE = Path("/var/lib/hermes-chatgpt-mcp-beta/oauth-state.json")
BETA_ENV_FILE = "/home/ubuntu/.hermes/hermes-chatgpt-mcp-beta.env"


def _assert_beta_runtime_isolation(settings: Settings) -> None:
    if settings.public_base_url != BETA_PUBLIC_BASE_URL:
        raise RuntimeError("beta public origin is not configured")
    if Path(settings.oauth_state_file or "").expanduser() != BETA_OAUTH_STATE_FILE:
        raise RuntimeError("beta OAuth state file is not isolated")
    if os.environ.get("MCP_ENV_FILE") != BETA_ENV_FILE:
        raise RuntimeError("beta private environment file is not selected")
    if os.environ.get("MCP_OAUTH_SIGNING_KEY") != settings.oauth_signing_key:
        raise RuntimeError("beta OAuth signing key is not supplied by its private environment")


def main() -> None:
    import uvicorn

    settings = Settings.from_env()
    assert settings.surface == "beta", "beta entrypoint requires MCP_SURFACE=beta"
    _assert_beta_runtime_isolation(settings)
    auth = AuthService(settings, policy=BETA_AUTH_POLICY)
    app = create_app(settings=settings, surface="beta", auth_service=auth)
    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        log_level=os.environ.get("MCP_LOG_LEVEL", "info").lower(),
        access_log=False,
    )


if __name__ == "__main__":  # pragma: no cover
    main()
