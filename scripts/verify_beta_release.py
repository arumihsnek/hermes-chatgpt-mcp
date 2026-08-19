from __future__ import annotations

import argparse
import json
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


class ReleaseVerificationError(RuntimeError):
    """Raised when a beta health response cannot attest the requested release."""


def _health_url(base_url: str) -> str:
    parsed = urlsplit(base_url)
    if not parsed.scheme or not parsed.netloc:
        raise ReleaseVerificationError("release URL must include a scheme and host")
    path = parsed.path.rstrip("/")
    if not path.endswith("/healthz"):
        path += "/healthz"
    return parsed._replace(path=path, query="", fragment="").geturl()


def fetch_health(base_url: str, *, timeout: float = 5.0) -> dict[str, Any]:
    request = Request(_health_url(base_url), headers={"Accept": "application/json"})
    try:
        with urlopen(request, timeout=timeout) as response:
            status = int(response.status)
            payload = response.read(16_384)
    except HTTPError as exc:
        raise ReleaseVerificationError(f"health endpoint returned HTTP {exc.code}") from exc
    except (OSError, URLError, TimeoutError) as exc:
        raise ReleaseVerificationError("health endpoint was unreachable") from exc
    if status != 200:
        raise ReleaseVerificationError(f"health endpoint returned HTTP {status}")
    try:
        body = json.loads(payload.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ReleaseVerificationError("health endpoint returned invalid JSON") from exc
    if not isinstance(body, dict):
        raise ReleaseVerificationError("health endpoint returned a non-object JSON value")
    return body


def verify_health(body: dict[str, Any], expected_commit: str, *, expected_surface: str = "beta") -> dict[str, str]:
    if body.get("status") != "ok":
        raise ReleaseVerificationError("status is not ok")
    build = body.get("build")
    if not isinstance(build, dict):
        raise ReleaseVerificationError("build attestation is missing")
    if build.get("build_commit") != expected_commit:
        raise ReleaseVerificationError("build_commit does not match requested release")
    if build.get("surface") != expected_surface:
        raise ReleaseVerificationError("surface does not match beta")
    return {
        "status": "ok",
        "surface": expected_surface,
        "build_commit": expected_commit,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify a public Hermes beta release health attestation.")
    parser.add_argument("--url", required=True, help="Public beta base URL")
    parser.add_argument("--commit", required=True, help="Expected deployed commit SHA")
    args = parser.parse_args(argv)
    try:
        result = verify_health(fetch_health(args.url), args.commit)
    except ReleaseVerificationError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    host = urlsplit(args.url).netloc
    print(f"PASS host={host} status={result['status']} surface={result['surface']} build_commit={result['build_commit']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
