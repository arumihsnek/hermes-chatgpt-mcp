from __future__ import annotations

import os
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from .config import ConfigurationError, Settings
from .hermes import ReadOnlyHermesStore, load_kanban_module


class BoardResolutionError(LookupError):
    """A safe, stable error raised while resolving an MCP board request."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class BoardHandle:
    """Safe metadata and canonical DB path for one authorized board."""

    slug: str
    name: str
    description: str
    project_id: str | None
    created_at: int | None
    is_default: bool
    db_path: Path


class HermesBoardResolver:
    """Resolve MCP boards through Hermes' canonical board APIs.

    The resolver is deliberately service-scoped: Hermes does not expose
    per-principal board ACLs, so the read/create allowlists are deployment
    policy, not claims about individual OAuth users.
    """

    def __init__(self, settings: Settings, *, hermes_module: Any | None = None) -> None:
        if os.environ.get("HERMES_KANBAN_DB", "").strip():
            raise ConfigurationError(
                "HERMES_KANBAN_DB is incompatible with explicit multi-board routing"
            )
        self.settings = settings
        self.hermes = hermes_module or load_kanban_module(settings.hermes_agent_root)
        configured_home = settings.hermes_kanban_home
        canonical_home = Path(self.hermes.kanban_home()).expanduser().resolve()
        self.home = (configured_home or canonical_home).expanduser().resolve()
        if canonical_home != self.home:
            raise ConfigurationError(
                "HERMES_KANBAN_HOME does not match Hermes canonical board home"
            )
        self.max_board_count = settings.max_board_count
        self.default_slug = self._configured_default()
        # Fail closed when the deployment omitted a board allowlist. The
        # default board remains usable for local compatibility, but the
        # resolver must never enumerate every Hermes board by accident.
        self.read_policy = (
            set(settings.kanban_read_boards)
            if settings.kanban_read_boards is not None
            else {self.default_slug}
        )
        self.create_policy = (
            set(settings.kanban_create_boards)
            if settings.kanban_create_boards is not None
            else {self.default_slug}
        )
        if not self.create_policy.issubset(self.read_policy):
            raise ConfigurationError(
                "MCP_KANBAN_CREATE_BOARDS must be a subset of MCP_KANBAN_READ_BOARDS"
            )
        if self.default_slug not in self.read_policy:
            raise ConfigurationError("configured default board must be readable")
        self._creation_locks: dict[str, threading.Lock] = {}
        self._lock = threading.Lock()
        self._validate_configured_boards()

    def _configured_default(self) -> str:
        candidate = self.settings.default_board
        if candidate is None:
            candidate = self.hermes.get_current_board()
        try:
            return ReadOnlyHermesStore.validate_board_slug(str(candidate))
        except (TypeError, ValueError) as exc:
            raise ConfigurationError("configured Hermes default board is invalid") from exc

    def _canonical_entries(self) -> list[dict[str, Any]]:
        try:
            entries = self.hermes.list_boards(include_archived=False)
        except Exception as exc:
            raise ConfigurationError("Hermes canonical board discovery is unavailable") from exc
        if not isinstance(entries, list) or len(entries) > self.max_board_count:
            raise ConfigurationError("Hermes board count exceeds the configured MCP bound")
        result: list[dict[str, Any]] = []
        seen: set[str] = set()
        for raw in entries:
            if not isinstance(raw, dict):
                continue
            try:
                slug = ReadOnlyHermesStore.validate_board_slug(str(raw.get("slug") or ""))
            except ValueError:
                continue
            if slug in seen:
                continue
            normalized = dict(raw)
            normalized["slug"] = slug
            result.append(normalized)
            seen.add(slug)
        return result

    def _canonical_entry_map(self) -> dict[str, dict[str, Any]]:
        return {str(entry["slug"]): entry for entry in self._canonical_entries()}

    def _db_path(self, slug: str) -> Path:
        try:
            path = Path(self.hermes.kanban_db_path(board=slug)).expanduser().resolve()
        except Exception as exc:
            raise BoardResolutionError("BOARD_NOT_FOUND", "requested board is unavailable") from exc
        try:
            path.relative_to(self.home)
        except ValueError as exc:
            raise ConfigurationError("Hermes canonical board path escapes configured home") from exc
        if not path.is_file():
            raise BoardResolutionError("BOARD_NOT_FOUND", "requested board is unavailable")
        return path

    def _handle(self, entry: dict[str, Any]) -> BoardHandle:
        slug = str(entry["slug"])
        created_at = entry.get("created_at")
        return BoardHandle(
            slug=slug,
            name=str(entry.get("name") or slug)[:512],
            description=str(entry.get("description") or "")[:2_000],
            project_id=(str(entry["project_id"])[:128] if entry.get("project_id") else None),
            created_at=(int(created_at) if isinstance(created_at, int) else None),
            # MCP's default is the board used when the request omits ``board``;
            # it may be a named Hermes board rather than Hermes' legacy
            # ``default`` database.
            is_default=slug == self.default_slug,
            db_path=self._db_path(slug),
        )

    def _validate_configured_boards(self) -> None:
        entries = self._canonical_entry_map()
        required = {self.default_slug} | self.create_policy
        for slug in required:
            if slug not in entries:
                raise ConfigurationError("configured board is not a canonical Hermes board")
            try:
                self._handle(entries[slug])
            except BoardResolutionError as exc:
                raise ConfigurationError("configured board database is unavailable") from exc

    def list_handles(self) -> list[BoardHandle]:
        entries = self._canonical_entry_map()
        handles: list[BoardHandle] = []
        for slug, entry in entries.items():
            if slug not in self.read_policy:
                continue
            try:
                handles.append(self._handle(entry))
            except BoardResolutionError:
                if slug in self.read_policy:
                    raise ConfigurationError("authorized board database is unavailable")
        return handles[: self.max_board_count]

    def resolve(
        self,
        requested: str | None,
        *,
        operation: Literal["read", "create"],
    ) -> BoardHandle:
        slug = self.default_slug if requested is None else requested
        try:
            slug = ReadOnlyHermesStore.validate_board_slug(str(slug))
        except (TypeError, ValueError) as exc:
            raise BoardResolutionError("BOARD_NOT_FOUND", "requested board is unavailable") from exc
        entries = self._canonical_entry_map()
        if slug not in entries or slug not in self.read_policy:
            raise BoardResolutionError("BOARD_NOT_FOUND", "requested board is unavailable")
        if operation == "create" and slug not in self.create_policy:
            raise BoardResolutionError("BOARD_NOT_ALLOWED", "creation is not allowed on this board")
        return self._handle(entries[slug])

    def store(self, handle: BoardHandle) -> ReadOnlyHermesStore:
        return ReadOnlyHermesStore(
            db_path=handle.db_path,
            board=handle.slug,
            hermes_module=self.hermes,
            hermes_agent_root=self.settings.hermes_agent_root,
        )

    def query_adapter(self, handle: BoardHandle):
        from .adapter import HermesReadOnlyAdapter

        return HermesReadOnlyAdapter(
            self.store(handle),
            max_body_chars=self.settings.max_body_chars,
            max_log_bytes=self.settings.max_log_bytes,
            max_activity_items=self.settings.max_activity_items,
            metadata={
                "slug": handle.slug,
                "name": handle.name,
                "description": handle.description,
                "project_id": handle.project_id,
                "created_at": handle.created_at,
            },
        )

    def command_adapter(self, handle: BoardHandle):
        from .command import HermesCreateAdapter

        return HermesCreateAdapter(self.store(handle))

    def create_allowed(self, slug: str) -> bool:
        return slug in self.create_policy

    def creation_lock(self, slug: str) -> threading.Lock:
        with self._lock:
            return self._creation_locks.setdefault(slug, threading.Lock())


class SingleBoardResolver:
    """Compatibility resolver for callers injecting one adapter."""

    def __init__(self, adapter: Any, command_adapter: Any, settings: Settings) -> None:
        metadata = adapter._metadata()
        self.adapter = adapter
        self._command_adapter = command_adapter
        self.settings = settings
        self.default_slug = adapter.store.board
        self.handle = BoardHandle(
            slug=adapter.store.board,
            name=str(metadata.get("name") or adapter.store.board)[:512],
            description=str(metadata.get("description") or "")[:2_000],
            project_id=(str(metadata["project_id"])[:128] if metadata.get("project_id") else None),
            created_at=(int(metadata["created_at"]) if isinstance(metadata.get("created_at"), int) else None),
            is_default=adapter.store.board == "default",
            db_path=adapter.store.db_path,
        )
        self._creation_lock = threading.Lock()

    def resolve(
        self,
        requested: str | None,
        *,
        operation: Literal["read", "create"],
    ) -> BoardHandle:
        if requested is not None and requested != self.handle.slug:
            raise BoardResolutionError("BOARD_NOT_FOUND", "requested board is unavailable")
        return self.handle

    def list_handles(self) -> list[BoardHandle]:
        return [self.handle]

    def query_adapter(self, handle: BoardHandle):
        return self.adapter

    def command_adapter(self, handle: BoardHandle):
        return self._command_adapter

    def create_allowed(self, slug: str) -> bool:
        return slug == self.handle.slug

    def creation_lock(self, slug: str) -> threading.Lock:
        return self._creation_lock
