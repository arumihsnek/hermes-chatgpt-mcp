from __future__ import annotations

import base64
import hashlib
import hmac
import html
import json
import os
import re
import secrets
import stat
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from mcp.server.auth.provider import AccessToken

from .config import Settings
from .diagnostics import emit, fingerprint, redirect_identity, request_fingerprint, scope_summary


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
    grant_id: str
    board: str | None = None
    board_access: str | None = None
    used: bool = False


@dataclass
class _Refresh:
    client_id: str
    subject: str
    scope: str
    expires_at: int
    grant_id: str
    board: str | None = None
    board_access: str | None = None


@dataclass(frozen=True)
class AuthPolicy:
    read_scope: str
    create_scope: str
    manage_scope: str
    board_create_scope: str
    offline_scope: str
    supported_scopes: tuple[str, ...]
    registration_defaults: tuple[str, ...]


STABLE_AUTH_POLICY = AuthPolicy(
    read_scope="hermes:read",
    create_scope="hermes:create",
    manage_scope="hermes:manage",
    board_create_scope="hermes:board:create",
    offline_scope="offline_access",
    supported_scopes=("hermes:read", "hermes:create", "offline_access"),
    registration_defaults=("hermes:read", "hermes:create"),
)

BETA_AUTH_POLICY = AuthPolicy(
    read_scope="hermes:read",
    create_scope="hermes:create",
    manage_scope="hermes:manage",
    board_create_scope="hermes:board:create",
    offline_scope="offline_access",
    supported_scopes=("hermes:read", "hermes:create", "hermes:manage", "hermes:board:create", "offline_access"),
    registration_defaults=("hermes:read", "hermes:create"),
)


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
    offline_scope = "offline_access"
    supported_scopes = (scope, create_scope, offline_scope)
    _state_version = 2
    _board_pattern = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")

    def __init__(self, settings: Settings, policy: AuthPolicy | None = None) -> None:
        self.settings = settings
        policy = policy or (BETA_AUTH_POLICY if settings.surface == "beta" else STABLE_AUTH_POLICY)
        self.policy = policy
        self.scope = policy.read_scope
        self.read_scope = policy.read_scope
        self.create_scope = policy.create_scope
        self.manage_scope = policy.manage_scope
        self.board_create_scope = policy.board_create_scope
        self.offline_scope = policy.offline_scope
        self.supported_scopes = policy.supported_scopes
        self._clients: dict[str, _Client] = {}
        self._codes: dict[str, _Code] = {}
        self._refresh_tokens: dict[str, _Refresh] = {}
        self._revoked_grants: set[str] = set()
        self._lock = threading.RLock()
        self._state_path = Path(settings.oauth_state_file).expanduser() if settings.oauth_state_file else None
        self._load_persistent_state()

    @staticmethod
    def _refresh_digest(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    @staticmethod
    def _token_payload(token: str) -> dict[str, object] | None:
        try:
            _, payload_b64, _ = token.split(".")
            payload = json.loads(_unb64(payload_b64))
            return payload if isinstance(payload, dict) else None
        except (ValueError, TypeError, UnicodeError, json.JSONDecodeError):
            return None

    def verified_claims(self, token: str) -> dict[str, object] | None:
        """Return non-secret claims for a valid token, for internal policy checks."""
        if self.verify_token(token) is None:
            return None
        return self._token_payload(token)

    def _scope_string(
        self,
        value: str | None,
        *,
        default: str | None = None,
        allowed: set[str] | None = None,
    ) -> str:
        raw = (value or default or "").split()
        scopes = tuple(dict.fromkeys(raw))
        allowed_scopes = allowed or set(self.supported_scopes)
        if not scopes or not set(scopes).issubset(allowed_scopes):
            raise OAuthError("unsupported scope", code="invalid_scope")
        if self.create_scope in scopes and self.read_scope not in scopes:
            raise OAuthError("hermes:create requires hermes:read", code="invalid_scope")
        if self.manage_scope in scopes and self.read_scope not in scopes:
            raise OAuthError("hermes:manage requires hermes:read", code="invalid_scope")
        if self.board_create_scope in scopes and self.read_scope not in scopes:
            raise OAuthError("hermes:board:create requires hermes:read", code="invalid_scope")
        return " ".join(scope for scope in self.supported_scopes if scope in scopes)

    def _validate_grant(self, scope_value: str, board: str | None, board_access: str | None) -> None:
        scopes = set(scope_value.split())
        command_scopes = {self.create_scope, self.manage_scope}
        has_command_scope = bool(scopes & command_scopes)
        has_board_administration_scope = self.board_create_scope in scopes
        if board_access not in {None, "write"}:
            raise OAuthError("invalid board access", code="invalid_request")
        if has_board_administration_scope:
            if has_command_scope or board is not None or board_access is not None:
                raise OAuthError("board administration cannot carry a board claim", code="invalid_scope")
            return
        if has_command_scope:
            if board is None or board_access != "write":
                raise OAuthError("command scope requires a selected board", code="invalid_scope")
            return
        if board is not None or board_access is not None:
            raise OAuthError("board grant must be write access", code="invalid_request")

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

    @classmethod
    def _validate_board(cls, board: str | None) -> str | None:
        if board is None:
            return None
        if not isinstance(board, str) or not cls._board_pattern.fullmatch(board):
            raise OAuthError("invalid board", code="invalid_request")
        return board

    @classmethod
    def _refresh_from_state(cls, value: object, digest: str) -> _Refresh | None:
        if not isinstance(value, dict):
            return None
        try:
            board = value.get("board")
            if board is not None:
                board = cls._validate_board(str(board))
            board_access = value.get("board_access")
            if board_access is not None and board_access != "write":
                return None
            return _Refresh(
                client_id=str(value["client_id"]),
                subject=str(value["subject"]),
                scope=str(value["scope"]),
                expires_at=int(value["expires_at"]),
                grant_id=str(value.get("grant_id") or f"legacy-{digest[:24]}"),
                board=board,
                board_access=board_access,
            )
        except (KeyError, TypeError, ValueError):
            return None

    def _load_persistent_state(self) -> None:
        path = self._state_path
        if path is None or not path.exists():
            return
        migrate_state = False
        try:
            mode = stat.S_IMODE(path.stat().st_mode)
            if mode & 0o077:
                raise RuntimeError("OAuth state file permissions are too broad")
            payload = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict) or payload.get("version") not in {1, self._state_version}:
                raise RuntimeError("OAuth state file version is unsupported")
            migrate_state = payload.get("version") != self._state_version
            clients = payload.get("clients", {})
            refresh_tokens = payload.get("refresh_tokens", {})
            revoked_grants = payload.get("revoked_grants", [])
            if not isinstance(clients, dict) or not isinstance(refresh_tokens, dict) or not isinstance(revoked_grants, list):
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
                refresh = self._refresh_from_state(raw, digest)
                if refresh is None or refresh.client_id not in loaded_clients:
                    raise RuntimeError("OAuth state contains an invalid refresh token record")
                normalized_scope = self._scope_string(refresh.scope, allowed=set(self.supported_scopes))
                if normalized_scope != refresh.scope:
                    refresh.scope = normalized_scope
                    migrate_state = True
                try:
                    self._validate_grant(normalized_scope, refresh.board, refresh.board_access)
                except OAuthError:
                    migrate_state = True
                    continue
                loaded_refresh[digest] = refresh
            loaded_revoked = {str(grant) for grant in revoked_grants if isinstance(grant, str) and grant}
        except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
            raise RuntimeError("OAuth state file cannot be loaded") from exc
        with self._lock:
            self._clients.update(loaded_clients)
            self._refresh_tokens.update(loaded_refresh)
            self._revoked_grants.update(loaded_revoked)
            if migrate_state:
                self._persist_locked()

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
                    "grant_id": refresh.grant_id,
                    "board": refresh.board,
                    "board_access": refresh.board_access,
                }
                for digest, refresh in self._refresh_tokens.items()
            },
            "revoked_grants": sorted(self._revoked_grants),
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
            raw_scope = payload.get("scope")
            if raw_scope:
                requested_scope = self._scope_string(str(raw_scope))
            else:
                default_scopes = list(self.policy.registration_defaults)
                if "refresh_token" in grant_types:
                    default_scopes.append(self.offline_scope)
                requested_scope = self._scope_string(" ".join(default_scopes))
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
        emit(
            self.settings,
            "dcr",
            client_fp=fingerprint(client_id),
            requested_scopes=scope_summary(payload.get("scope") or self.read_scope, self.supported_scopes),
            granted_scopes=scope_summary(requested_scope, self.supported_scopes),
            allowed_scopes=scope_summary(requested_scope, self.supported_scopes),
            redirect=redirect_identity(redirects[0]),
            grant_types=",".join(grant_types),
            new_registration=True,
            client_reused=False,
            outcome="success",
        )
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
        # DCR scope metadata supplies the client's default scope.  The
        # resource owner's authorization request may ask for any scope that
        # this authorization server supports; the issued token still contains
        # only the scopes explicitly requested and approved here.
        self._scope_string(scope, default=client.scope, allowed=set(self.supported_scopes))
        if code_challenge_method != "S256" or not code_challenge or len(code_challenge) > 128:
            raise OAuthError("PKCE S256 is required", code="invalid_request")
        return client

    def create_authorization_code(
        self,
        *,
        client_id: str,
        redirect_uri: str,
        scope: str,
        code_challenge: str,
        board: str | None = None,
        write_grant: bool = False,
    ) -> str:
        client = self.validate_authorization_request(
            client_id=client_id,
            redirect_uri=redirect_uri,
            response_type="code",
            scope=scope,
            code_challenge=code_challenge,
            code_challenge_method="S256",
        )
        scope_value = self._scope_string(scope, default=client.scope, allowed=set(self.supported_scopes))
        board = self._validate_board(board)
        command_scopes = {self.create_scope, self.manage_scope}
        if write_grant:
            if board is None or not (command_scopes & set(scope_value.split())):
                raise OAuthError("write board grant requires a command scope and board", code="invalid_scope")
            board_access = "write"
        else:
            board_access = None
        self._validate_grant(scope_value, board, board_access)
        grant_id = secrets.token_urlsafe(18)
        code = secrets.token_urlsafe(32)
        flow_fp = request_fingerprint(client_id, redirect_uri, scope_value, code_challenge)
        with self._lock:
            self._codes[code] = _Code(
                client_id=client_id,
                redirect_uri=redirect_uri,
                scope=scope_value,
                code_challenge=code_challenge,
                expires_at=int(time.time()) + self.settings.oauth_code_ttl_seconds,
                grant_id=grant_id,
                board=board,
                board_access=board_access,
            )
        emit(
            self.settings,
            "authorize.grant",
            client_fp=fingerprint(client_id),
            flow_fp=flow_fp,
            code_fp=fingerprint(code),
            requested_scopes=scope_summary(scope, self.supported_scopes),
            allowed_scopes=scope_summary(" ".join(self.supported_scopes), self.supported_scopes),
            granted_scopes=scope_summary(scope_value, self.supported_scopes),
            board=board,
            board_access=board_access,
            grant_fp=fingerprint(grant_id),
            redirect=redirect_identity(redirect_uri),
            client_reused=True,
            grant_reused=False,
            outcome="success",
        )
        return code

    def issue_access_token(
        self,
        *,
        client_id: str,
        subject: str,
        scopes: list[str] | None = None,
        board: str | None = None,
        board_access: str | None = None,
        grant_id: str | None = None,
    ) -> str:
        scope_value = self._scope_string(" ".join(scopes or [self.scope]))
        board = self._validate_board(board)
        self._validate_grant(scope_value, board, board_access)
        grant_id = grant_id or secrets.token_urlsafe(18)
        with self._lock:
            revoked = grant_id in self._revoked_grants
        if revoked:
            raise OAuthError("grant revoked", code="invalid_grant")
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
            "grant_id": grant_id,
        }
        if board is not None:
            payload["board"] = board
            payload["board_access"] = board_access
        header = {"alg": "HS256", "typ": "at+jwt"}
        signing_input = f"{_json_b64(header)}.{_json_b64(payload)}".encode("ascii")
        signature = hmac.new(self.settings.oauth_signing_key.encode("utf-8"), signing_input, hashlib.sha256).digest()
        return f"{signing_input.decode('ascii')}.{_b64(signature)}"

    def _issue_refresh_token(
        self,
        *,
        client_id: str,
        subject: str,
        scope: str,
        grant_id: str,
        board: str | None = None,
        board_access: str | None = None,
    ) -> str:
        token = secrets.token_urlsafe(48)
        with self._lock:
            self._refresh_tokens[self._refresh_digest(token)] = _Refresh(
                client_id=client_id,
                subject=subject,
                scope=scope,
                expires_at=int(time.time()) + 30 * 24 * 3600,
                grant_id=grant_id,
                board=board,
                board_access=board_access,
            )
            self._persist_locked()
        emit(
            self.settings,
            "token.refresh.issue",
            client_fp=fingerprint(client_id),
            refresh_fp=fingerprint(token),
            granted_scopes=scope_summary(scope, self.supported_scopes),
            outcome="success",
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
        access_token = self.issue_access_token(
            client_id=client_id,
            subject=client.client_name,
            scopes=entry.scope.split(),
            board=entry.board,
            board_access=entry.board_access,
            grant_id=entry.grant_id,
        )
        emit(
            self.settings,
            "token.authorization_code",
            client_fp=fingerprint(client_id),
            flow_fp=request_fingerprint(client_id, entry.redirect_uri, entry.scope, entry.code_challenge),
            code_fp=fingerprint(code),
            token_fp=fingerprint(access_token),
            granted_scopes=scope_summary(entry.scope, self.supported_scopes),
            effective_scopes=scope_summary(entry.scope, self.supported_scopes),
            outcome="success",
        )
        return access_token

    def exchange_code_bundle(self, *, code: str, client_id: str, redirect_uri: str, code_verifier: str) -> dict:
        access_token = self.exchange_code(code=code, client_id=client_id, redirect_uri=redirect_uri, code_verifier=code_verifier)
        client = self.client(client_id)
        access = self.verify_token(access_token)
        claims = self.verified_claims(access_token)
        if access is None or claims is None:
            raise OAuthError("issued token could not be verified", code="invalid_grant")
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
                grant_id=str(claims.get("grant_id") or ""),
                board=claims.get("board") if isinstance(claims.get("board"), str) else None,
                board_access=claims.get("board_access") if isinstance(claims.get("board_access"), str) else None,
            )
        return result

    def refresh_bundle(self, *, refresh_token: str, client_id: str) -> dict:
        self._cleanup()
        with self._lock:
            digest = self._refresh_digest(refresh_token)
            entry = self._refresh_tokens.get(digest)
            if entry is not None and entry.client_id == client_id:
                self._refresh_tokens.pop(digest, None)
            elif entry is not None:
                entry = None
            if entry is not None:
                self._persist_locked()
        if entry is None or entry.client_id != client_id:
            emit(
                self.settings,
                "token.refresh.exchange",
                client_fp=fingerprint(client_id),
                refresh_fp=fingerprint(refresh_token),
                outcome="invalid_grant",
            )
            raise OAuthError("invalid refresh token", code="invalid_grant")
        access_token = self.issue_access_token(
            client_id=client_id,
            subject=entry.subject,
            scopes=entry.scope.split(),
            board=entry.board,
            board_access=entry.board_access,
            grant_id=entry.grant_id,
        )
        new_refresh = self._issue_refresh_token(
            client_id=client_id,
            subject=entry.subject,
            scope=entry.scope,
            grant_id=entry.grant_id,
            board=entry.board,
            board_access=entry.board_access,
        )
        emit(
            self.settings,
            "token.refresh.exchange",
            client_fp=fingerprint(client_id),
            refresh_fp=fingerprint(refresh_token),
            new_refresh_fp=fingerprint(new_refresh),
            token_fp=fingerprint(access_token),
            original_scopes=scope_summary(entry.scope, self.supported_scopes),
            effective_scopes=scope_summary(entry.scope, self.supported_scopes),
            outcome="success",
        )
        return {
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_in": self.settings.oauth_token_ttl_seconds,
            "scope": " ".join(self.verify_token(access_token).scopes),  # type: ignore[union-attr]
            "refresh_token": new_refresh,
        }

    def revoke_token(self, token: str, *, client_id: str | None = None) -> None:
        """Revoke an access or refresh token without revealing token state."""
        grant_id: str | None = None
        digest = self._refresh_digest(token)
        with self._lock:
            refresh = self._refresh_tokens.get(digest)
            if refresh is not None and (client_id is None or refresh.client_id == client_id):
                grant_id = refresh.grant_id
                self._refresh_tokens = {
                    key: value for key, value in self._refresh_tokens.items()
                    if value.grant_id != grant_id
                }
        if grant_id is None:
            access = self.verify_token(token)
            claims = self.verified_claims(token)
            if access is not None and claims is not None and (client_id is None or access.client_id == client_id):
                candidate = claims.get("grant_id")
                if isinstance(candidate, str) and candidate:
                    grant_id = candidate
        if grant_id is not None:
            with self._lock:
                self._revoked_grants.add(grant_id)
                self._persist_locked()

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
            grant_id = payload.get("grant_id")
            if grant_id is not None:
                if not isinstance(grant_id, str):
                    return None
                with self._lock:
                    if grant_id in self._revoked_grants:
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

    def authorization_form(
        self,
        *,
        query: dict[str, str],
        board_options: list[dict[str, str]] | None = None,
        default_board: str | None = None,
    ) -> str:
        fields = {
            key: query.get(key, "")
            for key in ("client_id", "redirect_uri", "response_type", "scope", "state", "code_challenge", "code_challenge_method", "resource")
        }
        hidden = "".join(
            f'<input type="hidden" name="{html.escape(key)}" value="{html.escape(value)}">'
            for key, value in fields.items()
        )
        options = board_options or []
        default = default_board if any(item.get("slug") == default_board for item in options) else (options[0].get("slug") if options else "")
        option_parts: list[str] = []
        for item in options:
            slug = str(item.get("slug") or "")
            selected = " selected" if slug == default else ""
            option_parts.append(
                f'<option value="{html.escape(slug)}"{selected}>'
                f'{html.escape(str(item.get("name") or slug))}</option>'
            )
        board_select = "".join(option_parts)
        write_available = self.create_scope in query.get("scope", "").split()
        access_controls = (
            "<fieldset><legend>Access</legend>"
            "<label><input type='radio' name='access_mode' value='read' checked> Read all boards</label>"
            "<label><input type='radio' name='access_mode' value='write'> Read all boards and write one selected board</label>"
            f"<label>Write board <select name='board'>{board_select}</select></label></fieldset>"
            if write_available and options
            else "<p>read-only access to all boards.</p>"
        )
        return (
            "<!doctype html><meta charset='utf-8'><title>Hermes MCP authorization</title>"
            "<h1>Authorize Hermes MCP access</h1>"
            "<p>read-only access covers all active Hermes boards. Write access is limited to one board selected below.</p>"
            '<form method="post" action="/oauth/authorize">'
            f"{hidden}{access_controls}<label>Username <input name='username' autocomplete='username'></label>"
            "<label>Password <input type='password' name='password' autocomplete='current-password'></label>"
            "<button type='submit'>Authorize</button></form>"
        )


class BearerTokenVerifier:
    """Async MCP SDK bridge for the synchronous, bounded token verifier."""

    def __init__(self, service: AuthService) -> None:
        self.service = service

    async def verify_token(self, token: str) -> AccessToken | None:
        access = self.service.verify_token(token)
        if access is None:
            emit(
                self.service.settings,
                "mcp.bearer",
                token_fp=fingerprint(token),
                outcome="rejected",
            )
        else:
            emit(
                self.service.settings,
                "mcp.bearer",
                client_fp=fingerprint(access.client_id),
                token_fp=fingerprint(token),
                effective_scopes=scope_summary(" ".join(access.scopes), self.service.supported_scopes),
                outcome="accepted",
            )
        return access
