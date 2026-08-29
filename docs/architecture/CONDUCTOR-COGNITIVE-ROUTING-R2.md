# Conductor Cognitive Routing R2

Status: CANDIDATE ARCHITECTURE — not active policy
Date: 2026-08-30
Repository: `arumihsnek/hermes-chatgpt-mcp`
Baseline: remote `main` observed at `fd0286c27d8fb223188bcb7a98ffe4419e060c14`
Supersedes: `CONDUCTOR-COGNITIVE-ROUTING-R1.md` as the current routing candidate; R1 remains historical evidence

## Purpose

Define a bounded architecture for splitting Hermes project cognition across:

1. a fast, interactive ChatGPT Chat conductor;
2. an optional agentic cognitive coprocessor for reusable procedural work;
3. Hermes tasks for durable units of responsibility.

The objective is not to maximize autonomy. The objective is to maximize verified
outcome quality per unit of model/credit cost, operational risk, context load and
human attention while preserving Hermes as the stable control plane.

This document is a candidate architecture and evaluation contract. It does not
activate a new runtime, grant authority, promote a model, install a skill, or
satisfy a Human Gate.

## Non-goals

This specification does not:

- replace Hermes/Kanban with ChatGPT Work, Codex, or another agent runtime;
- make any direct agent output canonical project state;
- authorize direct write access to Hermes from an experimental coprocessor;
- require every planning thought to become a Kanban card;
- require every durable task to run on Codex;
- freeze a model name, reasoning tier, pricing ratio, or product capability as a
  permanent governance rule;
- create a new MCP/control plane when an existing narrow primitive is sufficient;
- allow the author of a material change to count as its independent reviewer.

## Core topology

```text
Human
  |
  v
ChatGPT Chat
interactive conductor / brainstorming / routine control
  |
  | bounded delegation when procedural depth is useful
  v
Agentic cognitive coprocessor
Work Cloud leading candidate; local and Codex variants evaluated
  |
  | returns non-authoritative candidate
  v
ChatGPT Chat
accept / challenge / refine / decide
  |
  | authorized canonical operations
  v
Hermes
board / DAG / tasks / runs / evidence / reviews / gates
  |
  +--> durable workers and reviewers
```

Hermes remains the canonical source for mutable workflow state. The coprocessor
is a system under test and must remain isolatable from the stable control plane.

## Three execution lanes

### Lane A — Chat interactive control

Use Chat as the default human-facing conductor for work whose value comes from
rapid iteration rather than long autonomous execution.

Typical work:

- divergent brainstorming;
- quick architecture discussion and trade-offs;
- routine board pulse and controller decisions;
- small canonical Hermes mutations after evidence is sufficient;
- deciding whether a deeper planning/recovery/review pass is justified;
- challenging a returned plan candidate;
- keeping the human in the decision loop.

The Chat conductor should retrieve the minimum live state required for the next
decision and should not compensate for missing workflow primitives by loading a
large repository or replaying the entire project history.

### Lane B — Ephemeral cognitive coprocessor

Use an agentic coprocessor for a bounded cognitive subroutine of the conductor.
Its result is a candidate, not canonical project state.

Typical work:

- compile a mature idea into a plan candidate;
- propose a DAG, slices and dependencies;
- derive acceptance criteria and evidence requirements;
- perform bounded adversarial critique;
- inspect a repository or local artifacts to answer an architecture question;
- audit an evidence package without issuing the final authority decision;
- perform a deep controller/recovery assessment;
- compare alternative mechanisms before a durable task is opened.

Default safety posture:

- read-only or least-authority access;
- bounded objective and context;
- explicit candidate output;
- no silent Hermes mutation;
- no claim that project work is complete merely because the analysis completed;
- no self-activation of a specification, policy, release or Human Gate.

This lane is "thinking as a tool". Its lifecycle should normally end when the
candidate is returned to the Chat conductor.

### Lane C — Hermes durable work

Use a Hermes card when the work is an independent unit of responsibility rather
than an intermediate thought.

A card is preferred when one or more of the following are material:

- persistence across conversations or failures;
- ownership/assignee identity;
- dependencies or downstream consumers;
- retries, recovery or BLOCKED state;
- a material artifact or evidence package;
- independent review;
- provenance that another task/release consumes;
- a Human Gate or release chain;
- a result that must be durable even if the human-facing Chat ends.

The card may internally use any runtime that has a supported, authorized invocation path and has been validated for the task. Today, programmable Codex variants are concrete comparison candidates; Work Cloud card execution remains `NOT_PROVEN` until a supported programmatic surface exists. A future validated Work Cloud bridge could become a card runtime without changing the card's canonical Hermes lifecycle semantics.

## Boundary rule: ephemeral cognition vs durable work

The routing decision is semantic, not implementation-specific.

Use the ephemeral lane when the question is effectively:

> "Help the conductor think well enough to decide the next canonical action."

Use a Hermes card when the question is effectively:

> "Own this unit of project work and leave durable evidence/results for other
> work to depend on."

Do not create Kanban lifecycle for every intermediate model thought. Conversely,
do not use an ephemeral agent call to evade ownership, dependency, review,
evidence or gate semantics that a real project task requires.

## Candidate harnesses

Work Cloud is the leading default hypothesis for procedural conductor/planner work, but R2 does not declare a universal winner before same-scenario evaluation. The following surfaces are candidates for different slices.

### 1. Work Cloud — leading procedural-coprocessor candidate

Why it is the leading candidate for planning/review/deep-control experiments:

- Work is designed for longer multi-step work rather than only quick conversation;
- Cloud Work can start from a ChatGPT Project and use that Project context;
- cloud threads synchronize across web, mobile and desktop, avoiding dependence on one workstation;
- eligible skill workflows can encode reusable procedures instead of repeatedly reconstructing them from prose;
- the conductor role usually needs Hermes/GitHub/connected evidence rather than direct local filesystem ownership;
- avoiding local execution reduces machine affinity and accidental coupling between the conductor and a mutable checkout.

Important caveat: this architecture does **not** assume that Chat can programmatically invoke a Work Cloud thread. A human-started Work Cloud session, a scheduled Work task, and an invokable RPC/tool primitive are different capabilities. A direct Chat-to-Work-Cloud bridge remains `NOT_PROVEN` until a supported, authorized control surface is observed and tested.

Skill availability and connector/tool availability must also be verified on the target account/product surface; they must not be inferred merely from generic product documentation.

### 2. Work Local — comparison/fallback, not preferred

Work Local remains a valid comparison surface when a task genuinely requires direct access to local files or desktop applications. It is not the default conductor/planner path because the desired architecture prefers cloud continuity, machine independence and canonical retrieval through Hermes/GitHub/GPT-Hermes-like evidence surfaces.

Use Work Local only when the same scenario demonstrates a material advantage that cannot be obtained safely through cloud-connected evidence or a durable worker. Do not select it merely because a local checkout happens to exist.

### 3. Direct GPT-Hermes Codex primitive

The current GPT Hermes surface exposes narrow Codex-oriented primitives that can
represent an invokable cognitive subroutine more directly than a human-started
Work session.

Potential advantages:

- programmatic invocation;
- bounded job lifecycle;
- explicit result retrieval;
- natural fit for read-only plan/review calls;
- runs near the OCI repository/runtime when enabled.

This is an existing primitive and therefore should be evaluated before creating
another MCP or daemon.

### 4. Codex app-server

Candidate when a persistent programmable Codex session/server provides better
control, session continuity or structured invocation than one-shot CLI calls.

It should be evaluated for:

- lifecycle and session isolation;
- tool/skill loading;
- cancellation and observability;
- context reuse;
- failure recovery;
- authority boundaries;
- ease of wrapping behind a typed high-level primitive.

Current upstream documentation describes `codex app-server` as the programmable interface behind rich Codex clients, with typed thread/turn lifecycle, approvals, skills, apps, review and command execution. That makes it the strongest Codex candidate when a persistent machine-invokable cognitive service is required. It still must not be treated as equivalent to Work Cloud: the two products expose different context, UX and orchestration semantics.

### 5. Codex CLI / `exec` / exec-server

Candidate for simple, scriptable, bounded invocations where a persistent agent server is unnecessary. `codex exec` is the one-shot/non-interactive form; `codex exec-server` is a lower-level JSON-RPC process-execution service and should not be confused with the agentic app-server.

Potential strengths:

- low integration complexity;
- easy sandbox/workdir binding;
- deterministic process lifecycle;
- natural fit for repository-local technical analysis.

Potential weaknesses for conductor planning:

- less Project/Work semantic context;
- more prompt/harness plumbing;
- risk of using a software-development-specialized interface for primarily
  workflow/decision work.

### 6. Hermes card -> Codex runtime

This is not a competitor to the ephemeral lane; it is the durable-work form.

When the same model, skill and relevant context are used, the core model cost of
an equivalent direct invocation and card execution should be of the same order.
The card adds task-contract, lifecycle, evidence and possibly review overhead.
That overhead is waste for a disposable intermediate thought, but is valuable
and often globally cheaper when persistence, retries, ownership or downstream
provenance are required.

## Provisional selection rule

Choose by semantic need, not by product branding:

1. **Work Cloud + skill** when the job is long, procedural, Project-context-heavy, and can be started/continued through the supported Work surface. This is the leading quality/efficiency hypothesis for planning, deep sweep and procedural review.
2. **Codex app-server** when the controller requires a persistent, machine-invokable agentic service with structured thread/turn lifecycle, skills, approvals, review, cancellation or rich observability.
3. **Direct GPT-Hermes Codex primitive / `codex exec`** when a one-shot bounded programmatic analysis is enough and app-server continuity would be unnecessary overhead.
4. **Hermes card -> runtime** when the unit of work must be durable: ownership, dependencies, retries, BLOCKED state, artifacts/evidence, downstream consumption or independent review matter. The runtime may be Codex today or another validated runtime later; the card lifecycle is the semantic requirement.
5. **Work Local** only when direct local/desktop state provides a demonstrated material advantage that cannot be obtained through cloud-connected evidence or a durable worker.

The preferred cognitive surface and the preferred invocable surface may differ. Work Cloud can be the leading cognitive candidate while a supported programmatic bridge remains `NOT_PROVEN`; in that case app-server/direct Codex can be the best automation substrate without becoming the preferred human-facing planner.

## Comparison dimensions

Evaluate harnesses on the same scenario where semantically valid.

| Dimension | Why it matters |
|---|---|
| Verified acceptance | A cheap wrong plan is not efficient. |
| Credit/token cost | Weekly-pool efficiency when observable. |
| Context volume | Measures duplicated/reloaded state. |
| Latency | Critical for interactive loops. |
| Human intervention | Measures orchestration burden. |
| Skill/procedure fidelity | Whether reusable procedure is actually followed. |
| Project-context access | Avoids rebuilding stable context manually. |
| Local/OCI state access | Matters for repo/runtime evidence. |
| Programmability | Determines whether Chat can call it as a tool. |
| Isolation | Prevents candidate runtime from becoming the control plane. |
| Observability | Needed to classify failures and compare runs. |
| Lifecycle overhead | Cards are intentionally heavier than ephemeral calls. |
| Evidence quality | Determines whether downstream decisions are safe. |
| Retry/recovery behavior | Important for long agentic work. |
| Authority surface | Lower authority is preferred unless writes are required. |

No single harness is expected to dominate every row.

## References versus skills

Project references and skills have distinct roles.

### Project references

Use references for stable facts and governing semantics, for example:

- canonical board/repositories;
- canonical-source hierarchy;
- authority and side-effect rules;
- evidence labels;
- Human Gate semantics;
- stale-candidate protections;
- stable control-plane requirements.

They answer: **what is true and what rules govern the project?**

### Skills

Use skills for reusable procedures whose repeated execution should become more
consistent, for example:

- how to compile a Hermes plan;
- how to review an evidence package;
- how to perform a deep conductor sweep;
- how to run a metaworkflow experiment.

They answer: **what procedure should the agent execute now?**

A skill must not silently weaken or replace the governing references.

## Skill candidates

Priority is provisional and subject to evaluation.

### `hermes-planner` — first candidate

Expected procedure:

1. recover the minimum live state relevant to the design;
2. semantically rediscover the current generation of affected work;
3. deduplicate against existing remediation/incidents;
4. classify the narrowest responsible mechanism;
5. define bounded slices and acceptance criteria;
6. construct dependencies/DAG;
7. identify required capabilities/profile intent;
8. specify evidence and review requirements;
9. identify authority/gate constraints;
10. return a structured plan candidate;
11. validate that the candidate does not rely on stale IDs, heads or gates.

The skill should normally return a candidate to the conductor. It should not
silently create cards unless the invocation explicitly grants that authority and
the experiment has reached an approved rollout stage.

### `hermes-review`

Reusable independent-review procedure covering candidate identity, acceptance
criteria, evidence inspection, missing evidence, adversarial checks and explicit
epistemic verdict.

### `hermes-conductor`

Reserved initially for deep sweeps, recovery and complex cross-front analysis,
not every routine board pulse. Routine control is frequent enough that a heavy
agentic path may waste weekly pool and latency.

### `hermes-metaworkflow-eval`

Encodes baseline -> intervention -> same-scenario comparison -> independent
review and telemetry collection for changes to prompts, skills, profiles,
models, harnesses or routing.

### Brainstorming skill

Low priority. Divergent brainstorming benefits from flexibility and rapid human
interaction; a prescriptive workflow can reduce useful search-space diversity.

## Routing hypotheses

These are falsifiable hypotheses, not active policy.

### Brainstorming

Prefer Chat for divergent, human-interactive exploration. Escalate to an agentic
surface only when a bounded deep research/analysis pass is worth the extra
latency and pool use.

### Design convergence / formal planning

A skill-capable Work Cloud configuration is the leading candidate because the work is procedural, multi-step, can use Project context, and avoids binding the conductor to one workstation or checkout. It must be compared against Chat-only, Work Local only where locality is genuinely useful, and programmable Codex variants.

### Routine interactive controller

Prefer Chat for frequent short loops: board pulse, inspect one run, decide,
mutate Hermes, report. Escalate only when ambiguity or cross-front complexity
makes a deeper procedural sweep worthwhile.

### Deep controller sweep / recovery

Prefer an agentic skill-driven candidate in SHADOW first. The agent returns a
structured assessment; Chat/Hermes retains canonical mutation authority during
early rollout.

### Material review

Use an independent reviewer/harness when material. Skill-driven review is a good
candidate because the procedure is strict and repeatable. Author and independent
reviewer must remain distinct where required.

## Model-routing hypotheses

Model/provider/reasoning tier are experiment dimensions, not governance.

Current working hypotheses to test include:

- a Sol-class higher-capability Chat model for interactive brainstorming,
  ambiguity resolution and fast controller dialogue;
- a Luna-Max-class, skill-driven agent for long procedural planning where lower
  token pricing can offset greater deliberation;
- escalation to more expensive models only when same-scenario evidence shows a
  meaningful quality benefit.

Do not encode contemporary benchmark scores, temporary pricing or model names as
permanent authority rules. Record them in time-bounded experiment evidence.

## Cost model: direct call versus card

For equivalent model/skill/context, direct and card-based execution should have
similar core inference cost. They are not globally equivalent because they buy
different lifecycle properties.

Approximate conceptual accounting:

```text
direct cost
= inference + tool/context cost

card cost
= inference + tool/context cost
+ task contract/lifecycle/evidence/review overhead
```

The additional card overhead is justified when durability is required. For an
intermediate plan thought, it can be pure board pollution. Efficiency must be
measured as verified project outcome per total cost, not tokens alone.

## Current runtime snapshot — non-normative

Observed via GPT Hermes at approximately `2026-08-29T22:16Z`:

- Codex CLI was present as `codex-cli 0.150.1` on the OCI;
- GPT Hermes exposed `codex_plan`, `codex_start`, job/status/result and review
  primitives;
- `hermes_codex_status` reported `codex_available=true` but
  `enabled=false` and `write_enabled=false`;
- the live Hermes profile registry did not contain a profile literally named
  `codex-runtime`;
- the GPT Hermes mission surface reported historical native Codex sessions.

These observations are deliberately stale-by-design. Re-query the appropriate
canonical runtime source before any operational decision.

## Product-surface observations — time-sensitive

As of 2026-08-30, OpenAI documentation describes:

- Chat as the fast conversational surface;
- Work as the longer multi-step agentic surface;
- Work Cloud as the cloud-native multi-step surface, able to start from Project context and synchronize across web, mobile and desktop;
- Work Local in the desktop app as able, when permitted, to use local files/apps, but not preferred by this candidate architecture unless locality proves necessary;
- Codex as a separate software-development-focused surface;
- Work and Codex as following the same broad usage structure;
- skills as reusable workflows that may include instructions, examples and code,
  with actual availability dependent on account/surface/plugin support.

These are product observations, not project authority rules. Revalidate them
before relying on them in future routing decisions.

Time-sensitive source anchors used for R2:

- OpenAI Help, `ChatGPT Work and Codex`: https://help.openai.com/en/articles/20001275/
- OpenAI Codex `app-server` README: https://github.com/openai/codex/blob/main/codex-rs/app-server/README.md
- OpenAI Codex `app-server-daemon` README: https://github.com/openai/codex/blob/main/codex-rs/app-server-daemon/README.md
- OpenAI Codex non-interactive `exec` documentation/source: https://github.com/openai/codex/blob/main/codex-rs/README.md

## Integration preference order

When implementing the coprocessor boundary, prefer the narrowest mechanism that
meets the requirement:

1. supported Work Cloud product primitive, if an actually invokable and authorized surface is proven;
2. reusable skill on the selected agentic surface for procedure;
3. existing GPT Hermes bounded primitive when a machine-invokable one-shot path is sufficient;
4. narrow typed wrapper around an existing primitive;
5. Codex app-server when persistent machine invocation, structured lifecycle, skills or richer observability are required;
6. Codex CLI/`exec`/exec-server for narrower or one-shot technical invocation;
7. distinct profile only when identity/capability/isolation warrants it;
8. new MCP/subsystem only when lower layers cannot express the requirement.

A likely future typed primitive, if justified, is conceptually
`plan_candidate(...)`, not a second control plane.

## Evaluation plan

### Scenarios

Use the same real or faithfully replayable scenarios across applicable variants:

1. mature idea -> plan/DAG candidate;
2. ambiguous blocked flow -> recovery assessment;
3. material evidence package -> review candidate;
4. routine controller pulse -> next-safe-action decision;
5. planning request that should conclude "no new card needed";
6. durable research task that clearly does require a card.

### Variants

At minimum compare:

- Chat-only baseline using Project instructions/references;
- Chat -> Work Cloud with candidate skill, when skill and invocation semantics are available on the target surface;
- Work Local only as a locality-required comparison/fallback;
- Chat -> direct Codex primitive or equivalent programmable invocation;
- Codex app-server, CLI `exec`, and exec-server as technically distinct programmable surfaces;
- Hermes card -> Codex runtime for scenarios that legitimately require durable
  work.

Do not force a card variant onto a scenario whose semantic requirement is only
an intermediate thought; that would bias the experiment by changing the task.

### Metrics

Capture when observable:

- acceptance result and independent-review verdict;
- unsupported PASS or stale-state error count;
- context/token/credit cost;
- latency/runtime;
- number of tool calls;
- retries/reclaims;
- human interventions;
- evidence completeness;
- board cards created solely as orchestration overhead;
- duplicated state/context retrieval;
- unsafe action attempts prevented;
- downstream rework caused by the plan.

### Causal discipline

Use the same scenario and change one important variable at a time where practical.
Do not conclude that one harness is cheaper or smarter from unrelated tasks.

## Rollout

### SHADOW

The coprocessor observes/analyzes and returns candidates. Chat/Hermes performs
all canonical decisions and mutations.

### ASSISTED

Permit bounded low-risk compilation or card preparation after the candidate has
shown repeatable benefit. Maintain explicit fallback to the Chat-only path.

### PRIMARY

Use as the normal route only after same-scenario evidence, independent review and
operational dogfood demonstrate better verified outcome quality per total cost.

### RETIREMENT

If the skill/harness path proves reliable, remove redundant prompt prose,
wrappers, duplicate profiles or obsolete cards. Improvement should reduce
complexity as well as add capability.

## Acceptance criteria for this candidate spec

This architecture candidate is ready for independent review when:

- ephemeral cognition and durable work are explicitly distinguished;
- Work Cloud is treated as the leading procedural candidate without assuming a programmatic invocation surface;
- Work Local is explicitly secondary and requires a demonstrated locality advantage;
- Codex app-server, CLI/exec, direct primitives and card-based Codex are treated
  as alternatives with different integration/lifecycle properties;
- Hermes remains the stable canonical control plane;
- Skills and Project references have distinct responsibilities;
- model/pricing statements are hypotheses or timestamped observations;
- runtime observations are explicitly non-normative and stale-by-design;
- the evaluation compares same scenarios and includes total workflow cost;
- no release, merge, deployment or Human Gate authority is implied.
