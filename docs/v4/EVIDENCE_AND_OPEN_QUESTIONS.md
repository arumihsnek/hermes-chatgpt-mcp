# Evidence and Open Questions — V4 Documentation

## Integrated Evidence Sources

This documentation integrates findings from the following parent tasks:

### t_1419658e — V4 MCP Tool Catalog
- 79 tools cataloged (29 P0, 23 P1, 12 P2, 15 DO_NOT_EXPOSE)
- 11 AVAILABLE_VALIDATED, 5 AVAILABLE_INCONSISTENT, 15 PLANNED_V4, 39 NOT_PROVEN, 8 NOT_AVAILABLE
- Current scope proven: hermes:read (baseline), hermes:create (create_task), hermes:manage (add_comment, assign_task), hermes:board:create (create_board)
- 5 P0 blockers documented:
  - P0-1 (content_base64)
  - P0-2 (size cap)
  - P0-3 (connector SHA)
  - P0-4 (skill queries)
  - P0-5 (sdlc-review force-load)
- Operator corrections applied:
  - dispatch=AVAILABLE_INCONSISTENT (BACKEND_ERROR)
  - get_board=AVAILABLE_INCONSISTENT (capability readback)
  - create_board NOT called in docs session
- Exact product vocabulary enforced: 9 status codes with UTF-8 emoji literals

### t_484d4ab0 — V4 Spec/ADR Corrections
- Corrected both V4 spec drafts with proper OAuth scope vocabulary
- Replaced all `board:read`/`board:write`/`board:admin` references with current proven scopes (`hermes:read`, `hermes:create`, `hermes:manage`, `hermes:board:create`, `offline_access`)
- Added explicit CURRENT scope table and PROPOSED fine-grained V4 taxonomy with migration mapping
- Verified no improper scope references remain outside PROPOSED sections
- Artifact lifecycle issue: post_complete_workspace_changes_not_durable

### t_4ce4ba8f — V4 Documentation Matrices
- Two exhaustive draft matrices and machine-readable index produced
- Applied operator quality gate feedback:
  - Exact product status vocabulary with emoji mapping
  - Separate columns for Current Live MCP Tool / Planned V4 MCP Tool (no name invention)
  - MCP E2E validation evidence reused from prior board QA
  - Daemon marked DO_NOT_EXPOSE/NO APLICA rather than implying V4 implementation
- Findings:
  - 47 Kanban CLI subcommands documented with CLI/MCP validation split
  - 74 top-level Hermes CLI commands categorized
  - 87 native tools inventoried across 31 toolsets
  - 14 profiles documented with spawnability classification
  - 53 skills documented (39 builtin, 14 local, 0 hub)
  - 10 MCP E2E validated commands reused from board QA
  - 5 P0 blockers for V4 release identified
  - Daemon explicitly marked DO_NOT_EXPOSE/NO APLICA
  - Operator quality gate feedback fully incorporated

### t_4d983898 — Source of Truth Draft
- Completed read-only V4 documentation draft and stale-docs inventory
- Evidence-bound to t_2d568471 plus all seven local-research parents
- Includes corrected four-profile OBSERVED spawnability (10 INFERRED_ONLY)
- Full 53-name skill inventory and sdlc-review caveat
- 74/47 CLI trees, 87-tool registry
- Runtime/config/attachments/MCP ledgers
- Registration ≠ operational PASS rule
- Hermes version: 0.20.2 (2026.8.16)
- Local head: 39cfd1ab41
- Deployed connector SHA: STILL_NOT_PROVEN
- Deployment label: Kanban_Beta is stale metadata; deployment classified STABLE by controller correction

### t_8a7b081c — Roadmap/Implementation/Dogfood Rewrites
- Rewrote authoritative V4 roadmap, implementation plan, and MCP-centered dogfood/QA plan
- Superseded both requested source tasks (t_91ef2f64 and t_343b3c40)
- Applied P0 scope/release-blocker distinction
- Current proven scope vocabulary: hermes:read, hermes:create, hermes:manage, hermes:board:create, optional offline_access
- Live 54-tool surface classification
- Disposable-board mutation rule
- Guarded/PLANNED V4 contracts
- Artifact-freeze regression coverage
- Acceptance checks: 15/15 PASS

## Open Questions and Evidence Gaps

### Connector and Deployment
- Exact deployed connector SHA remains STILL_NOT_PROVEN
- Live HTTP/API auth and reachability not fully validated
- Provider/model validity in production not confirmed
- Live SQLite schema dump not verified
- Native MCP/plugin/dynamic tool registration behavior not confirmed
- Live slash/terminate/heartbeat-retry behavior not observed

### Profile and Permission Systems
- Temporary per-task skill resolution mechanism not fully understood
- Fine-grained profile permission enforcement not implemented
- Historical C-IMPL-5 crash cause not resolved
- Managed overlay/effective controller config not documented

### Skill and Plugin Systems
- Skills-inspect hub-only limitation noted
- Local skill resolution mechanisms need validation
- Plugin/dynamic tool registration pathways unclear

### MCP Specific
- MCP transport layer for remote attachments (content_base64) not implemented
- Size caps for MCP transfers not enforced
- Skill query MCP tools not implemented
- SDLC-review force-load behavior in MCP context not defined

### Documentation and Process
- Post-commit artifact lifecycle regression observed (workspace changes not durable after task completion)
- Need for better artifact persistence mechanisms
- Cross-profile skill referencing limitations

### Regression Cases Documented
1. Post-complete workspace changes not durable (observed in t_484d4ab0)
2. Scope vocabulary corrections requiring rework (t_f96c8f07 superseded by t_484d4ab0)
3. Non-converging synthesis tasks introducing incorrect scopes/P0 semantics (t_343b3c40)
4. Artifact-freeze regression in dogfood QA (addressed in t_8a7b081c)

## Evidence Ledger

All claims in this documentation are bound to:
- Hermes v0.20.2 (2026.8.16)
- Source HEAD 39cfd1ab41 (local master)
- Board `hermes-chatgpt-mcp` MCP surface
- Local investigation sessions August 16-19, 2026
- Board QA validation sessions
- Live connector discovery 2026-08-19

Last updated: 2026-08-19