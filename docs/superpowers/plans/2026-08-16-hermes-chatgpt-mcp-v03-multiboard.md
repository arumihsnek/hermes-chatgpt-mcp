# Hermes ChatGPT MCP v0.3 Multi-Board Implementation Plan

> For agentic workers: use the subagent-driven-development or executing-plans workflow to execute this plan task by task. Steps use checkbox syntax for tracking.

**Goal:** Add canonical Hermes board discovery and real board-bound MCP routing while keeping service-level authorization and the Query/Command separation explicit.

**Architecture:** A HermesBoardResolver will call Hermes canonical board APIs, filter the result through explicit read/create service allowlists, and return immutable board handles. Each request will build a query adapter over a mode=ro/query_only store or a separate command adapter over Hermes kanban_db.create_task; no MCP SQL writes or controller reimplementation will be added.

**Tech Stack:** Python 3.12, FastMCP 1.28.1, Pydantic strict models, hermes_cli.kanban_db, SQLite read-only URI, pytest/httpx, systemd, OpenResty.

**Spec:** docs/superpowers/specs/2026-08-16-hermes-chatgpt-mcp-v03-multiboard-design.md

## Global Constraints

- list_boards must use Hermes list_boards(include_archived=False) and never scan an arbitrary filesystem path itself.
- Explicit board selection must resolve exactly; failure must never fall back to the configured default.
- Omitted board uses the configured default, otherwise Hermes get_current_board().
- Query connections remain SQLite mode=ro with immediate PRAGMA query_only=ON.
- All writes continue through Hermes kanban_db.create_task; no MCP INSERT, UPDATE, or DELETE is permitted.
- MCP_KANBAN_CREATE_BOARDS must be a subset of MCP_KANBAN_READ_BOARDS after resolution.
- The public v0.3 board policy is service-level, not per-principal ACL; documentation must say per-user board ACL is unavailable.
- The public surface adds only list_boards; no comments, attachments, metadata updates, lifecycle, or board administration tools are exposed.
- create_task.idempotency_key is required in v0.3 and creation is serialized per board within the single service process.
- Existing v0.2 tests and read-only guarantees must remain green.

---

### Task 1: Commit the reconnaissance design

**Files:**
- Create: docs/superpowers/specs/2026-08-16-hermes-chatgpt-mcp-v03-multiboard-design.md
- Create: docs/superpowers/plans/2026-08-16-hermes-chatgpt-mcp-v03-multiboard.md

**Interfaces:**
- Consumes: verified Hermes list_boards, read_board_metadata, board_exists, kanban_db_path, get_current_board, and management signatures.
- Produces: the reviewed design and this executable plan.

- [x] Record the v0.2 repository/deployment identity: master HEAD bbdd93c, deployed runtime commit 700ba8a, clean integration worktree, pre-existing dirty Hermes checkout, absent git remote/PR, and 36-test baseline.
- [x] Record the canonical Hermes board and management findings: independent board DB/metadata model, service-level allowlist limitation, tenant/session semantics, canonical management matrix, and deliberate non-exposure decisions.
- [x] Self-review the design and plan:

~~~text
rg -n 'TBD|TODO|FIXME' docs/superpowers/{specs,plans}/2026-08-16-hermes-chatgpt-mcp-v03-*.md
git diff --check
~~~

Expected: no placeholder matches and no whitespace errors. Commit:

~~~text
git add docs/superpowers/specs/2026-08-16-hermes-chatgpt-mcp-v03-multiboard-design.md \
  docs/superpowers/plans/2026-08-16-hermes-chatgpt-mcp-v03-multiboard.md
git commit -m "docs: design Hermes multi-board MCP surface"
~~~

---

### Task 2: Add strict board policy configuration and canonical resolver tests

**Files:**
- Create: hermes_chatgpt_mcp/boards.py
- Modify: hermes_chatgpt_mcp/config.py
- Test: tests/test_boards.py
- Test: tests/test_config.py

**Interfaces:**
- Consumes: Settings, load_kanban_module, ReadOnlyHermesStore, and the canonical Hermes module.
- Produces: BoardHandle, BoardResolutionError, HermesBoardResolver.resolve(), and HermesBoardResolver.list_handles().

- [ ] Write failing tests named test_explicit_board_resolves_exactly_without_default_fallback, test_unknown_board_is_not_replaced_by_default, test_default_board_uses_configured_board, test_create_allowlist_must_be_readable, test_unreadable_board_is_omitted_from_discovery, test_board_path_uses_canonical_hermes_resolution, and test_ambient_hermes_kanban_db_override_fails_closed.

Use two fixture board directories with independent board.json and kanban.db files. Assert that A and B produce distinct paths and an unknown slug raises BOARD_NOT_FOUND instead of returning the configured default.

- [ ] Run the focused tests and verify the expected RED failures:

~~~text
pytest tests/test_boards.py tests/test_config.py -q
~~~

Expected: new resolver tests fail because the resolver and settings fields do not exist; existing configuration tests must continue to run.

- [ ] Implement strict Settings fields:

~~~python
kanban_read_boards: tuple[str, ...] | None = None
kanban_create_boards: tuple[str, ...] | None = None
max_board_count: int = 50
~~~

Parse MCP_KANBAN_READ_BOARDS and MCP_KANBAN_CREATE_BOARDS as comma-separated canonical slugs, reject malformed or empty entries, and bound MCP_MAX_BOARD_COUNT. Keep v0.2 behavior when the variables are absent.

- [ ] Implement the canonical resolver:

~~~python
@dataclass(frozen=True)
class BoardHandle:
    slug: str
    name: str
    description: str
    project_id: str | None
    created_at: int | None
    is_default: bool
    db_path: Path

class HermesBoardResolver:
    def resolve(self, requested: str | None, *, operation: Literal["read", "create"]) -> BoardHandle: ...
    def list_handles(self) -> list[BoardHandle]: ...
~~~

Call Hermes list_boards(include_archived=False) and kanban_db_path(board=slug). Filter only after canonical discovery. Reject an ambient HERMES_KANBAN_DB, enforce that the canonical path is inside the configured Hermes home, and require every configured default/create board to have a real canonical entry and DB file. Never construct a fallback handle for an explicit request.

- [ ] Run focused and full tests:

~~~text
pytest tests/test_boards.py tests/test_config.py -q
pytest -q
~~~

Expected: all tests pass.

- [ ] Commit:

~~~text
git add hermes_chatgpt_mcp/boards.py hermes_chatgpt_mcp/config.py \
  tests/test_boards.py tests/test_config.py
git commit -m "feat: add canonical Hermes board resolver"
~~~

---

### Task 3: Add the strict list_boards schema and board-bound adapter factory

**Files:**
- Modify: hermes_chatgpt_mcp/schemas.py
- Modify: hermes_chatgpt_mcp/adapter.py
- Modify: hermes_chatgpt_mcp/hermes.py
- Test: tests/test_boards.py
- Test: tests/test_adapter.py

**Interfaces:**
- Consumes: BoardHandle, HermesBoardResolver, and existing adapter bounds.
- Produces: BoardCapabilities, BoardSummary, HermesBoardResolver.query_adapter(), and a board-safe metadata projection.

- [ ] Write failing tests asserting BoardSummary rejects unknown fields, omits physical paths, bounds descriptions, preserves project_id, reports is_default, and maps canonical board_stats by_status for both fixture boards.
- [ ] Run pytest tests/test_boards.py tests/test_adapter.py -q and confirm the expected RED failures.
- [ ] Add BoardCapabilities(read, create) and BoardSummary with bounded slug/name/description, optional project_id/created_at, is_default, task_counts, and capabilities. Omit db_path, default_workdir, and arbitrary metadata.
- [ ] Allow HermesReadOnlyAdapter to receive the resolver's canonical metadata projection. Use Hermes read_board_metadata in production resolution; preserve the direct-store fixture fallback only for tests that construct a store directly.
- [ ] Add bounded board stats projection by calling canonical board_stats through the existing read-only store. Stop at Settings.max_board_count and never follow paths supplied in metadata.
- [ ] Run focused/full tests and commit:

~~~text
pytest tests/test_boards.py tests/test_adapter.py -q
pytest -q
git add hermes_chatgpt_mcp/schemas.py hermes_chatgpt_mcp/adapter.py \
  hermes_chatgpt_mcp/hermes.py tests/test_boards.py tests/test_adapter.py
git commit -m "feat: project canonical multi-board summaries"
~~~

---

### Task 4: Expose list_boards and route all existing tools by board

**Files:**
- Modify: hermes_chatgpt_mcp/server.py
- Modify: hermes_chatgpt_mcp/command.py
- Modify: hermes_chatgpt_mcp/schemas.py
- Test: tests/test_mcp_contract.py
- Test: tests/test_mcp_readonly.py
- Test: tests/test_mcp_create.py
- Create: tests/test_mcp_multiboard.py

**Interfaces:**
- Consumes: resolver and adapter factory from Tasks 2-3.
- Produces: eight MCP tools, with list_boards read-only and all existing tools selecting an explicit/default board handle.

- [ ] Write failing contract tests asserting tools/list returns the seven existing tools plus list_boards, all input schemas are strict, and list_boards has readOnlyHint=true, destructiveHint=false, and no request parameters.
- [ ] Add failing board tests named test_list_boards_returns_only_authorized_canonical_boards, test_read_tools_route_to_explicit_board_a_and_b, test_unknown_board_does_not_fallback_to_default, and test_task_id_from_board_b_is_not_found_on_board_a.
- [ ] Run pytest tests/test_mcp_contract.py tests/test_mcp_multiboard.py -q and confirm failures for the missing tool and routing.
- [ ] Replace ensure_board() equality checking with helpers that resolve a read or create BoardHandle and construct the matching adapter. Preserve injection compatibility by treating an explicitly injected adapter as a one-board resolver unless a resolver is supplied.
- [ ] Run require_scope(hermes:create) before resolving a create request so a read-only token receives only SCOPE_REQUIRED and cannot probe board policy.
- [ ] Register list_boards with read-only annotations, canonical discovery, bounded stats, and safe metadata. Do not expose archived boards, db_path, default workdirs, or environment values.
- [ ] Route get_board, list_tasks, get_task, get_task_graph, get_dispatch, and get_activity through the selected board adapter. Route create_task through the selected board command adapter.
- [ ] Run focused/full tests and commit:

~~~text
pytest tests/test_mcp_contract.py tests/test_mcp_readonly.py \
  tests/test_mcp_create.py tests/test_mcp_multiboard.py -q
pytest -q
git add hermes_chatgpt_mcp/server.py hermes_chatgpt_mcp/command.py \
  hermes_chatgpt_mcp/schemas.py tests/test_mcp_contract.py \
  tests/test_mcp_readonly.py tests/test_mcp_create.py tests/test_mcp_multiboard.py
git commit -m "feat: expose canonical multi-board MCP routing"
~~~

---

### Task 5: Make creation retry-safe and errors structured

**Files:**
- Modify: hermes_chatgpt_mcp/command.py
- Modify: hermes_chatgpt_mcp/server.py
- Modify: hermes_chatgpt_mcp/schemas.py
- Test: tests/test_command_adapter.py
- Test: tests/test_mcp_create.py
- Test: tests/test_mcp_multiboard.py

**Interfaces:**
- Consumes: canonical create_task and board-bound command adapter.
- Produces: mandatory idempotency key, per-board creation lock, stable JSON error codes, and no new mutation route.

- [ ] Write failing tests named test_create_requires_idempotency_key_without_writing, test_same_key_retries_do_not_create_a_second_task, test_cross_board_parent_is_rejected_without_writing, test_board_errors_return_stable_codes_without_paths, and test_read_scope_cannot_probe_create_board_policy.
- [ ] Run pytest tests/test_command_adapter.py tests/test_mcp_create.py tests/test_mcp_multiboard.py -q and confirm the expected RED failures.
- [ ] Make CreateTaskInput.idempotency_key required. Store one threading.Lock per board in the resolver/factory and hold it only around canonical connect_closing plus create_task. Keep Hermes idempotency semantics authoritative and add no SQL preflight.
- [ ] Raise ToolError with a compact JSON object containing only code and message. Map unknown/unreadable boards to BOARD_NOT_FOUND, visible non-creatable boards to BOARD_NOT_ALLOWED, missing write scope to SCOPE_REQUIRED, task absence to TASK_NOT_FOUND, and unexpected failures to BACKEND_ERROR.
- [ ] Run all tests and commit:

~~~text
pytest -q
git add hermes_chatgpt_mcp/command.py hermes_chatgpt_mcp/server.py \
  hermes_chatgpt_mcp/schemas.py tests/test_command_adapter.py \
  tests/test_mcp_create.py tests/test_mcp_multiboard.py
git commit -m "fix: make multi-board creation retry-safe"
~~~

---

### Task 6: Add real two-board integration and isolation evidence

**Files:**
- Modify: tests/fixtures.py
- Create: tests/test_multiboard_integration.py
- Modify: scripts/live_smoke.py
- Modify: Makefile

**Interfaces:**
- Consumes: production resolver, eight MCP tools, and real Hermes fixtures.
- Produces: reproducible A/B read/write proof and safe live smoke tooling.

- [ ] Write a failing HTTP integration test with two independent fixture boards and unique seed tasks:

~~~python
list_boards()
get_board(board=A)
get_board(board=B)
list_tasks(board=A)
list_tasks(board=B)
create_task(board=A, idempotency_key=A)
create_task(board=B, idempotency_key=B)
~~~

Verify each created task with get_task, get_activity, and get_dispatch; repeat each create request; compare per-board fingerprints before/after reads; and assert no task/link/event appears in the other database.
- [ ] Run pytest tests/test_multiboard_integration.py -q and confirm RED before implementing the test support.
- [ ] Use real Hermes SCHEMA_SQL and kanban_db functions. Clean only tmp_path fixtures; live smoke cleanup may use canonical archive_task/delete_archived_task and never a public delete tool.
- [ ] Update live_smoke.py with explicit HERMES_MCP_TEST_BOARD_A and HERMES_MCP_TEST_BOARD_B variables, refuse missing/identical slugs, use identifiable keys, fingerprint both board DB/WAL/metadata sets, and print only safe summaries. Refuse real mutations unless both variables are set.
- [ ] Run and commit:

~~~text
pytest -q
python3 -m compileall -q hermes_chatgpt_mcp tests
git diff --check
git add tests/fixtures.py tests/test_multiboard_integration.py \
  scripts/live_smoke.py Makefile
git commit -m "test: prove Hermes multi-board isolation end to end"
~~~

---

### Task 7: Update OCI policy and documentation

**Files:**
- Modify: .env.example
- Modify: deploy/systemd/hermes-chatgpt-mcp.service
- Modify: scripts/install_oci.sh
- Modify: docs/architecture/HERMES-INTEGRATION.md
- Modify: docs/DEPLOYMENT.md
- Modify: docs/SECURITY.md
- Modify: README.md
- Modify: docs/REVIEW.md
- Test: tests/test_deployment.py

**Interfaces:**
- Consumes: final resolver config and public tool contract.
- Produces: reproducible service-level A/B policy, sandbox write paths, and complete v0.3 documentation.

- [ ] Write failing deployment assertions for read/create board configuration, both explicit board write paths, the unchanged OAuth state path, and all v0.2 hardening flags. Assert docs distinguish READ, CREATE, service-level board policy, tenant/session metadata, and omitted management/lifecycle operations.
- [ ] Run pytest tests/test_deployment.py -q and confirm the expected RED failures.
- [ ] Set OCI defaults:

~~~text
MCP_KANBAN_READ_BOARDS=codex_app_server,dashboard
MCP_KANBAN_CREATE_BOARDS=codex_app_server,dashboard
~~~

Add both named board directories to ReadWritePaths; retain the OAuth state directory and all v0.2 systemd protections. Preserve installer secrets and mode 0600 without printing values.
- [ ] Update architecture, security, deployment, README, and review with canonical discovery, exact resolution/no fallback, list output, allowlist semantics, error codes, idempotency, tenant/session/project semantics, management matrix, eight tools, ChatGPT reauthorization/tool refresh, and the absence of per-principal ACL.
- [ ] Run and commit:

~~~text
pytest -q
git diff --check
git add .env.example deploy/systemd/hermes-chatgpt-mcp.service \
  scripts/install_oci.sh docs/architecture/HERMES-INTEGRATION.md \
  docs/DEPLOYMENT.md docs/SECURITY.md README.md docs/REVIEW.md \
  tests/test_deployment.py
git commit -m "ops: deploy explicit Hermes multi-board policy"
~~~

---

### Task 8: Merge, deploy, and perform independent final review

**Files:**
- Modify only files already listed above.

**Interfaces:**
- Consumes: all committed v0.3 slices and the clean isolated branch.
- Produces: deployed primary master, public MCP proof, final review, and a precise handoff.

- [ ] Run the complete local gate:

~~~text
pytest -q
python3 -m compileall -q hermes_chatgpt_mcp tests
git diff --check
git status --short --branch
~~~

Expected: all tests pass and the worktree is clean.
- [ ] Verify git -C /home/ubuntu/hermes-agent status --short --branch matches the pre-existing reconnaissance snapshot and no Hermes file was changed.
- [ ] From /home/ubuntu/code/hermes-chatgpt-mcp, verify clean status and fast-forward:

~~~text
git merge --ff-only v0.3-multi-board
~~~

Keep each v0.3 slice commit separate and record the final SHA.
- [ ] Deploy and verify:

~~~text
./scripts/install_oci.sh
sudo systemd-analyze verify /etc/systemd/system/hermes-chatgpt-mcp.service
systemctl is-enabled hermes-chatgpt-mcp.service
systemctl is-active hermes-chatgpt-mcp.service
~~~

Validate health, TLS, OAuth discovery/DCR/PKCE, eight tools and annotations, read-only scope denial, create scope success, explicit A/B reads, one create in A, one create in B, idempotency, activity, dispatch, and post-restart DCR/refresh persistence. Clean only the two identifiable test cards through canonical Hermes APIs and verify both boards return to their pre-test fingerprints.
- [ ] Review the final diff for SQL writes, implicit fallback, path leakage, missing scope checks, cross-board adapter reuse, unbounded output, hidden management tools, and systemd write expansion. Re-run pytest -q after any correction and commit review corrections separately.

