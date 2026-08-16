# Hermes ChatGPT MCP Beta Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an independently deployable beta MCP surface with canonical Hermes board creation and narrow card management while preserving the stable read-plus-create service unchanged by default.

**Architecture:** Reuse the existing query adapter and board resolver, inject an explicit stable/beta authorization policy, and add dedicated command adapters for `create_board`, `add_comment`, and `assign_task`. The beta entrypoint and deployment use a separate port, public origin, OAuth state file, signing key, and systemd unit while pointing at Hermes' canonical board home.

**Tech Stack:** Python 3.11+, FastMCP 1.28.1, Pydantic strict models, Starlette, OAuth authorization-code + PKCE, SQLite query-only reads, Hermes `hermes_cli.kanban_db` canonical command functions, pytest, systemd, OpenResty.

**Spec:** `docs/superpowers/specs/2026-08-16-hermes-chatgpt-mcp-beta-design.md`

## Global Constraints

- The stable default remains the seven read tools plus `create_task`, with stable scopes `hermes:read`, `hermes:create`, and `offline_access`.
- The beta is selected explicitly by `MCP_SURFACE=beta` or its dedicated module; the stable default must not register beta tools or beta scopes.
- Query storage remains SQLite URI `mode=ro` with `PRAGMA query_only=ON`.
- All beta writes call Hermes canonical functions; no task or board mutation SQL may be added to this repository.
- A command grant is bound to one selected named board; a request for another board fails with `BOARD_SESSION_MISMATCH`.
- `hermes:board:create` is separate from `hermes:create` and `hermes:manage`; creating a board never changes the Hermes default board.
- No public delete, archive, lifecycle, controller, import, sync, or arbitrary update operation is added.
- Unknown fields, invalid slugs/IDs, oversize strings, and unbounded arrays are rejected before command execution.
- OAuth state, signing keys, passwords, tokens, and private deployment files are never committed.
- `/home/ubuntu/hermes-agent` is read-only for this mission.
- Every production-code change is preceded by a failing test and followed by focused plus full-suite verification.

---

### Task 1: Introduce explicit stable and beta authorization policies

**Files:**
- Modify: `hermes_chatgpt_mcp/auth.py`
- Modify: `hermes_chatgpt_mcp/config.py`
- Modify: `tests/test_auth.py`
- Create: `tests/test_beta_auth.py`
- Modify: `tests/test_config.py`

**Interfaces:**
- Add `AuthPolicy` with fields `read_scope`, `create_scope`, `manage_scope`, `board_create_scope`, `offline_scope`, `supported_scopes`, and `registration_defaults`.
- Add `STABLE_AUTH_POLICY` with exactly the current three supported scopes and `BETA_AUTH_POLICY` with `hermes:read`, `hermes:create`, `hermes:manage`, `hermes:board:create`, and `offline_access`.
- Change `AuthService` construction to `AuthService(settings, policy=STABLE_AUTH_POLICY)` while preserving the existing class-level stable aliases used by current tests and callers.
- Add `Settings.surface: Literal["stable", "beta"]` and `Settings.board_create_enabled: bool` parsed from `MCP_SURFACE` and `MCP_BOARD_CREATE_ENABLED`; defaults are `stable` and `False`.
- Keep `Settings.from_env()` compatible with the current stable environment file.

- [ ] **Step 1: Write failing policy tests.** Add tests showing that stable registration rejects `hermes:manage` and `hermes:board:create`, beta registration accepts them, and beta defaults do not silently grant board administration.
- [ ] **Step 2: Run the focused tests and verify the expected failure.**

Run: `pytest -q tests/test_beta_auth.py tests/test_auth.py::test_unsupported_scope_is_rejected tests/test_config.py`

Expected: the new beta-policy tests fail because policy injection and beta settings do not exist.

- [ ] **Step 3: Implement policy injection minimally.** Keep scope normalization, refresh rotation, persisted grants, and stable aliases intact; route all validation and diagnostic scope summaries through the selected policy.
- [ ] **Step 4: Extend grant validation.** Treat `hermes:create` and `hermes:manage` as command scopes requiring `board_access="write"` and one board; treat `hermes:board:create` as a global administrative scope that does not accept or manufacture a board claim.
- [ ] **Step 5: Run the focused tests and verify green.**

Run: `pytest -q tests/test_beta_auth.py tests/test_auth.py tests/test_config.py`

Expected: all focused auth/config tests pass, including existing stable scope and refresh tests.

- [ ] **Step 6: Commit the authorization boundary.**

```bash
git add hermes_chatgpt_mcp/auth.py hermes_chatgpt_mcp/config.py tests/test_auth.py tests/test_beta_auth.py tests/test_config.py
git commit -m "feat: add explicit beta authorization policy"
```

### Task 2: Add strict beta request and capability schemas

**Files:**
- Modify: `hermes_chatgpt_mcp/schemas.py`
- Modify: `tests/test_command_adapter.py`
- Create: `tests/test_beta_schemas.py`

**Interfaces:**
- Add beta-only `BetaBoardCapabilities` with `read`, `create`, and `manage` so the stable `BoardCapabilities` JSON remains unchanged.
- Add `GlobalCapabilities` with `create_board: bool`.
- Add beta-only `BetaBoardSummary` and `BetaBoardListView` with `global_capabilities`; the stable surface continues returning the existing `BoardListView` without beta fields.
- Add `CreateBoardInput(slug, name=None, description=None, icon=None, color=None)` with strict Hermes slug and bounded metadata fields.
- Add `CreateBoardResult(slug, name, description, icon=None, color=None, created: bool, is_default: bool)` with no filesystem path.
- Add `AddCommentInput(BoardQuery)` with `task_id: TaskId` and `body` bounded to 16,000 characters.
- Add `AddCommentResult(board, task_id, comment_id, author, created_at)`.
- Add `AssignTaskInput(BoardQuery)` with `task_id: TaskId` and non-empty `assignee: AssigneeName`.
- Add `AssignTaskResult(board, task_id, assignee, status)`.

- [ ] **Step 1: Write failing schema tests.** Cover unknown fields, invalid board slugs, invalid task IDs, empty comments, oversize comments, path-like metadata, and valid examples for all three inputs.
- [ ] **Step 2: Run the schema tests and verify they fail for missing models/fields.**

Run: `pytest -q tests/test_beta_schemas.py`

Expected: collection or assertion failures identifying the missing beta models and capability fields.

- [ ] **Step 3: Implement the models using the existing `StrictModel`, `BoardSlug`, `TaskId`, and `AssigneeName` types.** Keep `extra="forbid"` and avoid accepting a generic metadata dictionary.
- [ ] **Step 4: Run the schema tests and existing contract tests.**

Run: `pytest -q tests/test_beta_schemas.py tests/test_mcp_contract.py tests/test_mcp_create.py`

Expected: beta schema tests pass and stable contract tests remain green.

- [ ] **Step 5: Commit the strict public models.**

```bash
git add hermes_chatgpt_mcp/schemas.py tests/test_beta_schemas.py tests/test_command_adapter.py
git commit -m "feat: define beta board and card schemas"
```

### Task 3: Add narrow canonical Hermes command adapters

**Files:**
- Modify: `hermes_chatgpt_mcp/command.py`
- Modify: `hermes_chatgpt_mcp/boards.py`
- Create: `tests/test_beta_command_adapter.py`

**Interfaces:**
- Add `HermesBoardAdminAdapter.create_board(slug, name=None, description=None, icon=None, color=None) -> CreateBoardResult`.
- Add `HermesCardManagementAdapter.add_comment(task_id, body) -> AddCommentResult`.
- Add `HermesCardManagementAdapter.assign_task(task_id, assignee) -> AssignTaskResult`.
- Add resolver factories `board_admin_adapter()` and `management_adapter(handle)`; keep `command_adapter(handle)` returning the existing create-only adapter for stable behavior.

The board adapter calls `self.hermes.create_board(...)` and derives its safe result from the returned canonical metadata. It must not expose `db_path`, `default_workdir`, `project_id`, or arbitrary metadata.

The card adapter opens Hermes with `connect_closing(db_path=handle.db_path, board=handle.slug)`, calls exactly `add_comment` or `assign_task`, reloads the affected task/comment identity through canonical query functions, and closes the connection. The comment author is the fixed provenance `chatgpt_mcp`.

- [ ] **Step 1: Write failing adapter tests against real Hermes fixtures.** Verify board creation creates a canonical board directory/DB and does not change the current board; comments create a `commented` event; assignment creates an `assigned` event; missing task and running-task assignment fail without unrelated writes.
- [ ] **Step 2: Run the focused adapter tests and verify the expected failures.**

Run: `pytest -q tests/test_beta_command_adapter.py`

Expected: failures because the new adapter classes and resolver factories do not exist.

- [ ] **Step 3: Implement the two narrow adapters by calling only canonical Hermes functions.** Do not add SQL literals to `command.py`.
- [ ] **Step 4: Add a source-level guard test.** Assert `command.py` contains no `INSERT`, `UPDATE`, `DELETE`, or `REPLACE` SQL statement and that the new adapter methods reference the expected canonical function names.
- [ ] **Step 5: Run focused adapter and existing command tests.**

Run: `pytest -q tests/test_beta_command_adapter.py tests/test_command_adapter.py`

Expected: all adapter tests pass and the stable create adapter remains unchanged in behavior.

- [ ] **Step 6: Commit the canonical command boundary.**

```bash
git add hermes_chatgpt_mcp/command.py hermes_chatgpt_mcp/boards.py tests/test_beta_command_adapter.py
git commit -m "feat: add canonical beta board and card commands"
```

### Task 4: Wire beta board capabilities and command authorization

**Files:**
- Modify: `hermes_chatgpt_mcp/boards.py`
- Modify: `hermes_chatgpt_mcp/server.py`
- Modify: `hermes_chatgpt_mcp/auth.py`
- Create: `tests/test_mcp_beta.py`

**Interfaces:**
- Add `write_grant_board(required_scope: str | None = None) -> str | None` semantics that accept a signed `board_access="write"` claim only when the token contains the requested command scope.
- Add `has_command_scope(scope: str, board: str | None = None) -> bool` in the app-local authorization helpers.
- Add `board_summary(handle, *, beta: bool)` so stable output remains compatible and beta reports `manage` plus `global_capabilities.create_board`.
- Extend `resolve_board` operation vocabulary to `read`, `create`, and `manage`; `create` and `manage` both require exact grant-board matching, while `create_board` has no selected board.
- Add beta tools to `create_app(..., surface="beta")` only:
  - `create_board(request: CreateBoardInput) -> CreateBoardResult`;
  - `add_comment(request: AddCommentInput) -> AddCommentResult`;
  - `assign_task(request: AssignTaskInput) -> AssignTaskResult`.
- Keep `create_app()` defaulting to `surface="stable"` and registering exactly the existing eight stable tools.

- [ ] **Step 1: Write failing MCP authorization tests.** Exercise beta discovery, tool count, annotations, `hermes:read` denial, `hermes:create` denial of board creation, `hermes:manage` board binding, `hermes:board:create` board creation, and cross-board mismatch.
- [ ] **Step 2: Run the new MCP tests and verify they fail before implementation.**

Run: `pytest -q tests/test_mcp_beta.py`

Expected: failures because beta surface registration and authorization helpers are absent.

- [ ] **Step 3: Implement the beta-only tool registration and capability projection.** Keep read handlers shared and preserve stable annotations, schemas, and errors.
- [ ] **Step 4: Enforce scope and selected-board checks before constructing a command adapter.** `create_board` must also require `Settings.board_create_enabled` and must never accept a board-selection argument.
- [ ] **Step 5: Map Hermes validation errors to structured `CONFLICT`, missing task to `TASK_NOT_FOUND`, scope failures to `SCOPE_REQUIRED`, and never return stack traces or paths.
- [ ] **Step 6: Run focused MCP tests and stable contract/read-only tests.**

Run: `pytest -q tests/test_mcp_beta.py tests/test_mcp_contract.py tests/test_mcp_readonly.py tests/test_mcp_create.py tests/test_mcp_multiboard.py`

Expected: all beta tests pass; the stable surface remains eight tools and all seven reads remain read-only.

- [ ] **Step 7: Commit the beta MCP surface.**

```bash
git add hermes_chatgpt_mcp/auth.py hermes_chatgpt_mcp/boards.py hermes_chatgpt_mcp/server.py tests/test_mcp_beta.py
git commit -m "feat: expose beta board and card management tools"
```

### Task 5: Add the isolated beta entrypoint and OAuth/deployment configuration

**Files:**
- Create: `hermes_chatgpt_mcp/beta_server.py`
- Create: `deploy/systemd/hermes-chatgpt-mcp-beta.service`
- Create: `deploy/openresty/kanban-mcp-beta.conf`
- Create: `scripts/install_oci_beta.sh`
- Modify: `.env.example`
- Modify: `tests/test_deployment.py`
- Create: `tests/test_beta_entrypoint.py`

**Interfaces:**
- `beta_server.py` loads `Settings.from_env()`, asserts `settings.surface == "beta"`, constructs `AuthService(settings, policy=BETA_AUTH_POLICY)`, calls `create_app(settings=settings, surface="beta", auth_service=auth)`, and runs Uvicorn on the configured port.
- The beta unit uses `User=ubuntu`, `WorkingDirectory=/home/ubuntu/code/hermes-chatgpt-mcp/.worktrees/hermes-chatgpt-mcp-beta` for the isolated candidate deployment; `scripts/install_oci_beta.sh` verifies that path is a Git worktree on the requested beta commit before installing the unit.
- Production beta defaults use loopback `127.0.0.1:8791`, `MCP_SURFACE=beta`, `MCP_BOARD_CREATE_ENABLED=1`, `/var/lib/hermes-chatgpt-mcp-beta/oauth-state.json`, and a distinct `MCP_OAUTH_SIGNING_KEY` supplied only through a private environment file.
- The beta systemd sandbox allows only the named-board Hermes storage and its own state directory. It does not add access to the legacy root `default` database or unrelated Hermes services.
- OpenResty proxies `/mcp`, OAuth discovery, OAuth endpoints, and `/healthz` for the beta hostname to `127.0.0.1:8791`; no stable-host location is modified by this task.

- [ ] **Step 1: Write failing deployment tests.** Assert the beta unit has a distinct service name, port, state file, surface, restart policy, write paths, and no stable-state reuse; assert the beta entrypoint selects the beta policy.
- [ ] **Step 2: Run the deployment tests and verify expected failures.**

Run: `pytest -q tests/test_beta_entrypoint.py tests/test_deployment.py`

Expected: failures because the beta entrypoint/unit/config files do not exist.

- [ ] **Step 3: Implement the beta entrypoint and unit with the stable sandbox protections retained.** Do not copy secrets into tracked files.
- [ ] **Step 4: Add OpenResty configuration for the separate beta hostname and validate its syntax using the existing deployment test convention.**
- [ ] **Step 5: Add `scripts/install_oci_beta.sh` to install only the beta unit/include, create the beta state directory, preserve private credentials, validate OpenResty before reload, and never restart the stable unit.**
- [ ] **Step 6: Run focused deployment tests and compile checks.**

Run: `/home/ubuntu/hermes-agent/venv/bin/python -m pytest -q tests/test_beta_entrypoint.py tests/test_deployment.py && /home/ubuntu/hermes-agent/venv/bin/python -m compileall -q hermes_chatgpt_mcp tests`

Expected: all focused deployment tests pass and compilation exits zero.

- [ ] **Step 7: Commit the isolated beta runtime.**

```bash
git add hermes_chatgpt_mcp/beta_server.py deploy/systemd/hermes-chatgpt-mcp-beta.service deploy/openresty/kanban-mcp-beta.conf scripts/install_oci_beta.sh .env.example tests/test_beta_entrypoint.py tests/test_deployment.py
git commit -m "ops: add isolated beta MCP runtime"
```

### Task 6: Add end-to-end fixture, persistence, and isolation coverage

**Files:**
- Modify: `tests/test_mcp_beta.py`
- Create: `tests/test_beta_integration.py`
- Modify: `tests/test_readonly_storage.py`
- Modify: `tests/test_oauth_http.py`
- Modify: `tests/test_mcp_contract.py`

**Interfaces and scenarios:**
- A beta fixture creates two named boards through Hermes canonical fixtures, then uses MCP to create a third clearly named beta dogfood board.
- A beta board-creation token can create exactly one board, the new board appears in `list_boards`, the current/default marker is unchanged, and a repeated slug returns Hermes' canonical idempotent result.
- A selected-board management token can add a comment and assign a task on board A; the same token cannot mutate board B.
- A token containing only `hermes:read` cannot call any beta write; a token with `hermes:create` cannot call `create_board`; a token with `hermes:board:create` cannot create a task; a token with `hermes:manage` cannot create a task unless it also has `hermes:create`.
- `get_activity` shows canonical `created`, `commented`, and `assigned` events after the corresponding commands.
- Read-only before/after fingerprints remain equal after all read tools and all denied write attempts.
- Persisted beta DCR clients and refresh records survive a fresh `AuthService` instance and refresh rotation; stable OAuth state is never read.
- MCP discovery exposes the documented beta tools and mutation annotations, while stable discovery remains exactly eight tools.

- [ ] **Step 1: Add the fixture tests before production changes that would make them pass.** Keep test board slugs unique within `tmp_path` and avoid touching live OCI boards.
- [ ] **Step 2: Run the integration subset to establish red failures.**

Run: `pytest -q tests/test_beta_integration.py tests/test_mcp_beta.py tests/test_mcp_contract.py`

Expected: failures limited to missing beta behavior, with the existing stable cases still passing.

- [ ] **Step 3: Implement only the missing glue discovered by the failures.** Do not weaken assertions or replace canonical fixture calls with SQL.
- [ ] **Step 4: Run the full suite and inspect the exact count.**

Run: `pytest -q`

Expected: every existing and beta test passes.

- [ ] **Step 5: Commit the integration and isolation proof.**

```bash
git add tests/test_mcp_beta.py tests/test_beta_integration.py tests/test_readonly_storage.py tests/test_oauth_http.py tests/test_mcp_contract.py
git commit -m "test: prove beta authorization and canonical mutations"
```

### Task 7: Document beta operation, ChatGPT connection, and safe rollback

**Files:**
- Modify: `README.md`
- Modify: `docs/DEPLOYMENT.md`
- Modify: `docs/SECURITY.md`
- Modify: `docs/architecture/HERMES-INTEGRATION.md`
- Create: `tests/test_beta_docs.py`
- Create: `docs/evidence/BETA-BOARD-MANAGEMENT-PLAN-2026-08-16.md`

**Content:**
- Stable versus beta endpoints and exact tool/scope matrices.
- One-board write-grant semantics and why the `seq66_looper` mismatch is expected when another board is selected.
- Beta OAuth reauthorization instructions, separate DCR/state behavior, and the fact that `create_board` does not grant task-write access to the new board.
- Canonical Hermes function mapping and the explicit absence of tenant administration.
- Systemd/OpenResty installation, private environment requirements, health checks, restart behavior, and rollback to the stable endpoint.
- A dogfood prompt that first calls `list_boards`, creates a uniquely named test board, verifies it, authorizes that board, creates one test card, adds one comment, and assigns it.
- No secrets, bearer values, authorization codes, refresh tokens, or private filesystem paths beyond documented canonical roots.

- [ ] **Step 1: Add failing documentation checks in `tests/test_beta_docs.py` for the beta scope/tool matrix and stable-preservation statements.**
- [ ] **Step 2: Run the documentation checks and verify they fail for absent beta references.**
- [ ] **Step 3: Update the documentation and evidence record with exact implemented behavior and no speculative claims.**
- [ ] **Step 4: Run documentation checks, secret scans, and `git diff --check`.**
- [ ] **Step 5: Commit the documentation.**

```bash
git add README.md docs/DEPLOYMENT.md docs/SECURITY.md docs/architecture/HERMES-INTEGRATION.md tests/test_beta_docs.py docs/evidence/BETA-BOARD-MANAGEMENT-PLAN-2026-08-16.md
git commit -m "docs: document beta board management operation"
```

### Task 8: Execute verification, deployment review, and final handoff

**Files:**
- Review: all beta branch diffs and exact candidate commits
- Verify: `deploy/systemd/hermes-chatgpt-mcp-beta.service`, `deploy/openresty/kanban-mcp-beta.conf`

- [ ] **Step 1: Run complete verification.**

```bash
/home/ubuntu/hermes-agent/venv/bin/python -m pytest -q
/home/ubuntu/hermes-agent/venv/bin/python -m compileall -q hermes_chatgpt_mcp tests scripts
git diff --check master...HEAD
```

- [ ] **Step 2: Check the public tool allowlists.** Confirm stable has eight tools and beta has eleven tools: seven reads, `create_task`, `create_board`, `add_comment`, and `assign_task`.
- [ ] **Step 3: Run a local beta ASGI OAuth/MCP smoke test.** Verify DCR, PKCE, authorization, token scopes, tool discovery, read-only denial, board creation, card comment, assignment, and restart-style state reload without printing secrets.
- [ ] **Step 4: Inspect the full diff for SQL mutation, scope bypasses, arbitrary update surfaces, path exposure, and accidental stable behavior changes.**
- [ ] **Step 5: Validate the beta systemd unit with `systemd-analyze verify` and OpenResty syntax using the existing deployment process.** Do not restart the stable service.
- [ ] **Step 6:** If the beta hostname and TLS are available, deploy only the beta unit, run health/OAuth/MCP checks, and perform one controlled beta restart. Otherwise leave deployment prepared and report the external DNS/TLS prerequisite explicitly.
- [ ] **Step 7: Confirm the final worktree is clean, record the exact beta HEAD SHA, and produce the final review with stable endpoint status, tests, scopes, tools, and known limitations.**
