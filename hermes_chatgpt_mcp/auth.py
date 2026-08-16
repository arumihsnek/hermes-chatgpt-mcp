from __future__ import annotations

import base64
import hashlib
import hmac
import html
import json
import secrets
import threading
import time
from dataclasses import dataclass
from urllib.parse import urlparse

from mcp.server.auth.provider import AccessToken

from .config import Settings


class OAuthError(ValueError):
    """A safe OAuth protocol error without sensitive detail."""

    def __init__(self, message: str, *, code: str = "invalid_request") -> None:
        super().__init__(message)
        self.code = code


@dataclass
class _Client:
    client_id: str
    redirect_uris: tuple[str, ...]
    grant_types: tuple[str, ...]
    scope: str
    client_name: str


@dataclass
class _Code:
    client_id: str
    redirect_uri: str
    scope: str
    code_challenge: str
    expires_at: int
    used: bool = False


@dataclass
class _Refresh:
    client_id: str
    subject: str
    scope: str
    expires_at: int


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _unb64(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _json_b64(value: dict) -> str:
    return _b64(json.dumps(value, separators=(",", ":"), sort_keys=True).encode("utf-8"))


class AuthService:
    """Minimal local OAuth authorization-code service for a private connector.

    It stores short-lived registration/code state in memory. A restart requires
    the connector to authorize again; no Hermes state is involved.
    """

    scope = "hermes:read"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._clients: dict[str, _Client] = {}
        self._codes: dict[str, _Code] = {}
        self._refresh_tokens: dict[str, _Refresh] = {}
        self._lock = threading.RLock()

    def _cleanup(self) -> None:
        now = int(time.time())
        with self._lock:
            self._codes = {key: value for key, value in self._codes.items() if value.expires_at >= now and not value.used}
            self._refresh_tokens = {key: value for key, value in self._refresh_tokens.items() if value.expires_at >= now}
            if len(self._clients) > 64:
                for client_id in list(self._clients)[: len(self._clients) - 64]:
                    self._clients.pop(client_id, None)

    @staticmethod
    def _validate_redirect(uri: str) -> str:
        parsed = urlparse(uri)
        if parsed.fragment or parsed.username or parsed.password:
            raise OAuthError("invalid redirect URI", code="invalid_client_metadata")
        if parsed.scheme == "https" and parsed.netloc:
            return uri
        if parsed.scheme == "http" and parsed.hostname in {"localhost", "127.0.0.1", "::1"} and parsed.netloc:
            return uri
        raise OAuthError("invalid redirect URI", code="invalid_client_metadata")

    def register_client(self, payload: dict) -> dict:
        self._cleanup()
        if not isinstance(payload, dict):
            raise OAuthError("invalid client metadata", code="invalid_client_metadata")
        auth_method = payload.get("token_endpoint_auth_method", "none")
        if auth_method != "none":
            raise OAuthError("only public clients are supported", code="invalid_client_metadata")
        redirect_uris = payload.get("redirect_uris")
        if not isinstance(redirect_uris, list) or not 1 <= len(redirect_uris) <= 5:
            raise OAuthError("redirect_uris is required", code="invalid_client_metadata")
        redirects = tuple(dict.fromkeys(self._validate_redirect(str(uri)) for uri in redirect_uris))
        grant_types = tuple(payload.get("grant_types") or ["authorization_code"])
        if "authorization_code" not in grant_types or not set(grant_types).issubset({"authorization_code", "refresh_token"}):
            raise OAuthError("unsupported grant type", code="invalid_client_metadata")
        response_types = tuple(payload.get("response_types") or ["code"])
        if response_types != ("code",):
            raise OAuthError("only code response type is supported", code="invalid_client_metadata")
        requested_scope = str(payload.get("scope") or self.scope)
        if set(requested_scope.split()) != {self.scope}:
            raise OAuthError("unsupported scope", code="invalid_client_metadata")
        client_id = secrets.token_urlsafe(24)
        client = _Client(
            client_id=client_id,
            redirect_uris=redirects,
            grant_types=grant_types,
            scope=self.scope,
            client_name=str(payload.get("client_name") or "MCP client")[:120],
        )
        with self._lock:
            self._clients[client_id] = client
        return {
            "client_id": client_id,
            "client_id_issued_at": int(time.time()),
            "client_name": client.client_name,
            "redirect_uris": list(client.redirect_uris),
            "grant_types": list(client.grant_types),
            "response_types": ["code"],
            "token_endpoint_auth_method": "none",
            "scope": self.scope,
        }

    def client(self, client_id: str) -> _Client:
        self._cleanup()
        with self._lock:
            client = self._clients.get(client_id)
        if client is None:
            raise OAuthError("unknown client", code="invalid_client")
        return client

    def validate_authorization_request(
        self, *, client_id: str, redirect_uri: str, response_type: str, scope: str, code_challenge: str, code_challenge_method: str,
    ) -> _Client:
        client = self.client(client_id)
        if response_type != "code" or redirect_uri not in client.redirect_uris:
            raise OAuthError("invalid authorization request", code="invalid_request")
        if set(scope.split()) != {self.scope}:
            raise OAuthError("invalid scope", code="invalid_scope")
        if code_challenge_method != "S256" or not code_challenge or len(code_challenge) > 128:
            raise OAuthError("PKCE S256 is required", code="invalid_request")
        return client

    def create_authorization_code(self, *, client_id: str, redirect_uri: str, scope: str, code_challenge: str) -> str:
        self.validate_authorization_request(
            client_id=client_id,
            redirect_uri=redirect_uri,
            response_type="code",
            scope=scope,
            code_challenge=code_challenge,
            code_challenge_method="S256",
        )
        code = secrets.token_urlsafe(32)
        with self._lock:
            self._codes[code] = _Code(
                client_id=client_id,
                redirect_uri=redirect_uri,
                scope=self.scope,
                code_challenge=code_challenge,
                expires_at=int(time.time()) + self.settings.oauth_code_ttl_seconds,
            )
        return code

    def issue_access_token(self, *, client_id: str, subject: str, scopes: list[str] | None = None) -> str:
        scopes = scopes or [self.scope]
        if scopes != [self.scope] and set(scopes) != {self.scope}:
            raise OAuthError("unsupported scope", code="invalid_scope")
        now = int(time.time())
        payload = {
            "iss": self.settings.public_base_url,
            "aud": self.settings.public_base_url,
            "sub": subject[:128],
            "client_id": client_id[:128],
            "scope": self.scope,
            "iat": now,
            "exp": now + self.settings.oauth_token_ttl_seconds,
            "jti": secrets.token_urlsafe(16),
        }
        header = {"alg": "HS256", "typ": "at+jwt"}
        signing_input = f"{_json_b64(header)}.{_json_b64(payload)}".encode("ascii")
        signature = hmac.new(self.settings.oauth_signing_key.encode("utf-8"), signing_input, hashlib.sha256).digest()
        return f"{signing_input.decode('ascii')}.{_b64(signature)}"

    def _issue_refresh_token(self, *, client_id: str, subject: str, scope: str) -> str:
        token = secrets.token_urlsafe(48)
        with self._lock:
            self._refresh_tokens[token] = _Refresh(
                client_id=client_id,
                subject=subject,
                scope=scope,
                expires_at=int(time.time()) + 30 * 24 * 3600,
            )
        return token

    def exchange_code(self, *, code: str, client_id: str, redirect_uri: str, code_verifier: str) -> str:
        self._cleanup()
        with self._lock:
            entry = self._codes.get(code)
            client = self._clients.get(client_id)
            if entry is None or entry.used or client is None:
                raise OAuthError("invalid authorization code", code="invalid_grant")
            if entry.client_id != client_id or entry.redirect_uri != redirect_uri:
                raise OAuthError("invalid authorization code", code="invalid_grant")
            try:
                expected = _b64(hashlib.sha256(code_verifier.encode("ascii")).digest()) if code_verifier else ""
            except UnicodeEncodeError as exc:
                raise OAuthError("PKCE verification failed", code="invalid_grant") from exc
            if not hmac.compare_digest(expected, entry.code_challenge):
                raise OAuthError("PKCE verification failed", code="invalid_grant")
            entry.used = True
        return self.issue_access_token(client_id=client_id, subject=client.client_name)

    def exchange_code_bundle(self, *, code: str, client_id: str, redirect_uri: str, code_verifier: str) -> dict:
        access_token = self.exchange_code(code=code, client_id=client_id, redirect_uri=redirect_uri, code_verifier=code_verifier)
        client = self.client(client_id)
        result = {
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_in": self.settings.oauth_token_ttl_seconds,
            "scope": self.scope,
        }
        if "refresh_token" in client.grant_types:
            result["refresh_token"] = self._issue_refresh_token(client_id=client_id, subject=client.client_name, scope=self.scope)
        return result

    def refresh_bundle(self, *, refresh_token: str, client_id: str) -> dict:
        self._cleanup()
        with self._lock:
            entry = self._refresh_tokens.pop(refresh_token, None)
        if entry is None or entry.client_id != client_id:
            raise OAuthError("invalid refresh token", code="invalid_grant")
        access_token = self.issue_access_token(client_id=client_id, subject=entry.subject)
        new_refresh = self._issue_refresh_token(client_id=client_id, subject=entry.subject, scope=entry.scope)
        return {
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_in": self.settings.oauth_token_ttl_seconds,
            "scope": self.scope,
            "refresh_token": new_refresh,
        }

    def verify_token(self, token: str) -> AccessToken | None:
        try:
            header_b64, payload_b64, signature_b64 = token.split(".")
            signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
            expected = hmac.new(self.settings.oauth_signing_key.encode("utf-8"), signing_input, hashlib.sha256).digest()
            if not hmac.compare_digest(expected, _unb64(signature_b64)):
                return None
            header = json.loads(_unb64(header_b64))
            payload = json.loads(_unb64(payload_b64))
            now = int(time.time())
            if header.get("alg") != "HS256" or payload.get("iss") != self.settings.public_base_url or payload.get("aud") != self.settings.public_base_url:
                return None
            if not isinstance(payload.get("exp"), int) or payload["exp"] <= now:
                return None
            if payload.get("scope") != self.scope or not payload.get("client_id"):
                return None
            return AccessToken(
                token=token,
                client_id=str(payload["client_id"]),
                scopes=[self.scope],
                expires_at=int(payload["exp"]),
                resource=self.settings.public_base_url,
                subject=str(payload.get("sub") or ""),
                claims=payload,
            )
        except (ValueError, TypeError, KeyError, UnicodeError, json.JSONDecodeError):
            return None

    def authorization_form(self, *, query: dict[str, str]) -> str:
        fields = {
            key: query.get(key, "")
            for key in ("client_id", "redirect_uri", "response_type", "scope", "state", "code_challenge", "code_challenge_method", "resource")
        }
        hidden = "".join(
            f'<input type="hidden" name="{html.escape(key)}" value="{html.escape(value)}">'
            for key, value in fields.items()
        )
        return (
            "<!doctype html><meta charset='utf-8'><title>Hermes MCP authorization</title>"
            "<h1>Authorize Hermes read-only access</h1>"
            "<p>This grants ChatGPT read-only Kanban access.</p>"
            '<form method="post" action="/oauth/authorize">'
            f"{hidden}<label>Username <input name='username' autocomplete='username'></label>"
            "<label>Password <input type='password' name='password' autocomplete='current-password'></label>"
            "<button type='submit'>Authorize</button></form>"
        )


class BearerTokenVerifier:
    """Async MCP SDK bridge for the synchronous, bounded token verifier."""

    def __init__(self, service: AuthService) -> None:
        self.service = service

    async def verify_token(self, token: str) -> AccessToken | None:
        return self.service.verify_token(token)
