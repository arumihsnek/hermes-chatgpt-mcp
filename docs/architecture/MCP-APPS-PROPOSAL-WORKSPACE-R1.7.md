# MCP Apps Proposal Workspace R1.7

Status: **CANDIDATE SPECIFICATION**  
Scope: `hermes-chatgpt-mcp` MCP Apps UI + read/write control-plane primitives  
Activation: **NOT ACTIVE**. This document defines a candidate feature and does not change authority, release, or canonical-source semantics by itself.
Revision note: this revision adds the non-dispatchable `ATTENTION_REQUEST` / conductor handoff path and binds it to the existing Proposal Workspace context bridge.

## 1. Objective

Turn the Hermes MCP App from a board viewer/controller into a shared planning workspace where ChatGPT and the human can collaboratively shape a plan before any canonical Kanban mutation occurs, while also giving workers a durable way to elevate evidence or decisions to the human/ChatGPT conductor without abusing executable Kanban tasks.

The core invariants are:

> A proposal is not a Hermes task set until an explicit commit operation succeeds against the expected canonical board state.

> An attention request is not executable work and never becomes dispatchable merely because a worker wants ChatGPT or the human to inspect it.

The UI must make proposed state, attention state, and canonical state visually and semantically distinct at all times.

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
10. See worker/system attention requests in a dedicated non-dispatchable surface.
11. Open a request in ChatGPT with one explicit user action, then have ChatGPT rehydrate the exact current evidence from MCP rather than copy the whole payload into chat.
12. Turn an attention request into a proposal or explicit task only through a visible, deliberate transition.

## 3. Non-goals

R1.7 does not:

- silently create canonical tasks while a proposal is being edited;
- grant additional mutation authority because a card is selected;
- treat an attention request as a special READY/TODO task or assignee convention;
- assume a background worker can wake ChatGPT asynchronously;
- bypass Human Gates or protected release/deploy rules;
- infer missing execution provenance or model history;
- treat UI state as canonical board state;
- make direct destructive/admin actions available from the proposal or attention surface;
- require the entire proposal, request, or evidence body to be injected into every model turn.

## 4. Core model

R1.7 distinguishes three interaction objects that must never be conflated:

| Object | Meaning | Dispatchable | Canonical Kanban state | Authority |
|---|---|---:|---:|---|
| `TASK` | Work Hermes may route to a worker | yes, subject to normal workflow | yes | normal task/workflow authority only |
| `ATTENTION_REQUEST` | A worker/system asks the human or ChatGPT conductor to inspect, discuss, decide, or transform referenced evidence | **no** | no | **none**; reference and intent only |
| `PROPOSAL` | Editable, revisioned plan/delta that may later materialize into canonical tasks after explicit commit | no | no | draft mutation only until canonical commit |

An `ATTENTION_REQUEST` MUST NOT be represented as a READY/TODO task merely to make ChatGPT notice it. Doing so pollutes dispatch state and confuses evidence handoff with executable work.

### 4.0 Attention request identity

An attention request is a bounded durable handoff envelope, not a worker job and not a Human Gate. It SHOULD contain at least:

```text
request_id: ar_<opaque-id>
revision: monotonically increasing integer
board: hermes-chatgpt-mcp
kind: review_verdict | decision_needed | blocked_escalation | evidence_ready | proposal_feedback | ...
target: conductor | human | both
status: open | acknowledged | resolved | expired | superseded
created_by: authenticated principal / worker identity
summary: bounded text
source_refs: bounded exact references
suggested_actions: optional bounded UI hints
created_at / updated_at / expires_at
supersedes_request_id: optional
```

`source_refs` may bind exact task IDs, run IDs, proposal ID/revision, candidate SHA, evidence/comment IDs, incident IDs, or other canonical provenance references.

Requests that depend on a material candidate/evidence identity MUST bind that identity exactly. If the candidate or material evidence changes, the request becomes stale/superseded rather than carrying decision authority forward.

Implementations SHOULD first consider whether the existing Hermes event/notification substrate can mechanically enforce these semantics before adding a separate persistence subsystem. The semantic boundary is mandatory; a new database is not.

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

### 5.4 Needs attention surface

Open attention requests render outside normal Kanban work columns in a compact **Needs attention** surface. They may be grouped or filtered by kind, age, source, or urgency, but they never contribute to READY/TODO dispatch counts.

A request should expose bounded actions such as:

- **Discuss in ChatGPT**;
- **Open evidence**;
- **Turn into proposal**;
- **Acknowledge**;
- **Resolve / Dismiss**.

If a request is stale or superseded, the UI must say so and prevent any stale decision affordance from being presented as current authority.

## 6. ChatGPT ↔ widget context contract

The widget should publish compact semantic context rather than copying full card bodies or request evidence into the model context.

Suggested context payload:

```json
{
  "board": "hermes-chatgpt-mcp",
  "active_proposal": {"id": "p_123", "revision": 7},
  "attention_request": {"id": "ar_42", "revision": 3},
  "selected_refs": ["d_03", "d_07", "t_abc"],
  "view": "dependencies",
  "focus_ref": "d_03",
  "intent": "discuss"
}
```

The host bridge may use MCP Apps model-context update facilities when available, but correctness must not depend exclusively on ephemeral host context.

The MCP must expose a recovery read such as:

```text
get_active_proposal_context(session_id?)
```

so ChatGPT can rehydrate the active proposal/selection/request state after reconnect, cache loss, or a new turn.

### 6.1 Attention-to-chat bridge

Baseline MCP Apps behavior should use standard bridge facilities such as `ui/update-model-context` for compact semantic context and `ui/message` when the host supports a user-initiated conversational handoff.

ChatGPT-specific `window.openai.sendFollowUpMessage(...)` may be used as an additive convenience only after feature detection. It is not a correctness dependency and does not redefine MCP authority.

The handoff is explicitly **user-initiated**:

```text
worker/system -> persist ATTENTION_REQUEST
             -> workbench shows Needs attention
user         -> taps Discuss in ChatGPT
widget       -> sends request_id + selected refs + compact intent
ChatGPT      -> reads request + referenced canonical evidence through MCP
             -> reconstructs live state
             -> discusses / proposes / performs only separately authorized actions
```

A background worker completion or asynchronous tool callback MUST NOT assume it can autonomously wake ChatGPT. If host messaging/context facilities are absent or fail, the request remains visible and recoverable through MCP.

This means the durable object is the request, not the chat message. The chat message is merely a transport hint telling ChatGPT which live object to retrieve.

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
attention_request_get(request_id)
attention_request_list(board?, status="open", target?, limit?)
```

All reads must be bounded.

### 7.2 Draft and attention mutation

Proposal mutations affect only proposal storage. Attention mutations affect only non-dispatchable attention state:

```text
proposal_create(board, base_board_revision, initial_plan?)
proposal_card_add(...)
proposal_card_update(...)
proposal_card_remove(...)
proposal_edge_add(...)
proposal_edge_remove(...)
proposal_selection_set(selected_refs, focus_ref?)
proposal_discard(proposal_id, expected_revision)

attention_request_create(kind, summary, source_refs[], target?, suggested_actions?, expires_at?)
attention_request_ack(request_id, expected_revision)
attention_request_resolve(request_id, expected_revision, resolution?)
```

Proposal mutations require `expected_revision` and return a new proposal revision. Attention-request updates use their own optimistic request revision/version. Stale writes fail closed with conflict information.

`attention_request_create` MUST reject attempts to encode dispatch semantics, Human Gate decisions, unbounded worker logs, or direct dangerous actions. Suggested actions are UI hints, never executable authority.

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

An attention request may lead to a proposal or explicit task creation, but only through those normal explicit paths. Resolving or discussing a request never materializes canonical work by itself.

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

Attention requests have a parallel stale-evidence rule: when a request binds a material candidate/evidence identity and that identity changes, the request becomes `superseded` or is explicitly rebased to a new request revision. It must never silently inherit a new candidate.

## 10. Proposal rebase

Candidate flow:

```text
proposal_rebase(proposal_id, revision, target_board_revision)
```

Rebase produces a **new proposal revision** and a visible conflict/delta report. It never mutates canonical tasks.

## 11. Chat interaction examples

### 11.1 Selection-driven proposal interaction

With UI selection context present, the following should be resolvable without the user copying task IDs:

```text
"Split these two cards."
"Make the selected branch use reviewer after coder."
"Why are these blocked?"
"Discard this draft branch and add a test card before review."
"Commit only these four."
```

ChatGPT must resolve pronouns/referents through proposal/selection context, then read the referenced objects from MCP before answering or mutating.

### 11.2 Worker-to-conductor attention interaction

A worker may persist an attention request such as:

```text
Reviewer -> Attention ar_42
kind=review_verdict
source_refs=[task:t_review, candidate:47642b8..., comment:1628]
summary="Review passed; two non-blocking risks need conductor disposition."
```

The workbench renders the request in **Needs attention** rather than a Kanban work column.

On **Discuss in ChatGPT**, the widget sends a compact user-initiated follow-up containing `request_id` plus selected refs. ChatGPT reads `attention_request_get` and the referenced canonical evidence, reconstructs current state, and then discusses or prepares a proposal. The request itself neither creates work nor authorizes mutation.

On **Turn into proposal**, ChatGPT or the widget creates/revises a `PROPOSAL`; it MUST NOT silently translate the request directly into canonical tasks.

## 12. Context economy

Do not inject complete proposal or attention contents into every turn.

Default conversational context should contain only:

- proposal id + revision;
- selected/focused refs;
- board id;
- view mode;
- compact dirty/conflict indicators;
- optional active `attention_request` id/revision and intent.

Detailed card bodies, request evidence, graph neighborhoods, validation results and commit previews are fetched on demand.

## 13. Authority and safety invariants

1. Draft mutation authority is distinct from canonical Kanban mutation authority.
2. Selection grants zero additional authority.
3. Proposal commit uses the existing canonical command path; no hidden direct DB mutation.
4. Human Gate/release/deploy semantics remain unchanged.
5. A proposal cannot contain an instruction that causes automatic deploy/restart/protected merge on commit.
6. Any card that would trigger authority-sensitive work is created according to normal workflow and remains subject to its own gates.
7. Candidate/evidence identity changes invalidate material gates exactly as today.
8. Proposal/attention persistence must not contain credentials or unbounded worker logs.
9. Attention requests grant zero mutation, dispatch, review, Human Gate, release, deploy or approval authority.
10. Attention requests are excluded from normal READY/TODO dispatch queues; turning one into work requires an explicit task/proposal materialization path.
11. A user-initiated chat handoff conveys referents and intent only; ChatGPT must re-read live evidence before material decisions.
12. A request targeted at `human`, `conductor`, or both does not redefine who may perform the eventual action.

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
attention_request_created
attention_request_acknowledged
attention_request_resolved
attention_request_expired
attention_request_superseded
attention_request_opened_in_chat (bounded telemetry; no transcript copy)
```

For canonical mutations, provenance must identify both proposal revision and resulting Hermes task IDs.

For attention requests, provenance must preserve exact creator/source identity and bounded source references. `created_by` is provenance, not assignee semantics.

## 15. Storage and lifecycle

Proposal state and attention state are operational state, not canonical Kanban state.

Recommended proposal lifecycle:

```text
DRAFT -> PARTIALLY_COMMITTED -> COMMITTED
   |             |
   +-----------> DISCARDED
   |
   +-----------> CONFLICTED -> DRAFT (via explicit rebase)
```

Recommended attention lifecycle:

```text
OPEN -> ACKNOWLEDGED -> RESOLVED
  |          |
  |          +-------> SUPERSEDED
  +------------------> EXPIRED
```

Retention should be bounded and configurable. Expired drafts should be archived/expired, never silently committed. Expired attention requests should disappear from default attention UI while remaining available as bounded historical evidence when policy permits.

## 16. Dependencies view integration

The R1.6.3 DAG view should later render proposal nodes and edges using the same layout engine:

- solid lines: canonical dependency;
- dashed lines: proposed dependency;
- removed edge: explicit strike/removed visual in diff mode;
- draft node: ghost/dashed card;
- selected branch: persistent upstream/downstream emphasis.

Attention requests may visually badge referenced nodes/branches, but the badge must not create dependency edges or alter DAG readiness.

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

Attention requests use their own presentation ordering and are never mixed into normal Kanban status sorting as pseudo-tasks.

## 18. E2E acceptance plan

### Phase A — MCP primitives

- create/read/ack/resolve a bounded non-dispatchable attention request;
- attention request binds exact source/candidate/evidence refs and becomes superseded on material identity drift;
- attention requests never appear as READY/TODO work;
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

- open attention requests render in a compact **Needs attention** surface distinct from Kanban work columns;
- **Discuss in ChatGPT** is explicit user action and sends only bounded request/selection context;
- absence/failure of host chat bridge leaves the request recoverable through MCP;
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
7. reconnect/new turn can recover active proposal state;
8. a worker-generated attention request can be opened from the widget into chat, ChatGPT rehydrates its exact evidence via MCP, and no canonical task is created merely by the handoff;
9. an asynchronous/background request remains durable without assuming autonomous ChatGPT wake-up;
10. stale/superseded request evidence is surfaced as stale and cannot masquerade as a current decision input.

Host-specific model-context/message behavior must be classified as VERIFIED/PARTIAL/UNVERIFIED rather than assumed from SDK support.

## 19. Implementation slices

Recommended bounded sequence:

### P0 — Proposal IR + persistence

Versioned proposal/card/edge schemas, revision concurrency, bounded storage, reads and validation. No canonical writes.

### P1 — Draft editor in Kanban

Ghost cards/edges, add/edit/remove, selection context, proposal revision indicator.

### P2 — Commit preview + canonical commit

Exact validation, optimistic board revision check, partial commit evidence, draft→task mapping.

### P3 — Attention + ChatGPT context bridge

First add the bounded non-dispatchable `ATTENTION_REQUEST` IR/read path and workbench surface. Then add compact model-context updates, explicit user-initiated chat handoff, MCP recovery primitives, and selection/request-based conversational references. Do not make autonomous ChatGPT wake-up a dependency.

### P4 — Dependencies view parity

Proposal overlay in DAG/tree view, branch revision, focus, attention badges and partial commit.

### P5 — Independent real-host E2E

ChatGPT Web/mobile dogfood with attention handoff, reconnect/context recovery and stale conflict scenarios.

## 20. Falsifiable success criteria

R1.7 is successful only if real dogfood demonstrates all of the following:

- planning can be performed and substantially edited without creating canonical cards;
- ChatGPT can correctly refer to UI-selected cards after a user returns to chat;
- proposal context can be recovered without copying the full draft into every turn;
- a worker can raise a durable attention request without creating dispatchable Kanban work;
- the user can open that request in ChatGPT and ChatGPT resolves exact live evidence from MCP rather than trusting a copied prompt payload;
- explicit commit produces the exact reviewed plan or fails closed on stale/conflict;
- partial commit does not corrupt remaining draft graph state;
- proposal workflow reduces accidental card creation/rework compared with direct plan→create flow;
- attention workflow reduces fake/coordinator-assigned evidence cards compared with task-based handoff;
- no authority or Human Gate invariant is weakened.

## 21. Open design questions for independent review

1. Whether proposal persistence belongs in the MCP repository/runtime or a Hermes-native proposal primitive.
2. Whether selection state should be persisted durably, session-durably, or remain short-lived with only proposal revision durable.
3. Whether canonical board revision is sufficiently granular for conflict detection or requires task/edge-level expected versions.
4. Whether commit needs a dedicated confirmation token bound to proposal revision + commit preview hash.
5. How to represent edits to existing canonical cards in a proposal without conflating them with new draft cards.
6. How much proposal state may be safely exposed through MCP Apps model context versus fetched by tools.
7. Whether multi-user/cross-session proposal ownership is needed before the first dogfood release.
8. Whether `ATTENTION_REQUEST` can be enforced by the existing Hermes event/notification substrate or needs a dedicated minimal store.
9. Whether baseline MCP Apps `ui/message` is sufficient across target hosts or ChatGPT should additionally expose `sendFollowUpMessage` behind capability detection; real-host E2E must decide, not documentation assumptions.
10. Exact TTL/deduplication rules for repeated worker requests that bind the same root cause/evidence generation.
11. Whether request acknowledgement is user-specific or global when more than one human/conductor session can observe the same board.

## 22. Recommended next decision

Do not implement R1.7 until R1.6.2 mobile workbench and R1.6.3 dependency/sorting view have passed their own independent reviews and real ChatGPT-side dogfood.

After that, start with **P0 Proposal IR + persistence** and an independent architecture review. The `ATTENTION_REQUEST` path belongs in the same shared interaction/context architecture but should be implemented at the narrowest enforceable layer, preferably reusing Hermes notification/event primitives if they can preserve non-dispatchability, provenance, boundedness and revision semantics.

Do not begin with UI-only mock drafts or a fake “assignee=chatgpt” convention: proposal identity/revision/conflict and attention identity/non-dispatchability must be real first.

## 23. Dogfood motivation and design consequence

Observed dogfood exposed the missing semantic primitive: a reviewer created a child card containing a completed review verdict and targeted it at the ChatGPT conductor. The intent was useful — elevate verified evidence for interactive disposition — but representing that handoff as a READY task made completed evidence look like executable backlog.

R1.7 therefore treats the desired behavior as an `ATTENTION_REQUEST`, not as a special assignee convention. The UI should make requests first-class and actionable while the canonical Kanban remains reserved for executable work. This is a workflow/observability correction, not a weakening of task provenance or review authority.

Current host-capability assumption (to be revalidated in real E2E): the MCP Apps bridge provides standard message/model-context mechanisms, while ChatGPT exposes additional `window.openai` conveniences such as `sendFollowUpMessage`. These capabilities are transport conveniences only; durable MCP state and explicit user action remain the correctness boundary.
