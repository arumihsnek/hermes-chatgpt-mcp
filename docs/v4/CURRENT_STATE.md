# CURRENT_STATE — Authoritative Current-State Document for arumihsnek/hermes-chatgpt-mcp

**Date:** 2026-08-19
**Author:** investigator (t_4d983898) (integrated by github-steward task t_70297725)
**Primary Evidence:** V4-LOCAL-SYNTHESIS (t_2d568471) + 7 parent investigations
**Hermes Version:** v0.20.2 (2026.8.16)
**Source HEAD:** 39cfd1ab41 (+2 carried commits, upstream b7bed241)
**Install Path:** /home/ubuntu/hermes-agent (git install)
**Board:** hermes-chatgpt-mcp

---

## 1. Evidence Provenance Hierarchy

This document derives exclusively from **local read-only investigations** completed on 2026-08-19. No public research, no repository modifications, no live mutations were performed.

| Layer | Task ID | Profile | Artifact | Scope |
|-------|---------|---------|----------|-------|
| Synthesis | t_2d568471 | software-architect | `V4-LOCAL-SYNTHESIS-REPORT_1.md`, `synthesis-metadata.json` | Reconciles all parents with Advanced Research baseline |
| Profiles | t_c2257b50 | investigator | `V4-LOCAL-PROFILES-INVESTIGATION.md`, `profile-evidence.json` | 14 profiles, spawnability, toolsets, docs/runtime |
| Skills | t_2d78d03f | profile-architect | `V4-LOCAL-SKILLS-INVESTIGATION_1.md` | 53 enabled skills, origins, sdlc-review force-load |
| CLI | t_59a2a2f5 | operator | `findings.txt` | 74 top-level commands, 47 kanban subcommands |
| Config | t_ef94f514 | investigator | `V4-LOCAL-CONFIG-report.md` | SQLite schema, workspace/branch, pause/resume, dynamic config |
| Runtime | t_ad6925aa | investigator | `V4-LOCAL-RUNTIME-report.md` | Gateway, dispatcher, workers, runs, build provenance |
| Attachments | t_2499ad0a | software-architect | `REPORT-t_2499ad0a-attachments-contract.md` | 4-surface contract matrix, MCP connector gap |
| Native Tools | t_5caf4595 | software-architect | `native_tools_inventory.json`, `native_tools_inventory_report.md` | 87 tools, 31 registry toolsets, origin/risk/availability |

**Gate Decision (from synthesis):** `INVENTORY_COMPLETE_FOR_V4_DOCS` — All 8 LOCAL items RESOLVED_LOCALLY; remaining STILL_NOT_PROVEN items are non-blocking for P0/P1 tool contract design.

---

## 2. Kanban_Beta Naming — Stable vs Stale

| Item | Status | Evidence |
|------|--------|----------|
| Connector discovery label `Kanban_Beta` | **STALE METADATA** — not backend evidence | Controller correction: deployment is STABLE (t_2d568471 comment, t_ad6925aa) |
| Backend classification | STABLE | t_ad6925aa: "deployment is STABLE per controller correction" |
| Local source | v0.20.2, HEAD 39cfd1ab41 | `hermes version`, git log |
| Inference rule | **Do not infer backend beta from namespace** | Baseline ledger comment |

---

## 3. Hermes Version & Build Provenance

| Field | Value | Source |
|-------|-------|--------|
| Hermes version | 0.20.2 (2026.8.16) | `hermes version` (t_ad6925aa) |
| Upstream SHA | b7bed241 | `hermes version` |
| Local HEAD | 39cfd1ab41 (+2 carried commits) | `git log -1 --oneline` |
| Install directory | /home/ubuntu/hermes-agent | `hermes version` |
| Install method | git | `hermes version` |
| Python | 3.11.15 | `hermes version` |
| OpenAI SDK | 2.24.0 | `hermes version` |
| Executable | /home/ubuntu/.local/bin/hermes | `which hermes` |
| Connector deployed SHA | **STILL_NOT_PROVEN** | t_2499ad0a: local master fd0286c stale; beta/worktree 9900c10 has attach; live schema confirms deployed version ahead |

---

## 4. Profile Inventory — 14 Profiles

**Source:** t_c2257b50 (V4-LOCAL-PROFILES), t_2d568471 synthesis

| Profile | Description | Purpose | Model/Provider | Runtime Skills | Effective CLI Toolsets | Disponible | Spawnability | Evidence |
|---------|-------------|---------|----------------|----------------|------------------------|------------|--------------|----------|
| **default** | Full-stack dev & multi-agent coordination | Orchestration, profile/skill mgmt, planning; not impl/deploy | mimo-v2.5 / opencode-go | 358 | 18 | YES | INFERRED_ONLY | t_c2257b50 |
| **coder** | TDD & systematic investigation | Software impl, tests, debugging, DB work, spikes | poolside/laguna-xs-2.1 / nvidia | 10 | 18 | YES | INFERRED_ONLY | t_c2257b50 |
| **github-steward** | Bounded provenance-first GitHub ops | Bounded GitHub inspection/proposal/authorized ops | nvidia/nemotron-3-super-120b-a12b / nvidia | 79 | 18 | YES | INFERRED_ONLY | t_c2257b50 |
| **investigator** | Systematic debugging, code review, research | Reproducible technical investigation, debugging, code review, research synthesis | nvidia/nemotron-3-ultra-550b-a55b / nvidia | 95 | 18 | YES | **OBSERVED** (t_c2257b50, t_ef94f514, t_ad6925aa) | t_c2257b50 |
| **kahuku** | Surface Go 3 hardware-dependent ops | Hardware runtime env ops, build/deploy/verify | mimo-v2.5 / opencode-go | 5 | 15 | YES | INFERRED_ONLY | t_c2257b50 |
| **kahuku-candidate** | Candidate Surface Go 3 profile | Hardware-dependent correction validation | mimo-v2.5 / opencode-go | 91 | 4 | YES | INFERRED_ONLY | t_c2257b50 |
| **kanban-coordinator** | Kanban control-plane routing | DAG construction/repair, outcome interpretation, gates | nvidia/nemotron-3-ultra-550b-a55b / nvidia | 92 | 18 | YES | INFERRED_ONLY | t_c2257b50 |
| **operator** | Android ADB/bridge execution | ADB/bridge, import/execute, state capture, evidence bundles | nvidia/nemotron-3-super-120b-a12b / nvidia | 9 | 18 | YES | **OBSERVED** (t_59a2a2f5) | t_c2257b50 |
| **profile-architect** | Design/improve profiles, prompts, skills | Profile design, audit, validation, architecture diagrams | z-ai/glm-5.2 / nvidia | 53 | 16 | YES | **OBSERVED** (t_2d78d03f) | t_c2257b50 |
| **researcher** | Text/web-first technical research | Source-grounded research, non-destructive experiments | nvidia/nemotron-3-nano-30b-a3b / nvidia | 7 | 18 | YES | INFERRED_ONLY | t_c2257b50 |
| **reviewer** | Adversarial evidence/contract review | Fail-closed verdicts on changes/PR, regressions, security | z-ai/glm-5.2 / nvidia | 14 | 18 | YES | INFERRED_ONLY | t_c2257b50 |
| **software-architect** | Tasker XML/IR architecture, schemas | Architecture decisions, ADRs, event sourcing, canonical data models | z-ai/glm-5.2 / nvidia | 9 | 5 | YES | **OBSERVED** (t_5caf4595, t_2499ad0a, t_2d568471) | t_c2257b50 |
| **wilson** | Personal secretary & Obsidian second-brain | Personal secretary, Obsidian management | nvidia/nemotron-3-nano-30b-a3b / opencode-go | 91 | 15 | YES | INFERRED_ONLY | t_c2257b50 |
| **worker** | Low-risk mechanical execution | Mechanical edits, formatting, extraction, trivial tests | nvidia/nemotron-3-super-120b-a12b / nvidia | 3 | 18 | YES | INFERRED_ONLY | t_c2257b50 |

**Spawnability Classification (corrected per synthesis):**
- **OBSERVED (end-to-end spawn):** `investigator` (3 tasks), `profile-architect` (1), `operator` (1), `software-architect` (3) — 4 profiles
- **INFERRED_ONLY (dispatcher-eligible by profile_exists predicate):** 10 profiles
- **Dispatcher gate:** `profile_exists(assignee)` only; no enforcement of `kanban.capabilities/refuses` (t_c2257b50)

**Toolset Mismatch (critical for routing):**
- Profiles WITHOUT `platform_toolsets.cli` (coder, investigator, researcher, reviewer, worker, etc.) inherit broad `hermes-cli` composite → **18 tools**
- Profiles WITH explicit `platform_toolsets.cli` (software-architect=5, kahuku-candidate=4, kahuku=15, wilson=15) → narrow surface
- **Routing implication:** Use runtime effective CLI toolsets, not legacy top-level `toolsets:` field (t_c2257b50, P1-1)

---

## 5. Skill Inventory — 53 Enabled Skills

**Source:** t_2d78d03f (V4-LOCAL-SKILLS), t_2d568471 synthesis

| Origin | Count | Discovery | Trust |
|--------|-------|-----------|-------|
| **builtin** | 39 | `.bundled_manifest` + source tree `/home/ubuntu/hermes-agent/skills/` | Builtin |
| **local** | 14 | `HERMES_HOME/skills/` + `skills.external_dirs` | Local |
| **hub** | 0 | Hub lockfile `~/.hermes/skills/.hub/lock.json` | Community |
| **plugin** | varies | `PluginManager.list_plugin_skill_metadata()` | Varies |

**Key Skills (profile-architect runtime):**

| Skill | Purpose | Origin | Special State |
|-------|---------|--------|---------------|
| **sdlc-review** | Review Kanban handoffs, route verified outcomes | builtin | **FORCE-LOADED** by dispatcher into review workers at `kanban_db.py:10384`; NOT in `reviewer` profile local skills; `hermes skills inspect` CANNOT resolve it (hub-only search) |
| **hermes-agent** | Platform ops, config, gateway mgmt | builtin | — |
| **profile-craft** | Profile authoring, validation, SOUL.md | local (profile dir) | — |
| **prompt-engineering** | Prompt authoring, SOUL.md generation | local (profile dir) | — |
| **kanban-complete-guard** | Prevent premature task completion | local (profile dir) | — |
| **hermes-dojo** | Continuous self-improvement | local (symlink) | — |
| **merge-reconciler** | Neutral merge conflict resolution | builtin | — |
| **systematic-debugging** | 4-phase root cause debugging | builtin | — |
| **test-driven-development** | TDD workflow | builtin | — |
| **github-pr-workflow** | PR lifecycle | builtin | — |
| **github-code-review** | Code review via gh/REST | builtin | — |

**CLI Limitation:** `hermes skills inspect` **only searches hub sources** — fails for builtin/local skills despite being loadable via `skill_view()`. V4 must use `skills list` or `skill_view` (t_2d78d03f, P0-4).

**Missing-Skill Runtime Policy (unchanged):**
- ALL missing → hard fail (ValueError, rc=1)
- SOME missing → warn + continue (t_2d78d03f, t_d6817074)

**Task Skill Override Semantics:**
- Creation skills preserved in order
- Force-load appends (e.g., `sdlc-review` for review lane)
- Worker receives union (t_2d78d03f)

### Complete enabled-name inventory

The profile-architect runtime inventory reports **53 enabled names**: 39 builtin, 14 local, and 0 hub. The lists below preserve the recorded origin categories; descriptions are concise paraphrases of the installed skill metadata where available (t_2d78d03f).

**Builtin (39):**

| Skill | Brief purpose |
|-------|---------------|
| `sdlc-review` | Review Kanban handoffs and route verified outcomes |
| `hermes-agent` | Use, configure, theme, extend, and orchestrate Hermes Agent |
| `merge-reconciler` | Neutral resolution of agent merge conflicts |
| `systematic-debugging` | Four-phase root-cause debugging |
| `test-driven-development` | RED-GREEN-REFACTOR TDD workflow |
| `github-pr-workflow` | GitHub PR lifecycle |
| `github-code-review` | Review PR diffs/comments through gh or REST |
| `requesting-code-review` | Pre-commit security and quality review |
| `dogfood` | Exploratory QA of web applications |
| `grounded-citations` | Ground answers in cited, verifiable sources |
| `pretext` | Creative browser demos with DOM-free text layout |
| `touchdesigner-mcp` | Control TouchDesigner through twozero MCP |
| `email-inbox-triage` | Prioritize inbox threads and draft replies |
| `codebase-inspection` | Inspect codebases with pygount |
| `github-auth` | GitHub authentication setup |
| `github-issue-to-pr` | Carry a GitHub issue to a verified PR |
| `github-issues` | Create, triage, label, and assign issues |
| `github-repo-management` | Clone/manage repositories and releases |
| `gif-search` | Search/download GIFs from Tenor |
| `evaluating-llms-harness` | Run lm-eval-harness model benchmarks |
| `weights-and-biases` | W&B experiment tracking and registry |
| `box` | Manage Box cloud files and sharing |
| `document-to-action-items` | Extract obligations and action items from documents |
| `docx` | Create/read/edit Word documents and templates |
| `meeting-action-items` | Turn meeting notes into cited decisions and tickets |
| `pdf` | Create, merge, split, fill, and secure PDFs |
| `product-price-monitor` | Monitor product, flight, or listing prices |
| `session-librarian` | Organize sessions by prompt |
| `weekly-review-planning` | Weekly reset of commitments and next steps |
| `xlsx` | Create/read/edit Excel workbooks and CSVs |
| `blocked-page-recovery` | Recover blocked, paywalled, or WAF pages |
| `competitor-news-monitor` | Monitor named companies for material news |
| `llm-wiki` | Build/query Karpathy's interlinked LLM Wiki |
| `spike` | Throwaway experiments to validate an idea |
| `simplify-code` | Parallel cleanup of recent code changes |
| `hermes-agent-skill-authoring` | Author in-repo `SKILL.md` files |
| `inspecting-hermes-desktop-dom` | Inspect live Hermes desktop DOM/CSS over CDP |
| `plan` | Write a markdown plan to `.hermes/plans/` |
| `python-debugpy` | Debug Python with pdb/debugpy |

**Local (14):**

| Skill | Brief purpose |
|-------|---------------|
| `profile-craft` | Design and validate Hermes profile distributions |
| `prompt-engineering` | Turn a profile idea into a mature prompt/SOUL |
| `kanban-complete-guard` | Guard against completion without `kanban_complete` |
| `hermes-dojo` | Continuous Hermes self-improvement and pitfalls |
| `skill-gap-diagnostics` | Capture skill gaps and compute coverage |
| `hermes-profile-maintenance` | Audit installed Hermes profiles |
| `lifecycle-unacknowledged-exit` | Park workers exiting without lifecycle acknowledgement |
| `health-confidence-scoring` | Wilson-score profile health labels |
| `blocked-criteria-refinement` | Reduce blocked rates through dependency criteria |
| `wilson-proposals-cycle-fix` | Fix structural cycles in proposals boards |
| `hermes-themes` | Author Hermes color themes |
| `hermes-desktop-plugins` | Write desktop app plugins |
| `tui-widgets` | Author live Hermes TUI dock widgets |
| `skill-gap-diagnostics-merged` | `[MERGED]` consolidated diagnostics; marked disabled/merged in the source inventory |

**Hub:** 0 enabled names. **Plugin:** plugin metadata is a separate possible origin, but no plugin inventory was established by this mission; do not silently fold it into the 53-name enabled count.

---

## 6. CLI & Kanban Command Trees

**Source:** t_59a2a2f5 (findings.txt), t_2d568471 synthesis

### Top-Level Hermes Commands (74 registered)
```
hermes {chat, model, moa, fallback, secrets, egress, migrate, gateway, proxy, lsp,
setup, whatsapp, whatsapp-cloud, slack, send, login, logout, auth, status, pause,
resume, cron, sync, webhook, portal, kanban, project, hooks, doctor, verify,
security, approvals, dump, debug, backup, checkpoints, import, import-agent,
config, skin, console, pairing, skills, bundles, plugins, curator, pets, journey,
learning, memory-graph, memory, tools, computer-use, mcp, sessions, insights,
monitoring, claw, version, update, uninstall, acp, profile, completion, dashboard,
serve, desktop, gui, logs, prompt-size}
```

### Kanban Subcommands (47 registered)
```
hermes kanban {init, boards, create, swarm, list, ls, show, assign, set-model,
reclaim, reassign, diagnostics, diag, link, unlink, claim, comment, attach,
attachments, attach-rm, complete, edit, block, schedule, unblock, request-review,
request-changes, reopen-review, promote, archive, tail, dispatch, daemon, watch,
stats, notify-subscribe, notify-list, notify-unsubscribe, log, runs, heartbeat,
assignees, context, specify, decompose, gc, repair}
```

**Special Notes:**
- `daemon` = DEPRECATED (dispatch embedded in gateway)
- `diag` = alias for `diagnostics`
- `ls` = alias for `list`
- **No `kanban pause` / `kanban resume` subcommand exists** (t_ef94f514)

**CRITICAL CAVEAT:** `--help` registration proves command EXISTS in CLI parser. It does **NOT** prove operational PASS for every leaf. Only exercised subcommands have behavioral evidence:
- **Exercised (proven):** `list`, `show`, `runs`, `diagnostics`, `assignees`, `boards`, `stats`, `context`, `log`, `attach`, `attachments`, `comment`, `complete`, `heartbeat`, `dispatch`
- **Registered only (unverified leaf behavior):** `daemon`, `watch`, `schedule`, `swarm`, `repair`, `gc`, `decompose`, `specify`, `create`, `edit`, `block`, `unblock`, `request-review`, `request-changes`, `reopen-review`, `promote`, `archive`, `assign`, `set-model`, `reclaim`, `reassign`, `link`, `unlink`, `claim`, `notify-*`

---

## 7. Native Tool Registry Summary

**Source:** t_5caf4595 (V4-LOCAL-NATIVE-TOOLS)

| Metric | Value |
|--------|-------|
| Total unique leaf tools | 87 |
| Static toolsets (toolsets.py) | 59 |
| Registry toolsets (from ToolEntry.toolset) | 31 |
| Plugin-registered toolsets | 2 (browser-cdp, browser-use) |
| Unique toolsets across both | 33 |
| Origin: BUILTIN | 87 |
| Origin: PLUGIN | 0 |
| Origin: MCP | 0 |
| Origin: DYNAMIC | 0 |
| Risk: READ_ONLY | 39 |
| Risk: MUTATING | 48 |
| Availability: always_available | 14 |
| Availability: check_fn_available | 69 |
| Availability: requires_env | 4 (EXA/TAVILY/FIRECRAWL, XAI, DISCORD_BOT_TOKEN) |

### Core `hermes-cli` Toolset Composition (54 unique tools)
| Toolset | Tools | Count |
|---------|-------|-------|
| web | web_search, web_extract | 2 |
| terminal | terminal, process | 2 |
| file | read_file, write_file, patch, search_files | 4 |
| vision | vision_analyze | 1 |
| image_gen | image_generate | 1 |
| bfl | flux3 video generation suite | 6 |
| skills | skills_list, skill_view, skill_manage | 3 |
| browser | browser_* suite | 13 |
| tts | text_to_speech | 1 |
| todo | todo | 1 |
| memory | memory | 1 |
| session_search | session_search | 1 |
| clarify | clarify | 1 |
| code_execution | execute_code | 1 |
| delegation | delegate_task | 1 |
| cronjob | cronjob | 1 |
| homeassistant | ha_* suite | 4 |
| kanban | kanban_* suite | 14 |
| computer_use | computer_use | 1 |

---

## 8. Gateway / Dispatcher / Workers / Runs / Build / Runtime

**Source:** t_ad6925aa (V4-LOCAL-RUNTIME), t_ef94f514 (V4-LOCAL-CONFIG)

### Build Provenance
| Field | Value |
|-------|-------|
| Version | 0.20.2 (2026.8.16) |
| Upstream | b7bed241 |
| Local HEAD | 39cfd1ab41 (+2) |
| Install | /home/ubuntu/hermes-agent (git) |
| Python | 3.11.15 |
| OpenAI SDK | 2.24.0 |
| Executable | /home/ubuntu/.local/bin/hermes |

### Gateway
- **Default profile gateway:** RUNNING (PID 3968293)
- **Investigator profile gateway:** INACTIVE (systemd unit dead)
- **API-server port conflict:** Warning on port 8642
- **Connector label:** `Kanban_Beta` = STALE NAMESPACE (deployment is STABLE)

### Dispatcher (embedded in gateway)
- **Enabled by:** `kanban.dispatch_in_gateway=true` (default)
- **Singleton lock:** `<kanban_home>/kanban/.dispatcher.lock` (machine-global)
- **Board-scoped lock:** `dispatch_once()` acquires per-board lock
- **Tick interval:** 60s (default, from `kanban.dispatch_interval_seconds`)
- **Tick sequence:** reap zombies → check ESTOP → auto-decompose → enumerate boards → `dispatch_once()` per board
- **Auto-decompose:** Re-read each tick (live safety toggle), capped at `auto_decompose_per_tick=3`
- **Standalone daemon:** Exists but CLI-deprecated

### Worker Spawn (`_default_spawn` at `kanban_db.py:10709`)
- **Prompt:** `work kanban task <task_id>`
- **Child env:** Profile-scoped `HERMES_HOME`, `HERMES_PROFILE`, `HERMES_KANBAN_DB/BOARD/WORKSPACES_ROOT`, `HERMES_SESSION_SOURCE=kanban`
- **argv:** `hermes -p <assignee> --cli --accept-hooks [--skills ...] chat -q "work kanban task <task_id>"`
- **Subprocess:** detached, `start_new_session=True`, `cwd=workspace`, stdin=DEVNULL, stdout/stderr→log

### Active Workers / Runs / Inspect / Terminate
| Surface | Commands / Endpoints |
|---------|---------------------|
| **CLI** | `kanban list --status running --json`, `kanban runs <task_id> --json`, `kanban context`, `kanban log`, `kanban diagnostics`, `kanban stats`, `kanban assignees`, `kanban tail`, `kanban heartbeat` |
| **Dashboard API** | `GET /api/plugins/kanban/workers/active`, `GET /api/plugins/kanban/runs/{run_id}`, `GET /api/plugins/kanban/runs/{run_id}/inspect` (psutil), `POST /api/plugins/kanban/runs/{run_id}/terminate` (calls `reclaim_task()`) |
| **Native API-server** | `POST /v1/runs`, `GET /v1/runs/{run_id}`, `GET /v1/runs/{run_id}/events`, `POST /v1/runs/{run_id}/approval`, `POST /v1/runs/{run_id}/steer`, `POST /v1/runs/{run_id}/stop` |

**Key distinction:** Dashboard Kanban API paths (`/api/plugins/kanban/...`) are **separate** from native `/v1/runs` paths. Kanban terminate routes through `reclaim_task`; native `/stop` interrupts API-server agent runs.

### Heartbeat / Stale / Crash / Timeout / Retry
| Parameter | Value | Source |
|-----------|-------|--------|
| Default claim TTL | 15 minutes | `DEFAULT_CLAIM_TTL_SECONDS` |
| Heartbeat-stale threshold | 1 hour | `DEFAULT_CLAIM_HEARTBEAT_MAX_STALE_SECONDS` |
| Crash grace | 30 seconds | `DEFAULT_CRASH_GRACE_SECONDS` |
| Dispatch stale timeout | 4 hours | `dispatch_stale_timeout_seconds=14400` |
| Failure limit | 2 consecutive | Auto-blocks task |
| Rate-limit (exit 75) | Temporary | Not counted as failure |

**Live behavior for above:** UNSAFE_TO_TEST (would mutate state or require induced failure)

---

## 9. Attachments Contract (4-Surface Matrix)

**Source:** t_2499ad0a (V4-LOCAL-ATTACHMENTS)

| Transport | Hermes Agent | MCP Connector (beta) | Remote ChatGPT Client |
|-----------|--------------|----------------------|----------------------|
| **local_path** | N/A | PRESENT (staging-root restricted) | **ABSENT** (client cannot provide server path) |
| **base64 (inline)** | PRESENT (`content_base64`) | **ABSENT** (not in AttachInput) | NOT_PROVEN (MCP protocol allows, connector doesn't) |
| **raw bytes** | INTERNAL_ONLY (decoded from base64) | INTERNAL_ONLY (read from local_path) | ABSENT (no transport) |
| **multipart** | ABSENT | ABSENT | N/A (MCP uses JSON-RPC) |
| **URL (server fetch)** | PRESENT (`kanban_attach_url`) | ABSENT | NOT_PROVEN |

**Security Boundary:**
- Agent tools: in-process, accept base64 from model, decode/write
- MCP connector: reads `local_path` from **server filesystem**, validated against `MCP_ATTACHMENT_STAGING_ROOT`
- Remote client **cannot** provide server-local filesystem path

**Critical Gap:** MCP `attach(local_path=...)` is **architecturally wrong for remote clients** — returned `CONFLICT` when workspace path not within staging root (t_2499ad0a).

**Size Caps (mismatch):**
- Agent: `KANBAN_ATTACHMENT_MAX_BYTES = 25 MB`
- MCP connector: `MCP_MAX_ATTACHMENT_BYTES` default 10 MB
- **P0-2:** Unify to single cap

---

## 10. Config / Schema / Workspace / Branch

**Source:** t_ef94f514 (V4-LOCAL-CONFIG), t_2d568471

### Formal Board Schema (SQLite)
**Source:** `hermes_cli/kanban_db.py:SCHEMA_SQL` — 7 durable tables + indexes
- `tasks` — identity, title/body, assignee/status/priority, timestamps, workspace kind/path, branch/project, claim state, tenant, retry/failure, worker PID, runtime/heartbeat, skills, model/provider/reasoning overrides, goal-loop fields
- `task_links` — parent/child dependency edges
- `task_comments` — durable comments
- `task_events` — append-only lifecycle/events
- `task_runs` — historical attempts with full metadata
- `task_attachments` — attachment metadata and stored paths
- `kanban_notify_subs` — gateway notification subscriptions and cursors

**Live schema dump:** STILL_NOT_PROVEN (sqlite3 CLI unavailable)

### Workspace / Branch Precedence
1. Explicit `workspace_path` retained where valid
2. `scratch` without path → `<board-root>/workspaces/<task-id>` (absolute required)
3. `dir` tasks require explicit absolute `workspace_path`; relative rejected
4. `worktree` → real linked worktree; repo anchor at `<repo>/.worktrees/<task-id>`
5. Explicit `branch_name` valid only for `worktree`; default `wt/<task-id>`
6. Dispatcher/worker path board-pinned via `HERMES_KANBAN_BOARD` env

**Current task (scratch):** Branch enforcement NOT_APPLICABLE

### Pause/Resume & Dispatch Controls
| Control | Exists? | Scope | Mechanism |
|---------|---------|-------|-----------|
| Global pause | YES | New-work only | `hermes pause` writes `$HERMES_HOME/ESTOP`; embedded watcher checks each tick |
| Global resume | YES | — | `hermes resume` removes ESTOP |
| Board-local pause | **NO** | — | No `kanban pause/resume` subcommand; no config key |
| Dynamic config | YES | Varies | `hermes config set`; dashboard `PUT /orchestration` writes config.yaml; `auto_decompose` re-read per tick; others require restart |

---

## 11. Classification Ledger — All LOCAL & NOT_PROVEN Items

### LOCAL-001 through LOCAL-008
| ID | Topic | Classification | Evidence Source |
|----|-------|---------------|-----------------|
| LOCAL-001 | Real Hermes CLI tree | **RESOLVED_LOCALLY** | t_59a2a2f5: full `hermes --help` + `hermes kanban --help` |
| LOCAL-002 | Current installed profiles | **RESOLVED_LOCALLY** | t_c2257b50: 14 profiles via `hermes profile list`, all `on_disk: true` |
| LOCAL-003 | Installed skills inventory | **RESOLVED_LOCALLY** | t_2d78d03f: 53 enabled (39 builtin, 14 local, 0 hub) |
| LOCAL-004 | Active Kanban config | **RESOLVED_LOCALLY** | t_ef94f514: all defaults from `config_defaults.py`; managed overlay caveat |
| LOCAL-005 | Remote attachment/upload contract | **RESOLVED_LOCALLY** | t_2499ad0a: 4-surface matrix; MCP local_path only, base64/URL absent |
| LOCAL-006 | Why reviewer referenced sdlc-review | **RESOLVED_LOCALLY** | t_2d78d03f: force-load at `kanban_db.py:10384`; historical C-IMPL-5 crash |
| LOCAL-007 | `hermes kanban daemon --help` | **RESOLVED_LOCALLY** | t_59a2a2f5: present but DEPRECATED |
| LOCAL-008 | `/kanban` slash/API registration | **RESOLVED_LOCALLY** (registry/source); **UNSAFE_TO_TEST** (live slash) | t_ad6925aa: `CommandDef("kanban")` in commands.py; gateway handler in run.py; slash_commands.py |

### Section 14 NOT_PROVEN Items
| Item | Classification | Notes |
|------|---------------|-------|
| Attachments remote upload (MCP) | **RESOLVED_LOCALLY** | MCP exposes local_path only; base64/URL absent |
| Temporary skills per task | **STILL_NOT_PROVEN** | Code path exists (`kanban_db.py:10446`), but arbitrary name resolution depends on profile |
| Task skill override semantics | **RESOLVED_LOCALLY** | Creation skills preserved; force-load appends; worker receives union |
| Fine-grained profile permissions | **STILL_NOT_PROVEN** | `profile.yaml` has capabilities/refuses but Hermes core only reads description/description_auto |
| Default profiles list | **RESOLVED_LOCALLY** | 14 confirmed via `hermes profile list` |
| Formal board schema | **RESOLVED_LOCALLY** | `SCHEMA_SQL` in `kanban_db.py`; live dump blocked (no sqlite3) |
| Pause/resume dispatch commands | **RESOLVED_LOCALLY_ABSENT** | No `kanban pause/resume`; global ESTOP only |
| Workspace/branch enforcement | **RESOLVED_LOCALLY** | Precedence from source; branch enforcement N/A for scratch |
| Dynamic kanban.* config | **RESOLVED_LOCALLY** | Generic config setter + dashboard orchestration API; per-key reload semantics |

### Section 13 Docs/Runtime Discrepancies
| Discrepancy | Classification | Notes |
|-------------|---------------|-------|
| kanban CLI documented vs claimed absent | **RESOLVED_LOCALLY / BASELINE_OUTDATED_OR_VERSION_DRIFT** | Baseline used older snapshot; v0.20.2 registers kanban with 47 subcommands |
| Missing skills exception→warning | **RESOLVED_LOCALLY** | ALL-missing→hard fail; SOME-missing→warn+continue |
| Gateway list profiles semantics | **RESOLVED_LOCALLY** | Enumerates instances + process status; not all running |
| No pause dispatch (board-local) | **RESOLVED_LOCALLY_ABSENT** | Global pause exists; board-local absent |
| Daemon deprecated | **RESOLVED_LOCALLY** | CLI marked deprecated; dispatch embedded in gateway |
| Profile describe docs/CLI mismatch | **RESOLVED_LOCALLY** | Docs: bare `hermes profile`=help, `*` marker; Runtime: no action=status, `◆` marker |
| Attachment CLI/API uncertainty | **RESOLVED_LOCALLY** | Agent: base64+URL; MCP: local_path only; remote upload gap confirmed |

### Additional Classifications
| Item | Classification |
|------|---------------|
| Historical C-IMPL-5 crash cause | **STILL_NOT_PROVEN** |
| Plugin skill metadata source | **NOT_APPLICABLE** |
| `hermes skills inspect` limitation | **RESOLVED_LOCALLY** (hub-only search) |
| Missing-skill runtime policy | **RESOLVED_LOCALLY** |
| Deployed connector SHA | **STILL_NOT_PROVEN** |
| Live dashboard API auth | **STILL_NOT_PROVEN** |
| Live slash invocation | **UNSAFE_TO_TEST** |
| Kanban terminate live | **UNSAFE_TO_TEST** |
| Heartbeat reclaim live | **UNSAFE_TO_TEST** |
| Kanban_Beta label | **DUPLICATE / stale metadata** |

### Remaining parent-level NOT_PROVEN / UNSAFE_TO_TEST items

These items remain explicitly unresolved or intentionally untested; they are not converted into positive claims by this draft.

| Item | Classification | Source / boundary |
|------|----------------|-------------------|
| Temporary arbitrary per-task skill resolution | **STILL_NOT_PROVEN (partial)** | t_2d78d03f; forwarding `--skills` is proven, arbitrary-name resolution depends on the profile catalog |
| Fine-grained `profile.yaml` capabilities/refuses enforcement | **STILL_NOT_PROVEN** | t_c2257b50; no Hermes-core enforcement path found |
| Exact historical cause of C-IMPL-5 `sdlc-review` crash | **STILL_NOT_PROVEN** | t_2d78d03f; current force-load is proven, historical causal change is not |
| Managed config overlay existence/effective values | **STILL_NOT_PROVEN** | t_ef94f514; active profile/default source values are resolved, managed overlay was not inspected |
| Exact host-derived `max_in_progress` integer | **STILL_NOT_PROVEN** | t_ef94f514; source derives it from host memory, measurement was not captured |
| Exact live SQLite column set for this board | **STILL_NOT_PROVEN** | t_ef94f514; `sqlite3` executable unavailable |
| Separate ChatGPT MCP controller effective configuration | **STILL_NOT_PROVEN** | t_ef94f514; controller status/diagnostics are not config introspection |
| Deployed connector source SHA | **STILL_NOT_PROVEN** | t_2499ad0a; local master is stale relative to discovered live surface |
| Dashboard plugin API live reachability/auth/enablement | **STILL_NOT_PROVEN** | t_ad6925aa; no live HTTP request, port-conflict warning observed |
| Native `/v1/runs` listener availability/auth | **STILL_NOT_PROVEN** | t_ad6925aa; routes exist in source, no live HTTP request |
| Current liveness of recorded worker PID/run | **STILL_NOT_PROVEN** | t_ad6925aa; no `/inspect` or PID probe |
| Prior-audit delta against `t_dcbb9c45` | **STILL_NOT_PROVEN** | t_ad6925aa; historical snapshot not independently re-pinned |
| Provider credentials/model quota for profiles | **STILL_NOT_PROVEN** | t_c2257b50; secrets were not inspected and no provider call was made |
| End-to-end dispatch/completion for the 10 inferred-only profiles | **STILL_NOT_PROVEN** | t_c2257b50 + synthesis correction; only four profiles have observed mission spawn evidence |
| Gateway/messaging spawnability for each profile | **STILL_NOT_PROVEN** | t_c2257b50; gateway status is not worker-capability proof |
| MCP protocol support for base64 file content | **NOT_PROVEN** | t_2499ad0a; connector schema lacks the field and protocol was not separately inspected |
| ChatGPT client ability to send `content_base64` | **NOT_PROVEN** | t_2499ad0a; depends on future connector schema/client behavior |
| MCP URL upload path | **NOT_PROVEN / not implemented** | t_2499ad0a; no URL field is in the discovered connector schema |
| Actual external-state `check_fn` availability of native tools | **UNSAFE_TO_TEST** | t_5caf4595; would require triggering/probing external state |
| MCP-server tool registration | **STILL_NOT_PROVEN** | t_5caf4595; no MCP servers connected |
| Plugin tool registration | **STILL_NOT_PROVEN** | t_5caf4595; no plugins active |
| Context-engine dynamic tools | **STILL_NOT_PROVEN** | t_5caf4595; `context_engine` is empty by default |
| Platform-specific toolset completeness | **STILL_NOT_PROVEN** | t_5caf4595; only core registry was fully inventoried |
| Live `/kanban` connector delivery, ACL, routing, reply rendering | **UNSAFE_TO_TEST** | t_ad6925aa; production slash invocation intentionally not sent |
| Live Kanban terminate/reclaim behavior | **UNSAFE_TO_TEST** | t_ad6925aa; would mutate worker/task state |
| Live heartbeat, stale, crash, timeout, retry, auto-block, requeue behavior | **UNSAFE_TO_TEST** | t_ad6925aa; would mutate state or require induced failure |

---

## 12. MCP Gap List

**Source:** t_2d568471 synthesis, t_2499ad0a, t_5caf4595, t_2d78d03f

| Gap | Severity | Evidence | Recommendation |
|-----|----------|----------|----------------|
| MCP connector `attach(local_path)` is SERVER_LOCAL_BOUND | **BLOCKING** | t_2499ad0a: CONFLICT when workspace path not in staging root | **P0-1:** Add `content_base64` to MCP AttachInput schema |
| Size limit mismatch: agent=25MB vs MCP=10MB | **HIGH** | t_2499ad0a: `KANBAN_ATTACHMENT_MAX_BYTES` vs connector default | **P0-2:** Unify to single cap or document divergence |
| Deployed connector SHA unknown | **MEDIUM** | t_2499ad0a: local master stale, live schema shows attach tool | **P0-3:** Pin deployed connector version before V4 |
| `hermes skills inspect` cannot resolve builtin/local | **MEDIUM** | t_2d78d03f: hub-only search fails for builtin | **P0-4:** V4 skill queries must use `skills list` / `skill_view` |
| sdlc-review force-load pattern | **MEDIUM** | t_2d78d03f: production-critical dispatcher behavior | **P0-5:** Preserve force-load pattern for review workers |
| No board-local pause/resume | **LOW** | t_ef94f514: global ESTOP only | **P1-3:** Document as global control only |
| `profile.yaml` capabilities/refuses not enforced | **LOW** | t_c2257b50: no enforcement path found | **P1-5:** Treat as advisory metadata only |
| Live HTTP auth/enablement of dashboard plugin | **UNKNOWN** | t_ad6925aa: no live request made | **P1-6:** Integration test before V4 MCP tool design |
| Temporary per-task skill injection | **PARTIALLY_RESOLVED** | t_2d78d03f: code path exists, resolution depends on profile | Verify if V4 exposes task creation |

### Recommended MCP Response Shapes for V4
1. `list_native_tools` → `registry.get_all_entries()` with origin, availability, risk_class
2. `get_native_tool` → `registry.get_entry(name)` with full ToolEntry
3. `get_profile_tools` → `registry.get_definitions(tool_names)` filtered by profile toolset config
4. `attach` with `content_base64` field (not just `local_path`)
5. `kanban_*` suite (14 tools) — expose same schemas

---

## 13. Gate Decision & V4 P0/P1 Recommendations

### Gate Decision: `INVENTORY_COMPLETE_FOR_V4_DOCS`

**Rationale:** All 8 LOCAL items RESOLVED_LOCALLY (LOCAL-008 UNSAFE_TO_TEST only for live slash invocation — operational validation, not design blocker). Remaining STILL_NOT_PROVEN items:
1. Temporary skills per task — partial; design can proceed with documented limitation
2. Fine-grained profile permissions — advisory only, no enforcement
3. Historical C-IMPL-5 crash cause — historical, irrelevant to current contract
4. Deployed connector SHA — implementation concern, not document-level
5. Live HTTP auth/enablement — integration test, not document-level

**No remaining P0/P1 blockers for document design.**

### V4 P0 Recommendations (Blocking for Release)
| ID | Description | Evidence |
|----|-------------|----------|
| **P0-1** | Add `content_base64` to MCP connector AttachInput for remote file upload | t_2499ad0a: local_path-only is architecturally wrong for remote clients |
| **P0-2** | Unify attachment size cap (25MB agent vs 10MB MCP) | t_2499ad0a: size mismatch between surfaces |
| **P0-3** | Pin deployed connector SHA before V4 release | t_2499ad0a: local master fd0286c stale, deployed version unknown |
| **P0-4** | V4 skill queries: use `skills list` or `skill_view`, never `inspect` | t_2d78d03f: inspect is hub-only, fails for builtin/local |
| **P0-5** | Preserve sdlc-review force-load pattern for review workers | t_2d78d03f: production-critical; dispatcher appends at dispatch time |

### V4 P1 Recommendations (Important, Non-Blocking)
| ID | Description | Evidence |
|----|-------------|----------|
| **P1-1** | Use runtime effective CLI toolsets for profile routing | t_c2257b50: legacy `toolsets:` produces broader surface than expected |
| **P1-2** | Represent spawnability as `dispatcher_eligible` vs `end_to_end_observed` | t_c2257b50: only investigator has observed spawn |
| **P1-3** | Document global pause (ESTOP) vs board-local pause (absent) | t_ef94f514: no board-local pause exists |
| **P1-4** | Distinguish Kanban dashboard API from native `/v1/runs` paths | t_ad6925aa: separate termination surfaces |
| **P1-5** | Treat `profile.yaml` capabilities/refuses as advisory | t_c2257b50: no enforcement path in Hermes core |
| **P1-6** | Report MCP diagnostics/dispatch failures as backend observability | t_ef94f514: BACKEND_ERROR not config evidence |

---

## 14. Contradiction Ledger (Docs vs Runtime)

| Claim | Docs Source | Runtime Evidence | Verdict | Provenance |
|-------|-------------|------------------|---------|------------|
| `hermes profile` shows help | website docs:9-15 | No action = status display | **Runtime correct** | t_c2257b50 |
| Profile marker is `*` | website docs:33-49 | Uses `◆` marker | **Runtime correct** | t_c2257b50 |
| `hermes tools` configures active profile | website docs:110-119 | True at command level, but toolsets mismatch | **Partially correct** | t_c2257b50 |
| `hermes skills inspect` previews skill metadata | Implicit in CLI help | Hub-only search; fails for builtin/local | **Runtime limited** | t_2d78d03f |
| `hermes kanban daemon` is normal dispatch | CLI help exists | Marked DEPRECATED; dispatch embedded in gateway | **Runtime correct** | t_59a2a2f5, t_ad6925aa |
| Kanban pause/resume available | No docs claim this | Absent from CLI/source | **Confirmed absent** | t_ef94f514 |
| Attachment max is 25MB | Agent tool schema | MCP connector default 10MB | **Agent=25MB, MCP=10MB** | t_2499ad0a |

**Date of evidence collection:** 2026-08-19
**All evidence from Hermes v0.20.2 local inspection; no public docs consulted as authoritative source.**

---

## 15. Documentation Information Architecture Proposal

Based on the evidence inventory, the following IA is recommended for the V4 documentation set:

### Supersede (Replace Entirely)
| Current Doc | Reason | Replaced By |
|-------------|--------|-------------|
| Advanced Research baseline (sections 13, 14) | Outdated snapshot; contradicts current runtime on kanban CLI, profiles, skills | This SOURCE-OF-TRUTH-DRAFT + derived V4 docs |
| `docs/superpowers/specs/2026-08-16-hermes-chatgpt-mcp-design.md` | Pre-V4 design; references stale assumptions | V4 design doc (new) |
| `docs/superpowers/plans/2026-08-16-hermes-chatgpt-mcp.md` | Pre-investigation plan | V4 implementation plan (new) |
| Profile guide claims (`hermes profile` help, `*` marker) | Runtime diverges | Updated profile guide (new) |

### Retain (Valid, Link from V4)
| Current Doc | Validity | Action |
|-------------|----------|--------|
| `docs/DEPLOYMENT.md` | Deployment procedures; not contradicted by local evidence | Retain; link from V4 deployment section |
| `docs/SECURITY.md` | Security model; not contradicted | Retain; link from V4 security section |
| `docs/REVIEW.md` | Review process; aligns with sdlc-review force-load | Retain; link from V4 review section |
| `docs/architecture/HERMES-INTEGRATION.md` | Architecture overview; high-level valid | Retain; link from V4 architecture section |
| `docs/evidence/MULTIBOARD-GLOBAL-READ-ONE-BOARD-WRITE-2026-08-16.md` | Verified multiboard behavior | Retain as evidence artifact |
| `docs/evidence/OAUTH-CREATE-SCOPE-DIAGNOSIS-2026-08-16.md` | OAuth diagnosis; independent of this inventory | Retain as evidence artifact |

### New V4 Documents to Author
| Document | Purpose | Primary Evidence Sources |
|----------|---------|--------------------------|
| `V4-ARCHITECTURE.md` | System architecture: gateway, dispatcher, workers, runs, build | t_ad6925aa, t_ef94f514 |
| `V4-PROFILES.md` | Authoritative profile registry with spawnability, toolsets, models | t_c2257b50, t_2d568471 |
| `V4-SKILLS.md` | Skill system: origins, force-load, resolution, CLI limitations | t_2d78d03f, t_2d568471 |
| `V4-CLI-REFERENCE.md` | Complete command registry with operational status (exercised vs registered) | t_59a2a2f5, t_2d568471 |
| `V4-NATIVE-TOOLS.md` | Tool registry: 87 tools, origins, availability, risk, MCP exposure | t_5caf4595, t_2d568471 |
| `V4-KANBAN-CONTRACT.md` | Board schema, workspace/branch, pause/resume, dispatch controls | t_ef94f514, t_2d568471 |
| `V4-ATTACHMENTS.md` | 4-surface contract, MCP gap, V4 upload shape | t_2499ad0a, t_2d568471 |
| `V4-MCP-TOOLS.md` | MCP connector tool contracts, response shapes, gaps | t_2d568471, t_5caf4595, t_2499ad0a |
| `V4-RELEASE-CHECKLIST.md` | P0/P1 blockers, gate criteria, verification steps | t_2d568471 |

---

## 16. Stale-Docs Inventory

| Document | Staleness Type | Specific Issues |
|----------|----------------|-----------------|
| Advanced Research baseline (sections 13, 14) | **Version drift** | Claims kanban CLI absent; claims 13 profiles (excludes default); claims sdlc-review crash unresolved |
| `docs/superpowers/specs/2026-08-16-hermes-chatgpt-mcp-design.md` | **Pre-investigation** | Design based on stale assumptions; references Kanban_Beta as backend classification |
| `docs/superpowers/plans/2026-08-16-hermes-chatgpt-mcp.md` | **Superseded** | Plan for work already completed by local investigations |
| Profile guide (`website/docs/reference/profile-commands.md`) | **Runtime divergence** | `hermes profile` bare = help (doc) vs status (runtime); `*` marker (doc) vs `◆` (runtime) |
| Profile guide (`website/docs/user-guide/profiles.md`) | **Toolset mismatch** | `hermes tools` configures profile but legacy `toolsets:` vs `platform_toolsets.cli` produces different surface |
| Skills docs (implicit) | **CLI limitation undocumented** | `hermes skills inspect` documented as previewing metadata but hub-only; builtin/local skills falsely reported missing |

---

## 17. Registration ≠ Operational PASS — Canonical Statement

**This principle is established by the synthesis and must govern all V4 tool contracts:**

> **Command registration in `--help` output proves the command exists in the CLI parser. It does NOT prove operational PASS for any leaf subcommand. Actual leaf behavior is only proven where a real safe read call or prior board evidence exists.**

**Applied classifications:**
- **Exercised (proven):** `list`, `show`, `runs`, `diagnostics`, `assignees`, `boards`, `stats`, `context`, `log`
- **Registered only (unverified leaf behavior):** `attach`, `attachments`, `comment`, `complete`, `heartbeat`, `dispatch`, and all other kanban subcommands not listed above, plus top-level commands not exercised beyond safe read/status paths
- **MCP implication:** V4 tool contracts must distinguish `registry_presence: true` from `operational_availability: "NOT_PROVEN"` in response shapes (per t_5caf4595 recommended shape)

---

## 18. Appendices

### A. Complete Classification Reference (Machine-Readable)
See `synthesis-metadata.json` attached to t_2d568471 for the full classification object.

### B. Evidence Artifact Paths (Durable Board Attachments)
```
/home/ubuntu/.hermes/kanban/boards/hermes-chatgpt-mcp/attachments/t_2d568471/V4-LOCAL-SYNTHESIS-REPORT_1.md
/home/ubuntu/.hermes/kanban/boards/hermes-chatgpt-mcp/attachments/t_2d568471/synthesis-metadata.json
/home/ubuntu/.hermes/kanban/boards/hermes-chatgpt-mcp/attachments/t_c2257b50/V4-LOCAL-PROFILES-INVESTIGATION.md
/home/ubuntu/.hermes/kanban/boards/hermes-chatgpt-mcp/attachments/t_c2257b50/profile-evidence.json
/home/ubuntu/.hermes/kanban/boards/hermes-chatgpt-mcp/attachments/t_2d78d03f/V4-LOCAL-SKILLS-INVESTIGATION_1.md
/home/ubuntu/.hermes/kanban/boards/hermes-chatgpt-mcp/attachments/t_59a2a2f5/findings.txt
/home/ubuntu/.hermes/kanban/boards/hermes-chatgpt-mcp/attachments/t_ef94f514/V4-LOCAL-CONFIG-report.md
/home/ubuntu/.hermes/kanban/boards/hermes-chatgpt-mcp/attachments/t_ad6925aa/V4-LOCAL-RUNTIME-report.md
/home/ubuntu/.hermes/kanban/boards/hermes-chatgpt-mcp/attachments/t_2499ad0a/REPORT-t_2499ad0a-attachments-contract.md
/home/ubuntu/.hermes/kanban/boards/hermes-chatgpt-mcp/attachments/t_5caf4595/native_tools_inventory.json
/home/ubuntu/.hermes/kanban/boards/hermes-chatgpt-mcp/attachments/t_5caf4595/native_tools_inventory_report.md
```

### C. Source Code References (for verification)
| Component | Key Files |
|-----------|-----------|
| Dispatcher | `gateway/kanban_watchers.py:1182-1757`, `hermes_cli/kanban_db.py:9808-10418` |
| Worker spawn | `hermes_cli/kanban_db.py:10503-10921` |
| Kanban CLI registry | `hermes_cli/commands.py:336-344`, `hermes_cli/commands.py:399-497` |
| Gateway slash dispatch | `gateway/run.py:15774-15780`, `gateway/slash_commands.py:459-574` |
| Dashboard API | `plugins/kanban/dashboard/plugin_api.py:1541-1751` |
| Native API-server | `gateway/platforms/api_server.py:2053-2105`, `:7267-...` |
| Schema | `hermes_cli/kanban_db.py:SCHEMA_SQL` |
| Config defaults | `hermes_cli/config_defaults.py` |
| Tool registry | `tools/registry.py`, `toolsets.py`, `model_tools.py` |
| Profile resolution | `hermes_cli/profiles.py`, `hermes_cli/tools_config.py` |
| Skill loading | `agent/skill_commands.py`, `tools/skills_tool.py`, `agent/skill_utils.py` |
| MCP connector (beta) | `hermes_chatgpt_mcp/schemas.py`, `hermes_chatgpt_mcp/command.py` |

---

**END OF SOURCE-OF-TRUTH-DRAFT**

*This document is a DRAFT ARTIFACT ONLY. Do not edit the repository yet. All assertions marked with source task IDs. No silent corrections of evidence. No code changes, no public research, no repo writes.*