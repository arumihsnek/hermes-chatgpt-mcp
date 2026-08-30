# Proposal Workspace R1

Status: CANDIDATE SPECIFICATION
Repository: `arumihsnek/hermes-chatgpt-mcp`
Scope: ChatGPT MCP Apps + canonical Hermes Kanban

## 1. Problem

The current MCP Apps board is primarily an operational view over canonical Hermes tasks. Planning in chat and manipulating the resulting Kanban are still separated: ChatGPT can describe a plan in text, but the user cannot safely inspect, rearrange, edit, extend, compare, or selectively accept that plan in the board before canonical tasks exist.

Proposal Workspace introduces a shared planning surface between ChatGPT, the user, and Hermes. A plan can be rendered as editable draft cards and dependency edges without mutating the canonical Kanban. The user can edit the proposal visually, select one or more draft or real cards, refer to that selection naturally in chat, and explicitly materialize an exact proposal revision only after review.

This is not a second Kanban database and must not become hidden memory. It is a bounded, revisioned proposal layer with explicit promotion into canonical Hermes state.

## 2. Core invariant

`DRAFT != CANONICAL`.

No proposal operation may create, assign, schedule, dispatch, block, review, or otherwise mutate a canonical Hermes task until an explicit commit operation is confirmed.

The UI must visually distinguish proposed state from canonical state at all times.

## 3. User experience

### 3.1 Chat -> visual proposal

ChatGPT may produce a structured plan through a proposal tool rather than directly calling `create_task`.

The board renders:

- proposed new cards as dashed/ghost cards;
- proposed dependency edges as dashed connectors;
- proposed edits to existing cards as overlays/diffs on the canonical card;
- proposed deletions/removals as struck or dimmed deltas, never as actual archive/delete operations;
- a persistent `DRAFT <proposal-id> · rev <n>` indicator.

The proposal can be inspected in both `Kanban` and `Dependencies` views.

### 3.2 Visual editing

Within the proposal layer the user may:

- create a new draft card;
- edit title/body/priority/assignee/profile/skills/model/provider intent;
- link/unlink draft dependencies;
- propose edits to existing canonical cards;
- remove a draft card;
- reorder presentation without changing canonical priority;
- multi-select draft and/or canonical cards;
- ask ChatGPT to rewrite, split, merge, reprioritize, or reroute selected items.

Each semantic proposal mutation creates a new proposal revision. UI-only preferences such as sort mode, zoom, collapsed branches, and scroll position do not create proposal revisions.

### 3.3 Chat selection handoff

The widget should publish compact selection context to the model when the host supports MCP Apps model-context updates, for example:

```json
{
  "workspace": "proposal:p_123",
  "revision": 7,
  "selection": ["draft:d_3", "task:t_abcd"],
  "view": "dependencies"
}
```

ChatGPT must not rely exclusively on host-retained widget context. The MCP must also expose a bounded session-scoped selection read/write surface so that the assistant can recover the active proposal and selection after refresh, reconnect, or context loss.

Selection state must carry `updated_at` and a bounded TTL. R1 SHOULD default to a short recoverability window (for example 30 minutes) and MUST treat expired selection as absent. A selection write should include the exact proposal revision it refers to; if that revision is no longer current, the server returns a stale-selection signal rather than silently rebinding the same refs.

Natural-language references such as "estas dos", "la rama que he seleccionado", or "las tres de arriba" may resolve only when the selection token is current and unambiguous. Otherwise the assistant must read the active selection rather than guess.

Selection conveys reference, not authority. Selecting a task never authorizes mutation.

## 4. Data model

### 4.1 Proposal

A proposal record SHOULD contain at least:

- `proposal_id`
- `board_slug`
- `owner_subject` or equivalent authenticated principal binding
- `session_id` when available
- `created_at`
- `updated_at`
- `expires_at`
- `base_snapshot`
- `current_revision`
- `status`: `draft | partially_committed | committed | discarded | expired`
- optional human title/goal

Proposal storage must be isolated from canonical Hermes Kanban tables/state.

### 4.2 Revision

Proposal revisions are immutable logical snapshots or append-only deltas with deterministic reconstruction.

A revision contains a bounded set of operations such as:

- `draft_card_create`
- `draft_card_patch`
- `draft_card_remove`
- `canonical_card_patch_proposal`
- `edge_add`
- `edge_remove`
- `selection_hint` only when semantically relevant

Every mutation uses optimistic concurrency through `expected_revision`.

`proposal_apply` MUST be bounded. R1 should define explicit maxima for operations per call, draft cards/edges per proposal, payload bytes, and readback items. Oversized batches fail before mutation; they are never silently truncated. Every successful apply returns the new exact revision and a bounded readback of changed draft entities.

Concurrent stale writes fail with `CONFLICT`; the server does not silently merge semantically conflicting edits.

### 4.3 Draft identity

Draft cards use proposal-local opaque IDs, e.g. `d_01`, never fake canonical Hermes task IDs.

On commit the server returns an exact mapping:

```json
{
  "proposal_id": "p_123",
  "revision": 7,
  "materialized": {
    "d_01": "t_a1b2",
    "d_02": "t_c3d4"
  }
}
```

Draft edge references are rewritten through this mapping transactionally or through a validated bounded sequence with compensating failure semantics.

Committed revisions MUST persist an audit fingerprint over the exact proposal revision, canonical materialization mapping, and commit outcome. The fingerprint is evidence for later review/debugging; it does not replace canonical task/edge readback.

## 5. Base-state and stale-plan protection

Proposal commit must bind to the canonical state the user actually reviewed.

Do not depend solely on `board_revision` until the runtime proves it is meaningful and monotonic. R1 MUST define a minimum evidence set for `base_snapshot`: exact IDs plus stable fingerprints of every canonical task/edge the proposal reads or proposes to change. A monotonic board revision and/or ledger cursor may strengthen that evidence but cannot substitute for the affected-set fingerprints until independently proven reliable. A valid `base_snapshot` may therefore include:

- required stable fingerprints of canonical tasks/edges touched by the proposal;
- exact task IDs + relevant fields + dependency edges used to compute those fingerprints;
- canonical board revision when reliable;
- ledger/event cursor when reliable.

At commit, canonical items referenced or modified by the proposal are re-read.

If material state changed, commit fails closed with a structured conflict response containing bounded differences. The user may then rebase the proposal into a new revision.

Unrelated board changes should not necessarily invalidate a proposal if the affected-set fingerprint proves the proposal remains valid.

## 6. Proposed MCP surface

Names are provisional; schemas must be reviewed before implementation.

### Read-only

- `proposal_get(proposal_id, revision?)`
- `proposal_list(board?, status?, limit?)`
- `proposal_validate(proposal_id, revision)`
- `proposal_diff(proposal_id, from_revision, to_revision)`
- `proposal_selection_get(proposal_id?)`

### Draft mutations

- `proposal_create(board, goal?, initial_plan?, expected_base?)`
- `proposal_apply(proposal_id, expected_revision, operations[])`
- `proposal_selection_set(proposal_id, revision, selected_refs[])`
- `proposal_discard(proposal_id, expected_revision)`

Draft mutations alter only proposal state and require no canonical Kanban write authority beyond whatever dedicated proposal scope/policy is chosen.

### Canonical materialization

- `proposal_commit(proposal_id, revision, subset?, expected_base_snapshot, mode="materialize")`

`proposal_commit` is authority-bearing. It must require the same canonical scopes as the concrete Hermes mutations it will perform and must produce an explicit preview before execution.

R1 SHOULD NOT expose `commit_and_dispatch`.

By default, newly materialized tasks must be created in a non-dispatchable planning state (prefer TRIAGE) unless a separate, explicit workflow transition is confirmed afterwards. Materializing a plan must not unexpectedly spawn workers.

## 7. Commit protocol

1. Read exact proposal revision.
2. Validate internal graph, fields, profile/skill/model references, bounds, and cycle policy.
3. Re-read affected canonical state.
4. Compare against `base_snapshot`.
5. Produce deterministic commit preview:
   - new canonical cards;
   - proposed patches;
   - new/removed dependency edges;
   - skipped/invalid items;
   - exact canonical scopes/capabilities required by each operation;
   - expected post-commit non-dispatchable states.
6. Require explicit user confirmation of that exact revision/preview.
7. Execute a bounded canonical mutation sequence.
8. Read back every materialized task/edge.
9. Persist exact draft->canonical mapping and outcome.
10. Mark committed subset and create a new proposal revision if uncommitted draft work remains.

No optimistic UI success before canonical readback.

## 8. Partial commit

Partial commit is a first-class use case.

The user may select a subset of draft cards/branches and commit only that subset if the dependency closure is valid. R1 defines valid closure as the selected draft set plus every unresolved draft ancestor required for those selected nodes to be well-formed at materialization time. Already-canonical ancestors satisfy the closure without adding draft work. Draft descendants are never pulled in automatically. If a required draft ancestor is explicitly excluded by the user, the partial commit fails rather than widening the subset silently.

The server must compute and display:

- requested subset;
- required draft ancestors/dependencies;
- already-canonical dependencies;
- excluded descendants;
- invalid cross-boundary references.

The server must never silently add material draft work beyond the previewed dependency closure.

After partial commit, the proposal status becomes `partially_committed` and later revisions may refer to the resulting canonical IDs through the persisted mapping.

## 9. Kanban and Dependencies views

Proposal Workspace must work in both board modes.

### Kanban

- ghost cards coexist with canonical cards;
- draft status is visibly distinct from canonical status;
- sort is presentation-only;
- user may edit/reorder draft cards without changing canonical priority unless an explicit priority proposal is created.

### Dependencies

- canonical edges: solid lines;
- proposed new edges: dashed lines;
- proposed removed edges: muted/struck/dashed-red semantic treatment;
- mixed canonical/draft DAGs are supported;
- selecting nodes updates the same workspace selection context used by chat.

## 10. Model/profile/skill references

Proposal cards may contain intended profile, skills, provider, and model choices.

These values should be validated against the canonical read-only catalogs planned by the observability line, not hard-coded in the widget.

A proposal may temporarily contain unresolved values while editing, but `proposal_validate` and `proposal_commit` must distinguish:

- valid and currently resolvable;
- syntactically valid but unavailable;
- unknown/stale;
- authority-incompatible.

The UI should provide autocomplete and skill browsing from the same canonical catalogs ChatGPT uses.

## 11. Context economy

Do not inject the full proposal into every model turn.

The model context handoff should normally include only:

- active proposal ID;
- exact revision;
- selected refs;
- optional short proposal goal;
- UI view/mode when materially relevant.

ChatGPT retrieves proposal details on demand through MCP.

This keeps conversation context separate from proposal state and makes the proposal recoverable after context compaction.

## 12. Host capability fallback

MCP Apps host support for model-context updates and follow-up behavior must be validated in real ChatGPT E2E.

The design must remain functional if the host does not retain widget-updated model context reliably:

- selection and active proposal are persisted server-side with bounded TTL;
- ChatGPT can call `proposal_selection_get` / `proposal_get`;
- the widget can show whether chat-context synchronization is `CONNECTED`, `PARTIAL`, or `UNAVAILABLE` rather than pretending it succeeded.

## 13. Security and authority

- Proposal editing has no canonical side effects.
- Proposal selection grants no write authority.
- Proposal commit requires exact authenticated user authority and canonical write scopes.
- No Human Gate is implicitly satisfied by proposal approval.
- A proposal cannot authorize deploy, restart, protected merge, OAuth changes, destructive deletion, or other dangerous operations.
- Such operations, if ever represented as plan nodes, remain descriptive/non-executable until their own existing authority path is satisfied.
- Proposal storage must not contain tokens, secrets, raw environment dumps, or unrestricted worker logs.

## 14. Observability

Record bounded events for:

- proposal created;
- revision created;
- selection changed (coalesced/bounded; avoid high-frequency pointer noise);
- validation result;
- commit preview generated;
- commit confirmed/rejected;
- materialization mapping;
- conflict/rebase;
- discard/expiry.

Proposal telemetry must distinguish user edits, ChatGPT edits, and canonical commit operations.

## 15. Failure semantics

Explicit error classes should include:

- `PROPOSAL_NOT_FOUND`
- `PROPOSAL_EXPIRED`
- `REVISION_CONFLICT`
- `BASE_STATE_CONFLICT`
- `INVALID_DRAFT_GRAPH`
- `UNRESOLVED_CAPABILITY`
- `COMMIT_AUTHORITY_REQUIRED`
- `PARTIAL_COMMIT_INVALID_CLOSURE`
- `MATERIALIZATION_PARTIAL_FAILURE`

A partial materialization failure must return exact completed/failed operations and canonical readback. It must never report the proposal as fully committed without proof.

## 16. E2E acceptance scenarios

### E2E-PW-01 Chat plan -> visible draft
ChatGPT creates a proposal with 5 draft cards and dependencies. The widget renders them without creating any Hermes tasks.

### E2E-PW-02 Visual edit -> chat understanding
User renames one draft, creates another, changes an edge, selects two cards, then says in chat: "divide estas dos". ChatGPT resolves the exact active proposal revision and selection without guessed IDs.

### E2E-PW-03 Context loss recovery
After connector/widget refresh, ChatGPT retrieves the active proposal + selection from MCP and continues from the exact revision.

### E2E-PW-04 Concurrent revision conflict
Two stale edits target the same proposal revision. The second fails with `REVISION_CONFLICT`; no silent merge.

### E2E-PW-05 Canonical drift
A referenced canonical card changes after proposal review. Commit fails `BASE_STATE_CONFLICT` with bounded diff.

### E2E-PW-06 Partial commit
User selects a valid dependency-closed branch. Only previewed cards/edges materialize; mapping is returned; remaining proposal stays editable.

### E2E-PW-07 No surprise dispatch
Committing a plan creates non-dispatchable canonical cards and no worker starts.

### E2E-PW-08 Authority separation
Selecting cards or approving a proposal does not satisfy unrelated Human Gates or dangerous-operation authorization.

### E2E-PW-09 Mobile shared selection
Long-press multi-select in the mobile board updates bounded selection context and subsequent chat reference resolves exactly those cards.

### E2E-PW-10 Host context unavailable
With model-context synchronization unavailable, server-side proposal/selection recovery still allows exact chat references.

## 17. Delivery sequence

Recommended implementation order:

1. Proposal store + revision/concurrency model.
2. Read/write draft MCP primitives with no canonical mutations.
3. Kanban ghost overlay + visual editing.
4. Shared selection server fallback.
5. ChatGPT host model-context E2E experiment.
6. Validation + conflict/rebase surfaces.
7. Preview-only materialization.
8. `proposal_commit` with TRIAGE-only materialization and canonical readback.
9. Partial commit.
10. Dependencies-view overlay/parity.
11. Independent adversarial review and real ChatGPT dogfood.

Do not implement dispatch-on-commit in R1.

## 18. Non-goals for R1

- replacing Hermes Kanban canonical storage;
- arbitrary real-time collaborative editing between multiple human users;
- unbounded graph editors;
- automatic worker dispatch after proposal approval;
- using conversation memory as proposal persistence;
- silently converting proposal approval into release/deploy/Human Gate authority;
- treating the proposal UI as the source of truth for model/profile/skill catalogs.

## 19. Success criterion

Proposal Workspace R1 is successful when a user can move continuously between conversation and visual planning while preserving exact referents and authority boundaries:

`CHATGPT PLAN -> EDITABLE VISUAL DRAFT -> USER/CHAT ITERATION -> EXACT REVISION CONFIRMATION -> CANONICAL NON-DISPATCHABLE HERMES PLAN`

with no canonical mutation before confirmation and no need to paste task IDs back into chat.
