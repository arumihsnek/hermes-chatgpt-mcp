# V4 Evidence and Open Questions

**Status:** CANONICAL V4 DESIGN / CURRENT EVIDENCE
**Last reconciled:** 2026-08-19
**Documentation base:** 9900c10 (local ref only; deployed SHA NOT_PROVEN)
**See also:** [README.md](README.md) | [CURRENT_STATE.md](CURRENT_STATE.md) | [STALE_DOCS.md](STALE_DOCS.md)

---

## 1. Evidence Hierarchy

Evidence is ranked as follows:

1. **Local source-bound investigations (primary):** t_2d568471 and its seven parents; completed 2026-08-19 without public research, repository writes, or live mutations.
2. **Corrected canonical task artifacts:** t_4d983898 (SoT/inventory), t_484d4ab0 (spec/ADR), t_4ce4ba8f (matrices/index), t_8a7b081c (roadmap/implementation/QA), t_1419658e (final 79-entry catalog).
3. **Operator-authoritative live discovery:** connector discovery on 2026-08-19 showing 54 exposed tools. This proves exposure only, never behavioral validation.
4. **Behavioral evidence:** actual invocation in the docs session or prior board QA. This is required for `AVAILABLE_VALIDATED`.
5. **Historical repository documents:** dated v0.1/v0.3/v0.4 contracts, deployment notes, reviews, and evidence. They remain useful within their date/scope but do not override newer source-bound findings without revalidation.

### Binding rules

- Current-state claims must include Hermes version and local documentation base; exact deployed connector SHA remains **STILL_NOT_PROVEN**.
- `Kanban_Beta` is stale discovery metadata; controller evidence classifies deployment as STABLE. Do not infer deployed version from the label.
- CLI/source is an oracle/contrast for dogfood; MCP calls are the subject under test.
- CLI registration or `--help` output is not behavioral PASS.
- Current scope vocabulary is exactly `hermes:read`, `hermes:create`, `hermes:manage`, `hermes:board:create`; `offline_access` is connection-only. Finer scopes are PROPOSED only.
- Mutating dogfood uses disposable `hermes-chatgpt-e2e-*` fixtures only, never the project board `hermes-chatgpt-mcp`.

---

## 2. Remaining STILL_NOT_PROVEN Items

| Item | Why unresolved | Impact / next safe evidence |
|------|----------------|-----------------------------|
| Exact deployed connector SHA | Discovery metadata does not pin an immutable deployment commit; local 9900c10 is documentation base only | Pin exact SHA from authenticated deployment evidence before release promotion |
| Live HTTP/API auth and reachability | Dashboard/native API reachability and auth were not proven in the read-only run | Safe authenticated health/read probe in a controlled environment |
| Dashboard plugin live mount/auth | Source endpoints exist, but running gateway mount was not proven | Read-only plugin status/health evidence before workers/run MCP contracts |
| Provider/model validity and quota | Profile configuration and provider credentials were not exercised | Controlled non-mutating provider validation |
| Temporary per-task skill resolution | Partial source resolution depends on profile contents and dispatcher context | Disposable task preflight with no production mutation |
| Fine-grained profile permission enforcement | No Hermes-core enforcement path found; capabilities/refuses are advisory | Treat as advisory until explicit enforcement evidence exists |
| Managed overlay/effective controller config | Effective values known in places, complete overlay composition not pinned | Capture sanitized effective config in a controlled run |
| Live SQLite schema dump | Source schema inspected; live instance not dumped | Read-only schema introspection on disposable board |
| Native MCP/plugin/dynamic registration | Registry and static toolsets are inventoried; all runtime registration paths not proven | Read-only tool registry/runtime inventory |
| Skill metadata plugin integration | Local/builtin/hub origin semantics are known, plugin metadata source not fully proven | Read-only skill listing/view evidence |
| ChatGPT client `content_base64` support | Connector schema lacks remote field today; client ability to send future field is not proven | Contract/E2E test after schema extension |
| Current scopes for tools beyond explicit mappings | Catalog intentionally marks them `NOT_PROVEN / inherited policy` | Inspect live schema per tool; do not infer by operation type |

### Explicit current scope mappings

- `hermes:read`: all read-only tools (baseline).
- `hermes:create`: proven for `create_task` only.
- `hermes:manage`: proven for `add_comment` and `assign_task` only.
- `hermes:board:create`: proven for `create_board` only.
- `offline_access`: connection flow only; not a tool scope.

---

## 3. UNSAFE_TO_TEST Items

These remain unresolved by design because testing them against a live/protected control plane would mutate state or kill work:

| Item | Safety reason | Required test boundary |
|------|---------------|------------------------|
| Live `/kanban` connector delivery/ACL | Could exercise production write/auth paths | Disposable fixture + explicit auth test environment |
| Live terminate/reclaim/slash behavior | Can terminate or reclaim a worker/task | Disposable worker/run with guarded terminate contract |
| Live heartbeat/stale/crash/timeout behavior | Can alter liveness state and trigger reclamation | Disposable fixture with controlled clock/process |
| Raw terminal/process operations | Unrestricted process/shell behavior has no MCP-safe contract | Never expose through MCP |
| Destructive `gc`/`repair`/board deletion/workdir mutation | Data-integrity or filesystem mutation | Explicitly guarded admin environment; risk-based DO_NOT_EXPOSE |
| Secrets/auth/login/logout/update/uninstall operations | Credential/system state mutation | Never expose through MCP |

`UNSAFE_TO_TEST` is not the same as `NOT_PROVEN`: the former is a safety classification; the latter is an evidence gap.

---

## 4. Product and Surface Reconciliation

- **Live discovery:** 54 tools (18 read/introspection and 36 writes/actions).
- **Final catalog:** 79 entries, separating current exposure, current behavioral status, and planned V4 contract.
- **Native registry:** 87 unique leaf tools across 31 registry toolsets; not blanket operational availability.
- **Profiles:** 14 total; observed end-to-end spawn exactly `investigator`, `profile-architect`, `operator`, `software-architect`.
- **Skills:** 53 enabled semantics on default profile (39 builtin, 14 local, 0 hub); `sdlc-review` force-loaded for review dispatch.
- **CLI:** 74 top-level commands and 47 Kanban subcommands; no requirement to implement all 47 via MCP.
- **Specialized current gaps:** rich profiles/skills, validation, runtime info, `get_run`/`inspect_run`/`workers_active`/guarded terminate, remote base64 attachment, and general task edit.
- **Current `edit_task`:** completed-result edit only; full general task edit is planned V4.
- **Current `attach`:** local-path/server staging; remote `content_base64` planned V4. Hermes internal agent already supports `content_base64`.
- **Current `dispatch`:** exposed but manual call observed `BACKEND_ERROR`; classify `AVAILABLE_INCONSISTENT`.
- **Current `daemon`:** bounded MCP status/snapshot; standalone Hermes CLI daemon is deprecated.
- **Risk surfaces:** `gc`, `repair`, `boards-rm`, and workdir mutation are exposed but risk/admin/normal-use DO_NOT_EXPOSE candidates, not absent.
- **Pause/resume:** no board-local pause/resume; global ESTOP only.

---

## 5. Dogfood Incidents

1. **Post-complete artifact freeze (t_484d4ab0):** `kanban_complete` freezes durable result/artifacts; later workspace edits must not silently mutate completed artifacts. Corrections require explicit reissue/versioning.
2. **t_343 nonconvergence:** an earlier roadmap stream did not converge on the corrected scope/vocabulary; t_8a7b081c supersedes it.
3. **t_702 integration/stash incident:** the prior integration worker created a pre-safety stash. This task did not inspect, repair, drop, or mutate that stash or its non-authoritative worktree.
4. **Discovery vs stale checkout:** live discovery shows 54 tools while the documentation base checkout is older; discovery and local checkout must be reconciled explicitly.
5. **get_board capability inconsistency:** capability readback was inconsistent with successful writes; retain as a known issue until independently resolved.
6. **Manual dispatch `BACKEND_ERROR`:** current `dispatch` exposure exists, but a manual call returned `BACKEND_ERROR`; do not call it validated.

---

## 6. Stale-Claim Checks

The canonical set explicitly rejects these claims or scopes them correctly:

| Stale claim | Canonical treatment |
|-------------|---------------------|
| `9 live tools` | Replaced by 54-tool live discovery and 79-entry final catalog |
| `list_profiles` is CURRENT/live | It is a planned rich V4 contract; CLI evidence is not live MCP exposure |
| `board:read|board:write|board:admin` or `kanban:read|kanban:write|kanban:admin` are current | Replaced by current proven scope vocabulary; finer scopes are PROPOSED only |
| `implement all 47` | Explicitly rejected; inventory all 47, expose only approved MCP contracts |
| `hermes kanban inspect` is required/current | Explicitly rejected; use dashboard/source primitive for V4 `inspect_run` |
| Mutating dogfood against `hermes-chatgpt-mcp` | Explicitly prohibited; use disposable `hermes-chatgpt-e2e-*` fixtures |
| `--help` proves behavioral validation | Explicitly rejected; registration ≠ behavioral PASS |
| Agent must be changed to send base64 | Incorrect; Hermes internal agent already supports `content_base64`; MCP transport is missing it |
| Deployed SHA is known from local ref or `Kanban_Beta` | Explicitly rejected; deployed connector SHA is STILL_NOT_PROVEN |

---

## 7. Source and Historical References

- Canonical source task: t_4d983898 (`SOURCE-OF-TRUTH-DRAFT.md`)
- Stale inventory source: t_4d983898 (`STALE-DOCS-INVENTORY.md`)
- Corrected spec/ADR: t_484d4ab0
- Matrices/index: t_4ce4ba8f
- Roadmap/implementation/QA: t_8a7b081c
- Final catalog: t_1419658e
- Synthesis/local evidence: t_2d568471 and parents
- Historical repository docs: [STALE_DOCS.md](STALE_DOCS.md)
