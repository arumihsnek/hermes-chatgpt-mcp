"""Fail-closed v2 MCP Apps UI mutation boundary.

The boundary is deliberately separate from the broad stable create command: UI
callers can only create an unassigned task using a verified capability context.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from dataclasses import dataclass
from typing import Any, Iterable

from .hermes import ReadOnlyHermesStore
from .ui_write_contract import (
    UI_ALLOWED_CREATE_FIELDS,
    UI_ORIGIN_VALUE,
    UI_PROVENANCE_ACTOR,
    UiCapability,
    UiCapabilityIssuer,
    sanitize_ui_payload,
)


class UiMutationError(ValueError):
    def __init__(self, code: str, message: str = "UI mutation rejected") -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class UiCreateResult:
    mutation_status: str
    canonical_task_id: str
    board: str
    tenant: str
    board_revision_after: int
    readback_status: str = "complete"

    def to_dict(self) -> dict[str, Any]:
        return {"mutation_status": self.mutation_status, "canonical_task_id": self.canonical_task_id,
                "board": self.board, "tenant": self.tenant,
                "board_revision_after": self.board_revision_after,
                "readback_status": self.readback_status}


_SCHEMA = """
CREATE TABLE IF NOT EXISTS board_revision (
 board TEXT PRIMARY KEY, revision INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS ui_mutation_receipt (
 operation TEXT NOT NULL, scope_key TEXT NOT NULL, idempotency_key TEXT NOT NULL,
 request_fingerprint TEXT NOT NULL, canonical_task_id TEXT NOT NULL,
 outcome TEXT NOT NULL, origin TEXT NOT NULL, board_revision_after INTEGER NOT NULL,
 created_at INTEGER NOT NULL,
 PRIMARY KEY (scope_key, operation, idempotency_key)
);
"""


def _fingerprint(board: str, tenant: str, capability_id: str, title: str,
                body: str | None, parents: tuple[str, ...]) -> str:
    value = {"board": board, "tenant": tenant, "capability_id": capability_id,
             "title": title, "body": body, "parent_ids": list(parents)}
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


class UiMutationAdapter:
    """Policy and receipt boundary over Hermes' canonical create command."""
    def __init__(self, store: ReadOnlyHermesStore, capability: UiCapability,
                 issuer: UiCapabilityIssuer | None = None) -> None:
        self.store = store
        self.capability = capability
        self.issuer = issuer or UiCapabilityIssuer()

    def _validate(self, fields: dict[str, Any], operation: str) -> tuple[str, str | None, tuple[str, ...]]:
        valid, reason = self.issuer.validate(self.capability, expected_board=self.store.board,
                                             expected_tenant=self.capability.tenant)
        if not valid:
            raise UiMutationError("UI_ORIGIN_UNVERIFIED" if reason in {"EXPIRED", "MALFORMED_CAPABILITY"} else reason or "UI_ORIGIN_UNVERIFIED")
        if operation != "create_task" or tuple(self.capability.operations) != ("create_task",):
            raise UiMutationError("UI_OPERATION_FORBIDDEN")
        extra = set(fields) - UI_ALLOWED_CREATE_FIELDS
        if extra:
            if "board" in extra and fields.get("board") != self.capability.board:
                raise UiMutationError("BOARD_CONTEXT_MISMATCH")
            if "tenant" in extra and fields.get("tenant") != self.capability.tenant:
                raise UiMutationError("TENANT_CONTEXT_MISMATCH")
            raise UiMutationError("UI_FIELD_FORBIDDEN")
        title = fields.get("title")
        if not isinstance(title, str) or not title.strip():
            raise UiMutationError("INVALID_TITLE")
        body = fields.get("body")
        if body is not None and not isinstance(body, str):
            raise UiMutationError("INVALID_BODY")
        parents = tuple(str(x) for x in fields.get("parent_ids", ()) if str(x))
        return title.strip(), body, parents

    def create_task(self, *, title: str, body: str | None = None,
                    parent_ids: Iterable[str] = (), expected_board_revision: int,
                    idempotency_key: str, **extra: Any) -> UiCreateResult:
        fields = {"title": title, "body": body, "parent_ids": list(parent_ids),
                  "expected_board_revision": expected_board_revision,
                  "idempotency_key": idempotency_key, **extra}
        title, body, parents = self._validate(fields, "create_task")
        if not isinstance(expected_board_revision, int) or expected_board_revision < 0:
            raise UiMutationError("INVALID_REVISION")
        if not isinstance(idempotency_key, str) or not idempotency_key:
            raise UiMutationError("INVALID_IDEMPOTENCY_KEY")
        board = self.capability.board
        tenant = self.capability.tenant
        scope_key = f"{board}|{tenant}|{self.capability.subject}"
        body = sanitize_ui_payload(body) if body else body
        fp = _fingerprint(board, tenant, self.capability.capability_id, title, body, parents)
        hermes = self.store.hermes
        if hermes is None:
            raise UiMutationError("BACKEND_ERROR", "canonical Hermes module unavailable")
        with hermes.connect_closing(db_path=self.store.db_path, board=board) as conn:
            conn.executescript(_SCHEMA)
            row = conn.execute("SELECT revision FROM board_revision WHERE board=?", (board,)).fetchone()
            if row is None:
                conn.execute("INSERT INTO board_revision(board,revision) VALUES(?,0)", (board,))
                revision = 0
            else:
                revision = int(row[0])
            receipt = conn.execute("SELECT * FROM ui_mutation_receipt WHERE scope_key=? AND operation=? AND idempotency_key=?",
                                   (scope_key, "create_task", idempotency_key)).fetchone()
            if receipt:
                if receipt["request_fingerprint"] != fp:
                    raise UiMutationError("IDEMPOTENCY_CONFLICT")
                return UiCreateResult("idempotent_replay", str(receipt["canonical_task_id"]), board, tenant,
                                      int(receipt["board_revision_after"]))
            if revision != expected_board_revision:
                raise UiMutationError("STALE_VIEW")
            # The only task-changing call is Hermes' canonical command function;
            # all UI-only bookkeeping is additive and remains on this connection.
            task_id = hermes.create_task(
                conn, title=title, body=body,
                parents=parents, assignee=None, created_by=UI_PROVENANCE_ACTOR,
                priority=0, tenant=tenant, session_id=None, triage=False,
                idempotency_key=idempotency_key, initial_status="running", board=board,
            )
            after = revision + 1
            conn.execute("UPDATE board_revision SET revision=? WHERE board=? AND revision=?", (after, board, revision))
            conn.execute(
                "INSERT INTO task_events(task_id, run_id, kind, payload, created_at) VALUES(?,?,?,?,?)",
                (task_id, None, "ui_created", json.dumps(sanitize_ui_payload({
                    "origin": UI_ORIGIN_VALUE, "board": board, "tenant": tenant,
                    "capability_id": self.capability.capability_id,
                    "request_fingerprint": fp, "board_revision_after": after,
                }), separators=(",", ":")), int(time.time())),
            )
            conn.execute("INSERT INTO ui_mutation_receipt VALUES (?,?,?,?,?,?,?,?,?)",
                         ("create_task", scope_key, idempotency_key, fp, task_id, "created",
                          UI_ORIGIN_VALUE, after, int(time.time())))
            conn.commit()
            return UiCreateResult("created", str(task_id), board, tenant, after)
