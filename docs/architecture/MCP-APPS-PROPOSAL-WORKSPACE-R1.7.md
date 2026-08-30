# MCP Apps Proposal Workspace R1.7

Status: **CANDIDATE SPECIFICATION**  
Scope: `hermes-chatgpt-mcp` MCP Apps UI + read/write control-plane primitives  
Activation: **NOT ACTIVE**. This document defines a candidate feature and does not change authority, release, or canonical-source semantics by itself.

## 1. Objective

Turn the Hermes MCP App from a board viewer/controller into a shared planning workspace where ChatGPT and the human can collaboratively shape a plan before any canonical Kanban mutation occurs.

The core invariant is:

> A proposal is not a Hermes task set until an explicit commit operation succeeds against the expected canonical board revision.

The UI must make proposed state visually and semantically distinct from canonical state at all times.

## 2. User outcomes

The user should be able to:

1. Ask ChatGPT to propose a plan and see the proposed cards immediately in the board UI without creating canonical Hermes tasks.
2. Edit proposed titles, bodies, priorities, assignees, skills, model/provider preferences, tenants and dependency edges directly in the UI.
3. Add or delete draft cards and edges manually.
4. Select one or more draft or canonical cards in the UI and refer to them naturally in chat, e.g. “split these two”, “why are these blocked?”, “use a reviewer for these”.
5. Ask ChatGPT to revise only a selected branch/subgraph of the proposal.
6. Confirm the whole proposal or only a selected subset.
7. See a deterministic preview/diff of what the commit will create/change before confirmation.
8. Recover the current proposal and selection context if the widget/model context is lost or the conversation is resumed.
9. Detect stale proposals safely if the canonical board changed materially while the draft was being edited.

## 3. Non-goals

R1.7 does not:

- silently create canonical tasks while a proposal is being edited;
- grant additional mutation authority because a card is selected;
- bypass Human Gates or protected release/deploy rules;
- infer missing execution provenance or model history;
- treat UI state as canonical board state;
- make direct destructive/admin actions available from the proposal surface;
- require the entire proposal body to be injected into every model turn.

## 4. Core model

### 4.1 Proposal identity

A proposal is a versioned, session-addressable object:

```text
proposal_id: p_<opaque-id>
revision: monotonically increasing integer
board: hermes-chatgpt-mcp
base_board_revision: canonical revision observed when proposal/revision was created
status: draft | partially_committed | committed | discarded | conflicted
```

Each user or ChatGPT edit creates a new proposal revision. The active revision is immutable once superseded.

### 4.2 Draft card identity

Draft cards use proposal-local IDs and never masquerade as Hermes task IDs:

```text
draft_id: d_<opaque-id>
canonical_task_id: null until commit
```

After a successful commit the server returns an exact mapping:

```text
d_01 -> t_abcd1234
d_02 -> t_efgh5678
```

### 4.3 Draft edge model

Dependency edges are versioned proposal objects:

```text
parent_ref: d_01 | t_existing
child_ref: d_02 | t_existing
state: proposed_add | proposed_remove | unchanged
```

The proposal layer must support a true DAG, including multiple parents.

## 5. Visual contract

### 5.1 Canonical vs proposed

Canonical tasks keep the standard card appearance. Draft cards must be unmistakable, for example:

- dashed border;
- `DRAFT` badge;
- translucent/ghost surface;
- proposed edges drawn dashed;
- canonical IDs never shown for uncommitted draft cards.

The distinction must remain visible in both Kanban and Dependencies views.

### 5.2 Workbench modes

The shared toolbar should support at least:

```text
View: Kanban | Dependencies
Layer: Canonical | Proposal | Both
```

The user may compare the proposal against the canonical board without committing it.

### 5.3 Selection

Selection is first-class UI state:

- short tap/click: focus/select one card;
- long-press stationary on touch: toggle multi-selection;
- selected count remains visible;
- selection survives refresh and view switching where referenced items still exist;
- selection may contain both draft and canonical references.

Selection does **not** authorize mutation.

## 6. ChatGPT ↔ widget context contract

The widget should publish compact semantic context rather than copying full card bodies into the model context.

Suggested context payload:

```json
{
  "board": "hermes-chatgpt-mcp",
  "active_proposal": {"id": "p_123", "revision": 7},
  "selected_refs": ["d_03", "d_07", "t_abc"],
  "view": "dependencies",
  "focus_ref": "d_03"
}
```

The host bridge may use MCP Apps model-context update facilities when available, but correctness must not depend exclusively on ephemeral host context.

The MCP must expose a recovery read such as:

```text
get_active_proposal_context(session_id?)
```

so ChatGPT can rehydrate the active proposal/selection state after reconnect, cache loss, or a new turn.

## 7. Proposed MCP primitives

Names are candidates; final schemas require implementation review.

### 7.1 Read-only

```text
proposal_get(proposal_id, revision?)
proposal_list(board?, status?, limit?)
proposal_diff(proposal_id, from_revision?, to_revision?, against_canonical=true)
proposal_validate(proposal_id, revision)
proposal_commit_preview(proposal_id, revision, selected_refs?)
proposal_context_get(session_id?)
```

All reads must be bounded.

### 7.2 Draft mutation

Draft mutations affect only proposal storage:

```text
proposal_create(board, base_board_revision, initial_plan?)
proposal_card_add(...)
proposal_card_update(...)
proposal_card_remove(...)
proposal_edge_add(...)
proposal_edge_remove(...)
proposal_selection_set(selected_refs, focus_ref?)
proposal_discard(proposal_id, expected_revision)
```

Every mutation requires `expected_revision` and returns a new revision. Stale revision writes fail closed with conflict information.

### 7.3 Canonical commit

Canonical mutation occurs only through an explicit operation:

```text
proposal_commit(
  proposal_id,
  revision,
  expected_board_revision,
  selected_refs?,
  confirmation_token?
)
```

A commit must:

1. validate proposal revision identity;
2. validate canonical board revision / material conflicts;
3. re-run task/profile/skill/model/dependency validation;
4. produce a deterministic commit plan;
5. require explicit confirmation using the normal ChatGPT/MCP mutation flow;
6. execute canonical commands in bounded deterministic order;
7. read back canonical state after each mutation;
8. stop safely on failure and return exact partial-commit evidence;
9. return draft→canonical ID mapping;
10. persist commit provenance.

The implementation must not fake transactionality if Hermes cannot provide an atomic multi-card transaction. If atomic commit is unavailable, the response must explicitly expose partial success and remaining unapplied draft operations.

## 8. Partial commit

The user may commit only a selected subset.

Rules:

- selected draft cards must include any required uncommitted parent dependencies or the preview must report them as required additions;
- committing a subset creates a new proposal revision in `partially_committed` state;
- committed draft references become canonical mappings while remaining draft branches continue to exist;
- no dangling proposed edge may silently disappear;
- the UI must show committed vs remaining draft branches distinctly.

## 9. Conflict model

A proposal can become stale while the canonical board evolves.

`proposal_commit_preview` must classify at least:

- `NO_CONFLICT`;
- `CANONICAL_TASK_CHANGED`;
- `DEPENDENCY_CHANGED`;
- `ASSIGNEE_OR_CAPABILITY_CHANGED`;
- `BOARD_REVISION_CHANGED_NON_MATERIAL`;
- `BOARD_REVISION_CHANGED_MATERIAL`;
- `AUTHORITY_CHANGED`;
- `PROPOSAL_STALE_REVISION`.

Material conflict must fail closed and require rebase/review. A proposal must never silently overwrite canonical changes.

## 10. Proposal rebase

Candidate flow:

```text
proposal_rebase(proposal_id, revision, target_board_revision)
```

Rebase produces a **new proposal revision** and a visible conflict/delta report. It never mutates canonical tasks.

## 11. Chat interaction examples

With UI selection context present, the following should be resolvable without the user copying task IDs:

```text
"Split these two cards."
"Make the selected branch use reviewer after coder."
"Why are these blocked?"
"Discard this draft branch and add a test card before review."
"Commit only these four."
```

ChatGPT must resolve pronouns/referents through proposal/selection context, then read the referenced objects from MCP before answering or mutating.

## 12. Context economy

Do not inject complete proposal contents into every turn.

Default conversational context should contain only:

- proposal id + revision;
- selected/focused refs;
- board id;
- view mode;
- compact dirty/conflict indicators.

Detailed card bodies, graph neighborhoods, validation results and commit previews are fetched on demand.

## 13. Authority and safety invariants

1. Draft mutation authority is distinct from canonical Kanban mutation authority.
2. Selection grants zero additional authority.
3. Proposal commit uses the existing canonical command path; no hidden direct DB mutation.
4. Human Gate/release/deploy semantics remain unchanged.
5. A proposal cannot contain an instruction that causes automatic deploy/restart/protected merge on commit.
6. Any card that would trigger authority-sensitive work is created according to normal workflow and remains subject to its own gates.
7. Candidate/evidence identity changes invalidate material gates exactly as today.
8. Proposal persistence must not contain OAuth tokens, secrets or unbounded worker logs.

## 14. Audit/provenance

Persist at least:

```text
proposal_created
proposal_revision_created
proposal_selection_changed (bounded / optional retention)
proposal_validation
proposal_commit_preview
proposal_commit_started
proposal_operation_applied
proposal_operation_failed
proposal_commit_completed
proposal_rebased
proposal_discarded
```

For canonical mutations, provenance must identify both proposal revision and resulting Hermes task IDs.

## 15. Storage and lifecycle

Proposal state is operational state, not canonical Kanban state.

Recommended lifecycle:

```text
DRAFT -> PARTIALLY_COMMITTED -> COMMITTED
   |             |
   +-----------> DISCARDED
   |
   +-----------> CONFLICTED -> DRAFT (via explicit rebase)
```

Retention should be bounded and configurable. Expired drafts should be archived/expired, never silently committed.

## 16. Dependencies view integration

The R1.6.3 DAG view should later render proposal nodes and edges using the same layout engine:

- solid lines: canonical dependency;
- dashed lines: proposed dependency;
- removed edge: explicit strike/removed visual in diff mode;
- draft node: ghost/dashed card;
- selected branch: persistent upstream/downstream emphasis.

This avoids separate planning and execution visual models.

## 17. Kanban sorting integration

Proposal and canonical cards should respect the current presentation-only sort selector where meaningful:

- priority;
- title;
- created time;
- updated time when canonically available;
- assignee;
- dependency/topological order.

Sorting never mutates canonical task priority/order.

## 18. E2E acceptance plan

### Phase A — MCP primitives

- create/read/revise proposal;
- stale revision rejection;
- draft card/edge CRUD;
- bounded reads;
- no canonical task creation before commit;
- exact commit preview;
- partial commit mapping;
- conflict/rebase behavior;
- audit events.

### Phase B — MCP Apps UI

- ChatGPT proposes cards and they render as DRAFT;
- user edits/adds/removes cards and edges;
- selection survives refresh/view switch;
- dependencies view renders draft + canonical DAG;
- commit preview visibly matches proposal revision;
- no mutation before Confirm.

### Phase C — ChatGPT host loop

Real ChatGPT-side dogfood must prove:

1. select one or more cards in the widget;
2. return to chat and refer to “these cards” naturally;
3. ChatGPT resolves the exact refs from widget/model context or MCP recovery state;
4. ChatGPT modifies the proposal, not canonical Kanban;
5. UI refreshes to the new proposal revision;
6. explicit commit creates the intended canonical cards with exact readback;
7. reconnect/new turn can recover active proposal state.

Host-specific model-context behavior must be classified as VERIFIED/PARTIAL/UNVERIFIED rather than assumed from SDK support.

## 19. Implementation slices

Recommended bounded sequence:

### P0 — Proposal IR + persistence

Versioned proposal/card/edge schemas, revision concurrency, bounded storage, reads and validation. No canonical writes.

### P1 — Draft editor in Kanban

Ghost cards/edges, add/edit/remove, selection context, proposal revision indicator.

### P2 — Commit preview + canonical commit

Exact validation, optimistic board revision check, partial commit evidence, draft→task mapping.

### P3 — ChatGPT context bridge

Compact model-context updates plus MCP recovery primitive; selection-based conversational references.

### P4 — Dependencies view parity

Proposal overlay in DAG/tree view, branch revision, focus and partial commit.

### P5 — Independent real-host E2E

ChatGPT Web/mobile dogfood with reconnect/context recovery and stale conflict scenarios.

## 20. Falsifiable success criteria

R1.7 is successful only if real dogfood demonstrates all of the following:

- planning can be performed and substantially edited without creating canonical cards;
- ChatGPT can correctly refer to UI-selected cards after a user returns to chat;
- proposal context can be recovered without copying the full draft into every turn;
- explicit commit produces the exact reviewed plan or fails closed on stale/conflict;
- partial commit does not corrupt remaining draft graph state;
- proposal workflow reduces accidental card creation/rework compared with direct plan→create flow;
- no authority or Human Gate invariant is weakened.

## 21. Open design questions for independent review

1. Whether proposal persistence belongs in the MCP repository/runtime or a Hermes-native proposal primitive.
2. Whether selection state should be persisted durably, session-durably, or remain short-lived with only proposal revision durable.
3. Whether canonical board revision is sufficiently granular for conflict detection or requires task/edge-level expected versions.
4. Whether commit needs a dedicated confirmation token bound to proposal revision + commit preview hash.
5. How to represent edits to existing canonical cards in a proposal without conflating them with new draft cards.
6. How much proposal state may be safely exposed through MCP Apps model context versus fetched by tools.
7. Whether multi-user/cross-session proposal ownership is needed before the first dogfood release.

## 22. Recommended next decision

Do not implement R1.7 until R1.6.2 mobile workbench and R1.6.3 dependency/sorting view have passed their own independent reviews and real ChatGPT-side dogfood.

After that, start with **P0 Proposal IR + persistence** and an independent architecture review. Do not begin with UI-only mock drafts: the proposal identity/revision/conflict contract must be real first.
