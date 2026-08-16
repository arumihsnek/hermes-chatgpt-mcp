from __future__ import annotations

import base64
import hashlib
import hmac
import html
import json
import os
import secrets
import stat
import threading
import time
from dataclasses import dataclass
from pathlib import Path
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
    issued_at: int


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

    Dynamic client registrations and refresh-token rotation state are persisted
    when ``Settings.oauth_state_file`` is configured. Authorization codes stay
    short-lived and in memory; access tokens are signed and self-contained.
    """

    scope = "hermes:read"
    read_scope = scope
    create_scope = "hermes:create"
    supported_scopes = (scope, create_scope)
    _state_version = 1

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._clients: dict[str, _Client] = {}
        self._codes: dict[str, _Code] = {}
        self._refresh_tokens: dict[str, _Refresh] = {}
        self._lock = threading.RLock()
        self._state_path = Path(settings.oauth_state_file).expanduser() if settings.oauth_state_file else None
        self._load_persistent_state()

    @staticmethod
    def _refresh_digest(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    @classmethod
    def _scope_string(
        cls,
        value: str | None,
        *,
        default: str | None = None,
        allowed: set[str] | None = None,
    ) -> str:
        raw = (value or default or "").split()
        scopes = tuple(dict.fromkeys(raw))
        allowed_scopes = allowed or set(cls.supported_scopes)
        if not scopes or not set(scopes).issubset(allowed_scopes):
            raise OAuthError("unsupported scope", code="invalid_scope")
        if cls.create_scope in scopes and cls.read_scope not in scopes:
            raise OAuthError("hermes:create requires hermes:read", code="invalid_scope")
        return " ".join(scope for scope in cls.supported_scopes if scope in scopes)

    @staticmethod
    def _client_from_state(value: object) -> _Client | None:
        if not isinstance(value, dict):
            return None
        if not isinstance(value.get("redirect_uris"), list) or not isinstance(value.get("grant_types"), list):
            return None
        try:
            client_id = str(value["client_id"])
            redirects = tuple(str(item) for item in value["redirect_uris"])
            grants = tuple(str(item) for item in value["grant_types"])
            scope = str(value["scope"])
            client_name = str(value["client_name"])
            issued_at = int(value["issued_at"])
        except (KeyError, TypeError, ValueError):
            return None
        if not client_id or not redirects or not grants or not scope:
            return None
        return _Client(client_id, redirects, grants, scope, client_name[:120], issued_at)

    @staticmethod
    def _refresh_from_state(value: object) -> _Refresh | None:
        if not isinstance(value, dict):
            return None
        try:
            return _Refresh(
                client_id=str(value["client_id"]),
                subject=str(value["subject"]),
                scope=str(value["scope"]),
                expires_at=int(value["expires_at"]),
            )
        except (KeyError, TypeError, ValueError):
            return None

    def _load_persistent_state(self) -> None:
        path = self._state_path
        if path is None or not path.exists():
            return
        try:
            mode = stat.S_IMODE(path.stat().st_mode)
            if mode & 0o077:
                raise RuntimeError("OAuth state file permissions are too broad")
            payload = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict) or payload.get("version") != self._state_version:
                raise RuntimeError("OAuth state file version is unsupported")
            clients = payload.get("clients", {})
            refresh_tokens = payload.get("refresh_tokens", {})
            if not isinstance(clients, dict) or not isinstance(refresh_tokens, dict):
                raise RuntimeError("OAuth state file shape is invalid")
            loaded_clients: dict[str, _Client] = {}
            for client_id, raw in clients.items():
                client = self._client_from_state(raw)
                if client is None or str(client_id) != client.client_id:
                    raise RuntimeError("OAuth state contains an invalid client")
                self._scope_string(client.scope, allowed=set(self.supported_scopes))
                if client.grant_types != ("authorization_code",) and set(client.grant_types) != {"authorization_code", "refresh_token"}:
                    raise RuntimeError("OAuth state contains an invalid grant")
                for redirect in client.redirect_uris:
                    self._validate_redirect(redirect)
                loaded_clients[client.client_id] = client
            loaded_refresh: dict[str, _Refresh] = {}
            for digest, raw in refresh_tokens.items():
                if not isinstance(digest, str) or len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
                    raise RuntimeError("OAuth state contains an invalid refresh token record")
                refresh = self._refresh_from_state(raw)
                if refresh is None or refresh.client_id not in loaded_clients:
                    raise RuntimeError("OAuth state contains an invalid refresh token record")
                self._scope_string(refresh.scope, allowed=set(loaded_clients[refresh.client_id].scope.split()))
                loaded_refresh[digest] = refresh
        except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
            raise RuntimeError("OAuth state file cannot be loaded") from exc
        with self._lock:
            self._clients.update(loaded_clients)
            self._refresh_tokens.update(loaded_refresh)

    def _persist_locked(self) -> None:
        path = self._state_path
        if path is None:
            return
        parent = path.parent
        parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        os.chmod(parent, 0o700)
        payload = {
            "version": self._state_version,
            "clients": {
                client_id: {
                    "client_id": client.client_id,
                    "redirect_uris": list(client.redirect_uris),
                    "grant_types": list(client.grant_types),
                    "scope": client.scope,
                    "client_name": client.client_name,
                    "issued_at": client.issued_at,
                }
                for client_id, client in self._clients.items()
            },
            "refresh_tokens": {
                digest: {
                    "client_id": refresh.client_id,
                    "subject": refresh.subject,
                    "scope": refresh.scope,
                    "expires_at": refresh.expires_at,
                }
                for digest, refresh in self._refresh_tokens.items()
            },
        }
        temporary = path.with_name(f".{path.name}.{secrets.token_hex(8)}.tmp")
        try:
            with temporary.open("w", encoding="utf-8") as handle:
                os.chmod(temporary, 0o600)
                json.dump(payload, handle, separators=(",", ":"), sort_keys=True)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
            os.chmod(path, 0o600)
        finally:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass

    def _cleanup(self) -> None:
        now = int(time.time())
        with self._lock:
            old_client_count = len(self._clients)
            old_refresh_count = len(self._refresh_tokens)
            self._codes = {key: value for key, value in self._codes.items() if value.expires_at >= now and not value.used}
            self._refresh_tokens = {key: value for key, value in self._refresh_tokens.items() if value.expires_at >= now}
            if len(self._clients) > 64:
                for client_id in list(self._clients)[: len(self._clients) - 64]:
                    self._clients.pop(client_id, None)
            if old_client_count != len(self._clients) or old_refresh_count != len(self._refresh_tokens):
                self._persist_locked()

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
        raw_grant_types = payload.get("grant_types") or ["authorization_code"]
        if not isinstance(raw_grant_types, list):
            raise OAuthError("grant_types must be a list", code="invalid_client_metadata")
        grant_types = tuple(str(value) for value in raw_grant_types)
        if "authorization_code" not in grant_types or not set(grant_types).issubset({"authorization_code", "refresh_token"}):
            raise OAuthError("unsupported grant type", code="invalid_client_metadata")
        raw_response_types = payload.get("response_types") or ["code"]
        if not isinstance(raw_response_types, list):
            raise OAuthError("response_types must be a list", code="invalid_client_metadata")
        response_types = tuple(str(value) for value in raw_response_types)
        if response_types != ("code",):
            raise OAuthError("only code response type is supported", code="invalid_client_metadata")
        try:
            requested_scope = self._scope_string(str(payload.get("scope") or self.scope))
        except OAuthError as exc:
            raise OAuthError(str(exc), code="invalid_client_metadata") from exc
        client_id = secrets.token_urlsafe(24)
        issued_at = int(time.time())
        client = _Client(
            client_id=client_id,
            redirect_uris=redirects,
            grant_types=grant_types,
            scope=requested_scope,
            client_name=str(payload.get("client_name") or "MCP client")[:120],
            issued_at=issued_at,
        )
        with self._lock:
            self._clients[client_id] = client
            self._persist_locked()
        return {
            "client_id": client_id,
            "client_id_issued_at": issued_at,
            "client_name": client.client_name,
            "redirect_uris": list(client.redirect_uris),
            "grant_types": list(client.grant_types),
            "response_types": ["code"],
            "token_endpoint_auth_method": "none",
            "scope": client.scope,
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
        self._scope_string(scope, default=client.scope, allowed=set(client.scope.split()))
        if code_challenge_method != "S256" or not code_challenge or len(code_challenge) > 128:
            raise OAuthError("PKCE S256 is required", code="invalid_request")
        return client

    def create_authorization_code(self, *, client_id: str, redirect_uri: str, scope: str, code_challenge: str) -> str:
        client = self.validate_authorization_request(
            client_id=client_id,
            redirect_uri=redirect_uri,
            response_type="code",
            scope=scope,
            code_challenge=code_challenge,
            code_challenge_method="S256",
        )
        scope_value = self._scope_string(scope, default=client.scope, allowed=set(client.scope.split()))
        code = secrets.token_urlsafe(32)
        with self._lock:
            self._codes[code] = _Code(
                client_id=client_id,
                redirect_uri=redirect_uri,
                scope=scope_value,
                code_challenge=code_challenge,
                expires_at=int(time.time()) + self.settings.oauth_code_ttl_seconds,
            )
        return code

    def issue_access_token(self, *, client_id: str, subject: str, scopes: list[str] | None = None) -> str:
        scope_value = self._scope_string(" ".join(scopes or [self.scope]))
        now = int(time.time())
        payload = {
            "iss": self.settings.public_base_url,
            "aud": self.settings.public_base_url,
            "sub": subject[:128],
            "client_id": client_id[:128],
            "scope": scope_value,
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
            self._refresh_tokens[self._refresh_digest(token)] = _Refresh(
                client_id=client_id,
                subject=subject,
                scope=scope,
                expires_at=int(time.time()) + 30 * 24 * 3600,
            )
            self._persist_locked()
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
        return self.issue_access_token(
            client_id=client_id,
            subject=client.client_name,
            scopes=entry.scope.split(),
        )

    def exchange_code_bundle(self, *, code: str, client_id: str, redirect_uri: str, code_verifier: str) -> dict:
        access_token = self.exchange_code(code=code, client_id=client_id, redirect_uri=redirect_uri, code_verifier=code_verifier)
        client = self.client(client_id)
        result = {
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_in": self.settings.oauth_token_ttl_seconds,
            "scope": " ".join(self.verify_token(access_token).scopes),  # type: ignore[union-attr]
        }
        if "refresh_token" in client.grant_types:
            result["refresh_token"] = self._issue_refresh_token(
                client_id=client_id,
                subject=client.client_name,
                scope=result["scope"],
            )
        return result

    def refresh_bundle(self, *, refresh_token: str, client_id: str) -> dict:
        self._cleanup()
        with self._lock:
            entry = self._refresh_tokens.pop(self._refresh_digest(refresh_token), None)
            if entry is not None:
                self._persist_locked()
        if entry is None or entry.client_id != client_id:
            raise OAuthError("invalid refresh token", code="invalid_grant")
        access_token = self.issue_access_token(
            client_id=client_id,
            subject=entry.subject,
            scopes=entry.scope.split(),
        )
        new_refresh = self._issue_refresh_token(client_id=client_id, subject=entry.subject, scope=entry.scope)
        return {
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_in": self.settings.oauth_token_ttl_seconds,
            "scope": " ".join(self.verify_token(access_token).scopes),  # type: ignore[union-attr]
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
            scope_value = self._scope_string(str(payload.get("scope") or ""))
            if not payload.get("client_id"):
                return None
            return AccessToken(
                token=token,
                client_id=str(payload["client_id"]),
                scopes=scope_value.split(),
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
            "<h1>Authorize Hermes MCP access</h1>"
            "<p>This grants ChatGPT read-only Kanban access and, when requested, the separate task-creation scope.</p>"
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
