from __future__ import annotations

import os

from .auth import BETA_AUTH_POLICY, AuthService
from .config import Settings
from .server import create_app


def main() -> None:
    import uvicorn

    settings = Settings.from_env()
    assert settings.surface == "beta", "beta entrypoint requires MCP_SURFACE=beta"
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
