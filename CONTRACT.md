# MCP-UI Write Security Contract (Frozen D1R)

**Status:** Frozen. This contract is the authoritative reference for the D1R security boundary. Any implementation must satisfy all clauses below to pass D1 independent review.

**Candidate SHA (reviewed):** 2127a29015fc5aaea8ff9e4fdf3fe1f130923833 (not published; superseded by this durable fix on fc00135c5a094d03f2dc9cb8a1126533304f786f)

**Durable base SHA:** fc00135c5a094d03f2dc9cb8a1126533304f786f (C2 E2E-tested read-only Alpha)

---

## §1 Capability Token Schema

### 1.1 UiCapability
A capability token issued by `UiCapabilityIssuer.issue()` for UI-origin write operations.

```json
{
  "capability_id": "string (opaque stable id)",
  "subject": "string (authenticated session/user subject)",
  "surface": "stable",
  "resource_uri": "ui://hermes/kanban/v2",
  "board": "string (normalized canonical board slug)",
  "tenant": "string (explicitly bound tenant)",
  "operations": ["create_task"],
  "scope": "hermes:read hermes:create",
  "issued_at": "ISO 8601 timestamp",
  "expires_at": "ISO 8601 timestamp"
}
```

### 1.2 Required `scope` claim
**MANDATORY.** The issued token MUST include the exact space-delimited scope claim:
```
scope: "hermes:read hermes:create"
```
No additional scopes. No `manage`, `admin`, `board:create`. Omission or deviation returns `UI_ORIGIN_UNVERIFIED` and no write is performed.

### 1.3 Fail-closed validation
`UiCapabilityIssuer.validate()` MUST reject any token that:
- Lacks the exact `scope` claim above
- Has mismatched `resource_uri` (must be `ui://hermes/kanban/v2`)
- Has expired `expires_at`
- Has mismatched `board`, `tenant`, `subject`, or `capability_id`
- Has operations other than exactly `["create_task"]`

---

## §2 Payload Sanitization

### 2.1 `sanitize_ui_payload(payload: dict) -> dict`
All payloads crossing the UI boundary (outbound responses, inbound request echoes, event telemetry) MUST pass through this function.

### 2.2 Redaction rules (applied to STRING VALUES under ANY key)
For every string value in the payload (recursively through nested dicts/lists):
1. **Bearer tokens**: Replace `Bearer <token>` or `bearer <token>` with `Bearer [REDACTED]`
2. **Authorization headers**: Replace the full `Authorization` header value with the stable redaction marker.
3. **API keys / secrets**: Replace patterns matching `(?i)(api[_-]?key|secret|token|password|passwd)[:=\s]+[^\s]{8,}` with `[REDACTED]`
4. **Internal absolute paths**: Replace `/home/`, `/root/`, `/opt/`, `/var/`, `/etc/`, `/private/`, `/tmp/`, `/workspace/` prefixes with `[INTERNAL_PATH]/`
5. **Connection strings / DSNs**: Replace `postgres://`, `mysql://`, `mongodb://`, `redis://`, `sqlite://` schemes with `[REDACTED]://`

### 2.3 Non-destructive for ordinary text
Ordinary card text (titles, bodies, comments) containing words like "secret", "token", "internal" as natural language MUST NOT be over-redacted. Redaction applies only to structural patterns above, not substring matches.

### 2.4 Key-name filtering (supplementary)
Keys matching `(?i)(authorization|password|secret|token|api[_-]?key|private[_-]?key|bearer)` are fully redacted regardless of value. This is a defense-in-depth layer; the primary guarantee is value-level redaction above.

---

## §3 UI Write Policy Boundary

### 3.1 Allowlist
Exactly one operation from verified UI origin: `create_task` via canonical Hermes command path.

### 3.2 Forbidden from UI origin (server-enforced)
- Human Gate operations: `request_review`, `request_changes`, `reopen_review`, `force`
- All mutations beyond creation: `add_comment`, `assign_task`, `reassign_tasks`, `set_model`, `edit_task`, `link_tasks`, `unlink_tasks`, `complete_tasks`, `promote_tasks`, `block_tasks`, `unblock_tasks`, `schedule_tasks`, `reclaim_task`, `claim`, `dispatch`
- Board/infrastructure: `create_board`, `archive_tasks`, `boards-*`, `init`, `repair`, `gc`, `decompose`, `swarm`, `attach`, `attach-rm`, `heartbeat`, `specify`, `daemon`, `notify-subscribe`, `notify-unsubscribe`

### 3.3 Field restrictions
UI `create_task` payload accepts ONLY: `title`, optional `body`, optional `parent_ids`, `expected_board_revision`, `idempotency_key`.
Fields `board`, `tenant`, `assignee`, `priority`, `session_id`, `triage`, `created_by`, `origin` are `UI_FIELD_FORBIDDEN` if present.

---

## §4 Revision and Idempotency

### 4.1 Board revision CAS
Monotonic per-board `board_revision` incremented atomically with every canonical mutation. UI write carries `expected_board_revision`; CAS mismatch returns `STALE_VIEW`.

### 4.2 Idempotency receipt
Durable per-board receipt: `UNIQUE(scope_key, operation, idempotency_key)`.
- Replay with same fingerprint → `idempotent_replay`
- Same key, different fingerprint → `IDEMPOTENCY_CONFLICT`
- Stale rejection does not consume key

---

## §5 Provenance and Audit

### 5.1 Server-derived provenance
UI-created tasks: `created_by = "mcp_ui"`, event payload includes `origin: "ui"`, `capability_id`, `request_fingerprint`, `board_revision_after`.

### 5.2 No secrets in audit
Bearer tokens, raw secrets, internal paths MUST NOT appear in task events or receipts. Sanitization §2 applies before persistence.

---

## §6 Versioning and Enablement

### 6.1 Resource URI
Read-only v1: `ui://hermes/kanban/v1`
Write-enabled v2: `ui://hermes/kanban/v2` (atomically with behavior change)

### 6.2 Default state
**v2 disabled by default.** Feature flag `UI_WRITE_ENABLED=false` in production. v1 remains fully available.

### 6.3 Rollback
Disabling v2 restores v1 read-only behavior. Created tasks remain canonical; no history rewrite.

---

## §7 Test Contract (Fail-Closed)

### 7.1 Scope claim tests
- Issued token contains exact `scope: "hermes:read hermes:create"`
- Missing scope → reject
- Extra scope (`manage`, `admin`, `board:create`) → reject
- Wrong scope (`hermes:read` only) → reject

### 7.2 Sanitization tests (value-level, adversarial)
- `note: "Authorization: Bearer abc123"` → `note: "Authorization: Bearer [REDACTED]"`
- `description: "The path is /home/user/secret.txt"` → `description: "The path is [INTERNAL_PATH]/user/secret.txt"`
- `config: "postgres://user:pass@host/db"` → `config: "[REDACTED]://user:pass@host/db"`
- `title: "Token secret internal"` → unchanged (ordinary text)
- Key `password: "value"` → fully redacted (key-name layer)

### 7.3 Forbidden operation tests
Every operation in §3.2 returns `GATE_FORBIDDEN_FROM_UI` or `UI_OPERATION_FORBIDDEN` with valid manage/admin credentials; zero task/event/revision mutation.

### 7.4 Replay and stale tests
- Stale revision → `STALE_VIEW`, zero mutation
- Same key, same fingerprint → `idempotent_replay`
- Same key, different fingerprint → `IDEMPOTENCY_CONFLICT`