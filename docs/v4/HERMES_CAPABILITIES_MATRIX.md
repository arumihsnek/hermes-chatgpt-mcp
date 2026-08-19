# Hermes Native Capabilities Matrix

**Status:** CANONICAL V4 DESIGN / CURRENT EVIDENCE
**Last reconciled:** 2026-08-19
**Documentation base:** 9900c10 (local ref only; deployed SHA NOT_PROVEN)
**See also:** [README.md](README.md) | [CURRENT_STATE.md](CURRENT_STATE.md) | [EVIDENCE_AND_OPEN_QUESTIONS.md](EVIDENCE_AND_OPEN_QUESTIONS.md)
**Derived from:** t_4ce4ba8f (`HERMES-NATIVE-CAPABILITIES-MATRIX-DRAFT.md`)
**Critical caveat:** Native registration != behavioral PASS. The final catalog governs MCP status.

---

## Product Status Vocabulary## Product Status Vocabulary## Product Status Vocabulary
| Code | Meaning |
|------|---------|
| **DISPONIBLE Y VALIDADO** | Feature present, behavior confirmed via safe read call or board evidence |
| **DISPONIBLE CON ERRORES/INCONSISTENCIAS** | Feature present but known defect/inconsistency documented |
| **EN TRABAJO** | Actively being implemented in current development cycle |
| **PLANIFICADO V4** | Designed for V4 release, not yet implemented |
| **PLANIFICADO V4.x** | Designed for post-V4 minor release |
| **PLANIFICADO V5** | Designed for next major version |
| **NO DISPONIBLE/NO PLANIFICADO** | Not present, no active plan |
| **NOT_PROVEN** | Registered/exists but behavior not exercised; only registration evidence |
| **UNSAFE_TO_TEST** | Would mutate production state (dispatch, kill, slash invocation) |
| **NO APLICA AL MCP** | Not relevant to MCP connector surface |

## Priority Codes
| Code | Meaning |
|------|---------|
| **P0** | Blocking for V4 release |
| **P1** | Important for V4, non-blocking |
| **P2** | Nice to have for V4 |
| **P3** | Deferred |
| **DO_NOT_EXPOSE** | Must not be exposed via MCP/connector |

---

## Section 1: Top-Level Hermes CLI (74 registered commands)

| # | Command | Category | Description | Status | Known Issues | Priority | Target | Evidence |
|---|---------|----------|-------------|--------|--------------|----------|--------|----------|
| 1 | `chat` | Core | Interactive/conversational agent session | DISPONIBLE Y VALIDADO | — | P0 | V4 | t_59a2a2f5 |
| 2 | `model` | Core | Model selection and provider management | DISPONIBLE Y VALIDADO | — | P1 | V4 | t_59a2a2f5 |
| 3 | `moa` | Core | Mixture-of-agents orchestration | NOT_PROVEN | — | P2 | V4.x | t_59a2a2f5 |
| 4 | `fallback` | Core | Fallback model configuration | NOT_PROVEN | — | P2 | V4.x | t_59a2a2f5 |
| 5 | `secrets` | Security | Manage API keys and credentials | DISPONIBLE Y VALIDADO | — | P1 | V4 | t_59a2a2f5 |
| 6 | `egress` | Security | Network egress control | NOT_PROVEN | — | P2 | V4.x | t_59a2a2f5 |
| 7 | `migrate` | Migration | Database/state migration | NOT_PROVEN | — | P2 | V4.x | t_59a2a2f5 |
| 8 | `gateway` | Infrastructure | Gateway lifecycle (start/stop/status/list) | DISPONIBLE Y VALIDADO | — | P0 | V4 | t_59a2a2f5, t_ad6925aa |
| 9 | `proxy` | Infrastructure | HTTP proxy server | NOT_PROVEN | — | P3 | V5 | t_59a2a2f5 |
| 10 | `lsp` | Infrastructure | Language server protocol | NOT_PROVEN | — | P3 | V5 | t_59a2a2f5 |
| 11 | `setup` | Configuration | Interactive setup wizard | NOT_PROVEN | — | P2 | V4.x | t_59a2a2f5 |
| 12 | `whatsapp` | Messaging | WhatsApp integration | NOT_PROVEN | — | P2 | V4.x | t_59a2a2f5 |
| 13 | `whatsapp-cloud` | Messaging | WhatsApp Cloud API integration | NOT_PROVEN | — | P2 | V4.x | t_59a2a2f5 |
| 14 | `slack` | Messaging | Slack integration | NOT_PROVEN | — | P2 | V4.x | t_59a2a2f5 |
| 15 | `send` | Messaging | Send messages | NOT_PROVEN | — | P2 | V4.x | t_59a2a2f5 |
| 16 | `login` | Auth | Authentication login | NOT_PROVEN | — | P2 | V4.x | t_59a2a2f5 |
| 17 | `logout` | Auth | Authentication logout | NOT_PROVEN | — | P2 | V4.x | t_59a2a2f5 |
| 18 | `auth` | Auth | Authentication management | NOT_PROVEN | — | P2 | V4.x | t_59a2a2f5 |
| 19 | `status` | Observability | Global/current runtime status | DISPONIBLE Y VALIDADO | — | P0 | V4 | t_59a2a2f5, t_ad6925aa |
| 20 | `pause` | Control | Global emergency stop (ESTOP sentinel) | DISPONIBLE Y VALIDADO | No board-local pause | P1 | V4 | t_59a2a2f5, t_ef94f514 |
| 21 | `resume` | Control | Remove ESTOP sentinel | DISPONIBLE Y VALIDADO | Paired with pause | P1 | V4 | t_59a2a2f5, t_ef94f514 |
| 22 | `cron` | Scheduling | Cron job management | NOT_PROVEN | — | P2 | V4.x | t_59a2a2f5 |
| 23 | `sync` | Sync | Session sync | NOT_PROVEN | — | P2 | V4.x | t_59a2a2f5 |
| 24 | `webhook` | Integration | Webhook management | NOT_PROVEN | — | P2 | V4.x | t_59a2a2f5 |
| 25 | `portal` | Integration | Portal server | NOT_PROVEN | — | P3 | V5 | t_59a2a2f5 |
| 26 | `kanban` | Kanban | Full Kanban board control-plane | DISPONIBLE Y VALIDADO | See dedicated CLI matrix | P0 | V4 | t_59a2a2f5 |
| 27 | `project` | Project | Project workspace management | NOT_PROVEN | — | P2 | V4.x | t_59a2a2f5 |
| 28 | `hooks` | Lifecycle | Lifecycle hooks management | NOT_PROVEN | — | P2 | V4.x | t_59a2a2f5 |
| 29 | `doctor` | Diagnostics | Health check/diagnostics | NOT_PROVEN | — | P1 | V4 | t_59a2a2f5 |
| 30 | `verify` | Verification | System verification | NOT_PROVEN | — | P2 | V4.x | t_59a2a2f5 |
| 31 | `security` | Security | Security audit/scan | NOT_PROVEN | — | P2 | V4.x | t_59a2a2f5 |
| 32 | `approvals` | Governance | Approval management | NOT_PROVEN | — | P2 | V4.x | t_59a2a2f5 |
| 33 | `dump` | Debug | Dump state/registry | NOT_PROVEN | — | P2 | V4.x | t_59a2a2f5 |
| 34 | `debug` | Debug | Debug mode/info | NOT_PROVEN | — | P2 | V4.x | t_59a2a2f5 |
| 35 | `backup` | Ops | Backup state | NOT_PROVEN | — | P2 | V4.x | t_59a2a2f5 |
| 36 | `checkpoints` | Ops | Checkpoint management | NOT_PROVEN | — | P2 | V4.x | t_59a2a2f5 |
| 37 | `import` | Import | Import external state | NOT_PROVEN | — | P2 | V4.x | t_59a2a2f5 |
| 38 | `import-agent` | Import | Import agent profile | NOT_PROVEN | — | P2 | V4.x | t_59a2a2f5 |
| 39 | `config` | Configuration | Config show/set/get | DISPONIBLE Y VALIDADO | — | P0 | V4 | t_59a2a2f5, t_ef94f514 |
| 40 | `skin` | UI | Theme/skin management | NOT_PROVEN | — | P3 | V5 | t_59a2a2f5 |
| 41 | `console` | UI | Console mode | NOT_PROVEN | — | P3 | V5 | t_59a2a2f5 |
| 42 | `pairing` | Integration | Device pairing | NOT_PROVEN | — | P3 | V5 | t_59a2a2f5 |
| 43 | `skills` | Skills | Skill management (list/inspect/enable) | DISPONIBLE Y VALIDADO | `inspect` hub-only (not builtin/local) | P0 | V4 | t_59a2a2f5, t_2d78d03f |
| 44 | `bundles` | Skills | Skill bundle management | NOT_PROVEN | — | P2 | V4.x | t_59a2a2f5 |
| 45 | `plugins` | Integration | Plugin management | NOT_PROVEN | — | P2 | V4.x | t_59a2a2f5 |
| 46 | `curator` | Skills | Skill curation | NOT_PROVEN | — | P2 | V4.x | t_59a2a2f5 |
| 47 | `pets` | Fun | Pet companion | NOT_PROVEN | — | P3 | V5 | t_59a2a2f5 |
| 48 | `journey` | Learning | Learning journey | NOT_PROVEN | — | P3 | V5 | t_59a2a2f5 |
| 49 | `learning` | Learning | Learning mode | NOT_PROVEN | — | P3 | V5 | t_59a2a2f5 |
| 50 | `memory-graph` | Memory | Graph memory queries | NOT_PROVEN | — | P2 | V4.x | t_59a2a2f5 |
| 51 | `memory` | Memory | Persistent memory management | NOT_PROVEN | — | P1 | V4 | t_59a2a2f5 |
| 52 | `tools` | Tools | Tool management/summary | DISPONIBLE Y VALIDADO | — | P0 | V4 | t_59a2a2f5 |
| 53 | `computer-use` | Agent | Computer use control | NOT_PROVEN | — | P2 | V4.x | t_59a2a2f5 |
| 54 | `mcp` | Integration | MCP server management | NOT_PROVEN | — | P0 | V4 | t_59a2a2f5 |
| 55 | `sessions` | Session | Session management | NOT_PROVEN | — | P1 | V4 | t_59a2a2f5 |
| 56 | `insights` | Observability | Usage insights | NOT_PROVEN | — | P2 | V4.x | t_59a2a2f5 |
| 57 | `monitoring` | Observability | Monitoring | NOT_PROVEN | — | P2 | V4.x | t_59a2a2f5 |
| 58 | `claw` | Integration | Claw integration | NOT_PROVEN | — | P3 | V5 | t_59a2a2f5 |
| 59 | `version` | Info | Version info | DISPONIBLE Y VALIDADO | — | P0 | V4 | t_59a2a2f5 |
| 60 | `update` | Maintenance | Update Hermes | NOT_PROVEN | — | P1 | V4 | t_59a2a2f5 |
| 61 | `uninstall` | Maintenance | Uninstall Hermes | NOT_PROVEN | — | P2 | V4.x | t_59a2a2f5 |
| 62 | `acp` | Agent | Agent Control Protocol | NOT_PROVEN | — | P1 | V4 | t_59a2a2f5 |
| 63 | `profile` | Configuration | Profile management (list/show/set) | DISPONIBLE Y VALIDADO | Docs say `*`; runtime uses `◆` marker | P0 | V4 | t_59a2a2f5, t_c2257b50 |
| 64 | `completion` | UI | Tab completion setup | NOT_PROVEN | — | P3 | V5 | t_59a2a2f5 |
| 65 | `dashboard` | UI | Web dashboard | NOT_PROVEN | — | P1 | V4 | t_59a2a2f5 |
| 66 | `serve` | Server | HTTP server mode | NOT_PROVEN | — | P2 | V4.x | t_59a2a2f5 |
| 67 | `desktop` | UI | Desktop app | NOT_PROVEN | — | P3 | V5 | t_59a2a2f5 |
| 68 | `gui` | UI | GUI mode | NOT_PROVEN | — | P3 | V5 | t_59a2a2f5 |
| 69 | `logs` | Observability | Log viewing | NOT_PROVEN | — | P2 | V4.x | t_59a2a2f5 |
| 70 | `prompt-size` | Debug | Prompt size analysis | NOT_PROVEN | — | P3 | V5 | t_59a2a2f5 |

---

## Section 2: Native Tool Registry

### Registry Architecture Summary
| Metric | Value | Source |
|--------|-------|--------|
| Total unique leaf tools | 87 | t_5caf4595 |
| Static toolsets (toolsets.py) | 59 | Source inspection |
| Registry toolsets (from entries) | 31 | Registry introspection |
| Origin: BUILTIN | 87 | All current tools |
| Origin: PLUGIN | 0 | No active plugins |
| Origin: MCP | 0 | No MCP servers connected |
| Origin: DYNAMIC | 0 | context_engine empty |
| Risk: READ_ONLY | 39 | Search, view, list, analyze |
| Risk: MUTATING | 48 | Write, create, execute, send |
| Availability: always_available | 14 | No check_fn |
| Availability: check_fn_available | 69 | check_fn returns True |
| Availability: requires_env | 4 | EXA/TAVILY/FIRECRAWL keys, DISCORD_BOT_TOKEN |

### Tool Registry by Toolset

| Toolset | Tool Count | Status | Known Issues | Priority | Target | Evidence |
|---------|-----------|--------|--------------|----------|--------|----------|
| `kanban` | 14 | DISPONIBLE Y VALIDADO | `kanban_list` and `kanban_unblock` require orchestrator mode | P0 | V4 | t_5caf4595 |
| `terminal` | 2 | DISPONIBLE Y VALIDADO | — | P0 | V4 | t_5caf4595 |
| `file` | 4 | DISPONIBLE Y VALIDADO | — | P0 | V4 | t_5caf4595 |
| `skills` | 3 | DISPONIBLE Y VALIDADO | `skill_manage` (mutating), `skill_view`, `skills_list` | P0 | V4 | t_5caf4595, t_2d78d03f |
| `web` | 2 | DISPONIBLE Y VALIDADO | `requires_env`: EXA/TAVILY/FIRECRAWL API keys | P1 | V4 | t_5caf4595 |
| `browser` | 13 | DISPONIBLE Y VALIDADO | `check_browser_requirements` gate | P2 | V4.x | t_5caf4595 |
| `browser-cdp` | 2 | NOT_PROVEN | CDP-specific check_fn | P2 | V4.x | t_5caf4595 |
| `browser-use` | 1 | NOT_PROVEN | browser-use CLI mode | P2 | V4.x | t_5caf4595 |
| `code_execution` | 1 | NOT_PROVEN | sandbox requirements | P2 | V4.x | t_5caf4595 |
| `delegation` | 1 | NOT_PROVEN | subagent delegation | P2 | V4.x | t_5caf4595 |
| `todo` | 1 | NOT_PROVEN | task planning | P2 | V4.x | t_5caf4595 |
| `memory` | 1 | NOT_PROVEN | persistent memory | P2 | V4.x | t_5caf4595 |
| `session_search` | 1 | NOT_PROVEN | session history | P2 | V4.x | t_5caf4595 |
| `clarify` | 1 | NOT_PROVEN | user clarification | P2 | V4.x | t_5caf4595 |
| `cronjob` | 1 | NOT_PROVEN | cron management | P2 | V4.x | t_5caf4595 |
| `homeassistant` | 4 | NOT_PROVEN | HA availability check | P3 | V5 | t_5caf4595 |
| `computer_use` | 1 | NOT_PROVEN | platform control | P3 | V5 | t_5caf4595 |
| `image_gen` | 1 | NOT_PROVEN | image generation | P2 | V4.x | t_5caf4595 |
| `bfl` | 6 | NOT_PROVEN | BFL FLUX 3 video | P3 | V5 | t_5caf4595 |
| `tts` | 1 | NOT_PROVEN | text-to-speech | P3 | V5 | t_5caf4595 |
| `vision` | 1 | NOT_PROVEN | vision analysis | P1 | V4 | t_5caf4595 |
| `discord` | 1 | NOT_PROVEN | `requires_env`: DISCORD_BOT_TOKEN | P2 | V4.x | t_5caf4595 |
| `discord_admin` | 1 | NOT_PROVEN | `requires_env`: DISCORD_BOT_TOKEN | P2 | V4.x | t_5caf4595 |
| `desktop_ui` | 8 | NOT_PROVEN | GUI-only tools (close_terminal, focus_pane, etc.) | P3 | V5 | t_5caf4595 |
| `project` | 3 | NOT_PROVEN | GUI-only project tools | P2 | V4.x | t_5caf4595 |
| `hermes-yuanbao` | 5 | NOT_PROVEN | Yuanbao-specific | P3 | V5 | t_5caf4595 |
| `feishu_doc` | 1 | NOT_PROVEN | Feishu document access | P3 | V5 | t_5caf4595 |
| `feishu_drive` | 4 | NOT_PROVEN | Feishu drive management | P3 | V5 | t_5caf4595 |
| `xe_*` tools | ~15 | NOT_PROVEN | Feishu/enterprise tools | P3 | V5 | t_5caf4595 |

### Core Toolset Composition (hermes-cli, 54 unique tools)
The `hermes-cli` toolset (default for CLI workers) includes: web (2), terminal (2), file (4), vision (1), image_gen (1), bfl (6), skills (3), browser (13), tts (1), todo (1), memory (1), session_search (1), clarify (1), code_execution (1), delegation (1), cronjob (1), homeassistant (4), kanban (14), computer_use (1).

---

## Section 3: Profiles

| # | Profile | Description | Model/Provider | Runtime Skills | Effective CLI Toolsets | Disponible | Spawnable | Evidence |
|---|---------|-------------|----------------|----------------|----------------------|------------|-----------|----------|
| 1 | `default` | Full-stack software development and multi-agent coordination | mimo-v2.5 / opencode-go | 358 | 18 (bfl, browser, clarify, code_execution, context_engine, cronjob, delegation, file, kanban, memory, session_search, skills, terminal, todo, tts, video, vision, web) | YES | INFERRED_ONLY | t_c2257b50 |
| 2 | `coder` | Develops and debugs software using TDD and systematic investigation | poolside/laguna-xs-2.1 / nvidia | 10 | 18 (inherits hermes-cli composite) | YES | INFERRED_ONLY | t_c2257b50 |
| 3 | `github-steward` | Bounded, provenance-first GitHub operations | nvidia/nemotron-3-super-120b-a12b / nvidia | 79 | 18 (inherits hermes-cli composite) | YES | INFERRED_ONLY | t_c2257b50 |
| 4 | `investigator` | Investigates technical questions through systematic debugging | nvidia/nemotron-3-ultra-550b-a55b / nvidia | 95 | 18 (inherits hermes-cli composite) | YES | OBSERVED | t_c2257b50 |
| 5 | `kahuku` | Surface Go 3 hardware-dependent remote operations | mimo-v2.5 / opencode-go | 5 | 15 | YES | INFERRED_ONLY | t_c2257b50 |
| 6 | `kahuku-candidate` | Candidate Surface Go 3 hardware/runtime profile | mimo-v2.5 / opencode-go | 91 | 4 (bfl, file, kanban, terminal) | YES | INFERRED_ONLY | t_c2257b50 |
| 7 | `kanban-coordinator` | Kanban control-plane routing, DAGs, outcomes | nvidia/nemotron-3-ultra-550b-a55b / nvidia | 92 | 18 (inherits hermes-cli composite) | YES | INFERRED_ONLY | t_c2257b50 |
| 8 | `operator` | Android ADB/bridge execution, import/execute, state capture | nvidia/nemotron-3-super-120b-a12b / nvidia | 9 | 18 (inherits hermes-cli composite) | YES | INFERRED_ONLY | t_c2257b50 |
| 9 | `profile-architect` | Designs and improves AI-agent profiles, prompts, skills | z-ai/glm-5.2 / nvidia | 53 | 16 | YES | INFERRED_ONLY | t_c2257b50 |
| 10 | `researcher` | Text/web-first source-grounded technical research | nvidia/nemotron-3-nano-30b-a3b / nvidia | 7 | 18 (inherits hermes-cli composite) | YES | INFERRED_ONLY | t_c2257b50 |
| 11 | `reviewer` | Adversarial evidence/contract/regression/security review | z-ai/glm-5.2 / nvidia | 14 | 18 (inherits hermes-cli composite) | YES | INFERRED_ONLY | t_c2257b50 |
| 12 | `software-architect` | Tasker XML/IR architecture, schemas/catalogs, roundtrip | z-ai/glm-5.2 / nvidia | 9 | 5 (bfl, file, kanban, skills, terminal) | YES | INFERRED_ONLY | t_c2257b50 |
| 13 | `wilson` | Personal secretary and Obsidian second-brain management | nvidia/nemotron-3-nano-30b-a3b / opencode-go | 91 | 15 | YES | INFERRED_ONLY | t_c2257b50 |
| 14 | `worker` | Low-risk closed mechanical execution | nvidia/nemotron-3-super-120b-a12b / nvidia | 3 | 18 (inherits hermes-cli composite) | YES | INFERRED_ONLY | t_c2257b50 |

### Spawnability Note
- **OBSERVED end-to-end spawn:** `investigator` (t_c2257b50, t_ef94f514, t_ad6925aa), `profile-architect` (t_2d78d03f), `operator` (t_59a2a2f5), `software-architect` (t_5caf4595, t_2499ad0a, t_2d568471, t_4ce4ba8f)
- **INFERRED_ONLY:** All other 10 profiles — dispatcher-eligible by `profile_exists()` predicate only

### Toolset/Runtime Mismatch
Profiles without `platform_toolsets.cli` (e.g., `coder`, `investigator`, `researcher`, `reviewer`, `worker`) inherit broad `hermes-cli` composite (18 tools) despite narrow top-level toolset declarations. Profiles with explicit `platform_toolsets.cli` (`software-architect`=5, `kahuku-candidate`=4) report narrow surfaces. `profile.yaml` capabilities/refuses are declarative and NOT enforced by Hermes core.

---

## Section 4: Skills

| # | Skill | Origin | Description | Profiles | Status | Known Issues | Priority | Evidence |
|---|-------|--------|-------------|----------|--------|--------------|----------|----------|
| 1 | `sdlc-review` | builtin | Review Kanban handoffs | All (force-loaded) | DISPONIBLE Y VALIDADO | Force-loaded at dispatch; not in reviewer profile dir | P0 | t_2d78d03f |
| 2 | `hermes-agent` | builtin | Platform operations, config | default, profile-architect | DISPONIBLE Y VALIDADO | — | P0 | t_2d78d03f |
| 3 | `profile-craft` | local | Profile authoring | profile-architect | DISPONIBLE Y VALIDADO | — | P1 | t_2d78d03f |
| 4 | `prompt-engineering` | local | Prompt authoring | profile-architect | DISPONIBLE Y VALIDADO | — | P1 | t_2d78d03f |
| 5 | `kanban-complete-guard` | local | Prevent premature completion | Multiple | DISPONIBLE Y VALIDADO | — | P1 | t_2d78d03f |
| 6 | `hermes-dojo` | local | Self-improvement system | Multiple | DISPONIBLE Y VALIDADO | — | P2 | t_2d78d03f |
| 7 | `skill-gap-diagnostics` | local | Skill gap tracking | profile-architect | DISPONIBLE Y VALIDADO | — | P2 | t_2d78d03f |
| 8 | `hermes-profile-maintenance` | local | Profile audit | Multiple | DISPONIBLE Y VALIDADO | — | P2 | t_2d78d03f |
| 9 | `lifecycle-unacknowledged-exit` | local | Lifecycle management | Multiple | DISPONIBLE Y VALIDADO | — | P2 | t_2d78d03f |
| 10 | `health-confidence-scoring` | local | Statistical health scoring | profile-architect | DISPONIBLE Y VALIDADO | — | P2 | t_2d78d03f |
| 11 | `blocked-criteria-refinement` | local | Task dependency management | Multiple | DISPONIBLE Y VALIDADO | — | P1 | t_2d78d03f |
| 12 | `wilson-proposals-cycle-fix` | local | Board management | Multiple | DISPONIBLE Y VALIDADO | — | P2 | t_2d78d03f |
| 13 | `hermes-themes` | local | Theme authoring | profile-architect | DISPONIBLE Y VALIDADO | — | P3 | t_2d78d03f |
| 14 | `hermes-desktop-plugins` | local | Desktop plugin authoring | profile-architect | DISPONIBLE Y VALIDADO | — | P3 | t_2d78d03f |
| 15 | `tui-widgets` | local | TUI widget authoring | profile-architect | DISPONIBLE Y VALIDADO | — | P3 | t_2d78d03f |
| 16 | `merge-reconciler` | builtin | Merge conflict resolution | Multiple | DISPONIBLE Y VALIDADO | — | P2 | t_2d78d03f |
| 17 | `systematic-debugging` | builtin | 4-phase debugging | coder, profile-architect | DISPONIBLE Y VALIDADO | — | P1 | t_2d78d03f |
| 18 | `test-driven-development` | builtin | TDD workflow | coder | DISPONIBLE Y VALIDADO | — | P1 | t_2d78d03f |
| 19 | `github-pr-workflow` | builtin | PR lifecycle | Multiple | DISPONIBLE Y VALIDADO | — | P1 | t_2d78d03f |
| 20 | `github-code-review` | builtin | Code review | reviewer | DISPONIBLE Y VALIDADO | — | P1 | t_2d78d03f |
| 21 | `requesting-code-review` | builtin | Pre-merge review | reviewer | DISPONIBLE Y VALIDADO | — | P1 | t_2d78d03f |
| 22-53 | *(31 more builtin skills)* | builtin | Various capabilities | Multiple | DISPONIBLE Y VALIDADO | — | P2-P3 | t_2d78d03f |

**Total enabled on default/profile-architect:** 53 (39 builtin + 14 local + 0 hub)
**Skill inspection caveat:** `hermes skills inspect` cannot resolve builtin/local skills (hub-only search). Use `hermes skills list` or `skill_view()` instead.

---

## Section 5: Gateway/Dispatcher/Workers/Runtime

### Build Provenance
| Field | Value | Evidence |
|-------|-------|----------|
| Hermes version | 0.20.2 (2026.8.16) | `hermes version` |
| Upstream SHA | b7bed241 | `hermes version` |
| Local HEAD | 39cfd1ab41 (+2 carried commits) | `git log -1 --oneline` |
| Install directory | /home/ubuntu/hermes-agent | `hermes version` |
| Install method | git | `hermes version` |
| Python | 3.11.15 | `hermes version` |
| Executable | /home/ubuntu/.local/bin/hermes | `which hermes` |

### Gateway
| Component | Status | Notes | Evidence |
|-----------|--------|-------|----------|
| Default profile gateway | RUNNING (PID 3968293) | Only running profile observed | t_ad6925aa |
| Investigator profile gateway | INACTIVE (systemd unit dead) | Not running | t_ad6925aa |
| Connector label `Kanban_Beta` | STALE NAMESPACE | Deployment is STABLE per controller correction | t_ad6925aa |
| API-server port conflict | WARNING on port 8642 | — | t_ad6925aa |

### Dispatcher
| Property | Value | Evidence |
|----------|-------|----------|
| Embedded in gateway | `kanban.dispatch_in_gateway=true` (default) | t_ef94f514 |
| Machine-global lock | `<kanban_home>/kanban/.dispatcher.lock` | t_ad6925aa |
| Board-scoped dispatch lock | `dispatch_once()` | t_ad6925aa |
| Tick interval | 60 seconds (default) | t_ef94f514 |
| Tick sequence | reap zombies → check ESTOP → auto-decompose → enumerate boards → dispatch per-board | t_ad6925aa |
| Auto-decompose re-read | Per-tick (live safety toggle) | t_ef94f514 |
| Standalone daemon | DEPRECATED | t_59a2a2f5, t_ad6925aa |

### Worker Spawn
| Property | Value | Evidence |
|----------|-------|----------|
| Function | `_default_spawn()` at `kanban_db.py:10709` | t_ad6925aa |
| Prompt | `work kanban task <task_id>` | t_ad6925aa |
| Child env | Profile-scoped HERMES_HOME, HERMES_PROFILE, HERMES_KANBAN_DB/BOARD/WORKSPACES_ROOT, HERMES_SESSION_SOURCE=kanban | t_ad6925aa |
| argv | `hermes -p <assignee> --cli --accept-hooks [--skills ...] chat -q "work kanban task <task_id>"` | t_ad6925aa |

### Heartbeat/Stale/Crash/Timeout
| Property | Value | Evidence |
|----------|-------|----------|
| Default claim TTL | 15 minutes | t_ad6925aa |
| Heartbeat-stale threshold | 1 hour (PID alive, no heartbeat) | t_ad6925aa |
| Crash grace | 30 seconds after spawn | t_ad6925aa |
| Dispatch stale timeout | 4 hours | t_ef94f514 |
| Failure limit | 2 consecutive → auto-block | t_ef94f514 |
| Rate-limit (exit 75) | Treated as temporary, not failure | t_ad6925aa |

### Live HTTP Reachability
| Surface | Status | Evidence |
|---------|--------|----------|
| Dashboard plugin API enablement | STILL_NOT_PROVEN | t_ad6925aa |
| Native API-server listener reachability/auth | STILL_NOT_PROVEN | t_ad6925aa |
| Live `/kanban` connector delivery/ACL | UNSAFE_TO_TEST | t_ad6925aa |

---

## Section 6: MCP Connector Gap List

### Critical Gaps for V4 Tool Contract
| Gap | Severity | Current State | Recommendation | Evidence |
|-----|----------|---------------|----------------|----------|
| MCP connector `attach(local_path)` is SERVER_LOCAL_BOUND | BLOCKING | Remote clients cannot provide server-local paths | Add `content_base64` to MCP connector's AttachInput schema | t_2499ad0a |
| Size limit mismatch: agent=25MB, MCP connector=10MB | HIGH | Divergent caps across surfaces | Unify to single cap or document divergence | t_2499ad0a |
| Deployed connector SHA unknown | MEDIUM | Local master stale, live schema shows attach tool present | Pin deployed connector version before V4 release | t_2499ad0a |
| `hermes skills inspect` cannot resolve builtin/local | MEDIUM | Hub-only search | V4 skill queries must use `skills list` or `skill_view`, not `inspect` | t_2d78d03f |
| No board-local pause/resume | LOW | Global ESTOP only | V4 documentation should clarify this is global control | t_ef94f514 |
| `profile.yaml` capabilities/refuses not enforced | LOW | No enforcement path in Hermes core | Treat as declarative routing metadata only | t_c2257b50 |
| Live HTTP auth/enablement of dashboard plugin API | UNKNOWN | No live request made | Integration test before V4 MCP tool design | t_ad6925aa |
| Temporary per-task skill injection | PARTIALLY_RESOLVED | Code path exists; resolution depends on profile | Verify per-task skill resolution semantics | t_2d78d03f |

---

## Section 7: Contradiction Ledger (Docs vs Runtime)

| Claim | Docs Source | Runtime Evidence | Verdict | Provenance |
|-------|-------------|------------------|---------|------------|
| `hermes profile` shows help | website docs:9-15 | Runtime: no action = status display | Runtime correct | t_c2257b50 |
| Profile marker is `*` | website docs:33-49 | Runtime: `◆` marker | Runtime correct | t_c2257b50 |
| `hermes tools` configures active profile | website docs:110-119 | Runtime: true at command level, but toolsets mismatch | Partially correct | t_c2257b50 |
| `hermes skills inspect` previews skill metadata | Implicit in CLI help | Runtime: hub-only search, fails for builtin/local | Runtime limited | t_2d78d03f |
| `hermes kanban daemon` is normal dispatch | CLI help exists | Runtime: marked DEPRECATED, dispatch embedded in gateway | Runtime correct | t_59a2a2f5, t_ad6925aa |
| Kanban pause/resume available | No docs claim this | Runtime: absent from CLI/source | Confirmed absent | t_ef94f514 |
| Attachment max is 25MB | Agent tool schema | MCP connector default 10MB | Agent=25MB, MCP=10MB | t_2499ad0a |

---

## P0/P1 Recommendations for V4

### V4 P0 (Blocking for Release)
| ID | Title | Reason |
|----|-------|--------|
| P0-1 | Add `content_base64` to MCP connector AttachInput | local_path-only attach is architecturally wrong for remote clients |
| P0-2 | Unify attachment size cap (25MB agent vs 10MB MCP) | Size mismatch between surfaces |
| P0-3 | Pin deployed connector SHA | Local master stale, deployed version unknown |
| P0-4 | V4 skill queries: use `skills list` or `skill_view`, never `inspect` | inspect is hub-only, fails for builtin/local |
| P0-5 | Preserve sdlc-review force-load pattern | Production-critical; dispatcher appends at dispatch time |

### V4 P1 (Important, Non-Blocking)
| ID | Title | Reason |
|----|-------|--------|
| P1-1 | Use runtime effective CLI toolsets for profile routing | Legacy toolsets field produces broader surface than expected |
| P1-2 | Represent spawnability as `dispatcher_eligible` vs `end_to_end_observed` | Only 4 profiles have observed spawn |
| P1-3 | Document global pause (ESTOP) vs board-local pause (absent) | No board-local pause exists |
| P1-4 | Distinguish Kanban dashboard API from native `/v1/runs` paths | Separate termination surfaces |
| P1-5 | Treat `profile.yaml` capabilities/refuses as advisory | No enforcement path in Hermes core |
| P1-6 | Report MCP diagnostics/dispatch failures as backend observability | BACKEND_ERROR observations not config evidence |

---

## Evidence Traceability

| Evidence Source | Task | Artifacts |
|-----------------|------|-----------|
| CLI enumeration | t_59a2a2f5 | `findings.txt` |
| Synthesis ledger | t_2d568471 | `V4-LOCAL-SYNTHESIS-REPORT_1.md`, `synthesis-metadata.json` |
| Runtime investigation | t_ad6925aa | `V4-LOCAL-RUNTIME-report.md` |
| Config investigation | t_ef94f514 | `V4-LOCAL-CONFIG-report.md` |
| Attachments contract | t_2499ad0a | `REPORT-t_2499ad0a-attachments-contract.md` |
| Skills investigation | t_2d78d03f | `V4-LOCAL-SKILLS-INVESTIGATION_1.md` |
| Profiles investigation | t_c2257b50 | `V4-LOCAL-PROFILES-INVESTIGATION.md` |
| Native tools inventory | t_5caf4595 | `native_tools_inventory.json`, `native_tools_inventory_report.md` |