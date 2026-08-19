from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

import pytest

from scripts.verify_beta_release import ReleaseVerificationError, fetch_health, verify_health


class _HealthHandler(BaseHTTPRequestHandler):
    payload: bytes = b"{}"
    status = 200

    def do_GET(self):  # noqa: N802 - stdlib HTTPServer hook
        if self.path != "/healthz":
            self.send_response(404)
            self.end_headers()
            return
        self.send_response(self.status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(self.payload)))
        self.end_headers()
        self.wfile.write(self.payload)

    def log_message(self, *_args):
        return


@pytest.fixture
def health_server():
    server = ThreadingHTTPServer(("127.0.0.1", 0), _HealthHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server, _HealthHandler
    finally:
        server.shutdown()
        thread.join(timeout=2)


def _url(server: ThreadingHTTPServer) -> str:
    return f"http://127.0.0.1:{server.server_port}"


def _healthy_payload():
    return {
        "status": "ok",
        "build": {
            "build_commit": "c" * 40,
            "surface": "beta",
            "deployed_at": "2026-08-19T12:00:00Z",
        },
    }


def test_release_verifier_accepts_matching_beta_health(health_server):
    server, handler = health_server
    handler.payload = json.dumps(_healthy_payload()).encode()
    handler.status = 200

    health = fetch_health(_url(server))

    assert verify_health(health, "c" * 40) == {
        "status": "ok",
        "surface": "beta",
        "build_commit": "c" * 40,
    }


@pytest.mark.parametrize(
    ("mutator", "message"),
    [
        (lambda body: body["build"].update(build_commit="d" * 40), "build_commit"),
        (lambda body: body["build"].update(surface="stable"), "surface"),
        (lambda body: body.update(status="degraded"), "status"),
    ],
)
def test_release_verifier_rejects_non_matching_health(mutator, message):
    body = _healthy_payload()
    mutator(body)

    with pytest.raises(ReleaseVerificationError, match=message):
        verify_health(body, "c" * 40)


def test_release_verifier_rejects_non_json_or_non_200_health(health_server):
    server, handler = health_server
    handler.payload = b"not-json"
    handler.status = 200
    with pytest.raises(ReleaseVerificationError, match="JSON"):
        fetch_health(_url(server))

    handler.payload = b'{"status":"ok"}'
    handler.status = 503
    with pytest.raises(ReleaseVerificationError, match="HTTP 503"):
        fetch_health(_url(server))
