# Upstream-Native Workflow and Generic Device Owner Direction

**Status:** CANDIDATE DIRECTION — analysis only, not active architecture  
**Date:** 2026-09-03  
**Scope:** Hermes ChatGPT MCP / Hermes control-plane evolution  
**Decision class:** CORE if adopted; adoption requires independent review, real boundary evidence, and explicit Human Gate approval.

## 1. Purpose

This document records an architectural direction developed from current Hermes dogfood, the existing `hermes-chatgpt-mcp` integration model, and a focused investigation into remote sysadmin / SSH MCP backends usable from ChatGPT Web.

It is deliberately **not** an implementation plan, migration handoff, or statement of current runtime truth.

The purpose is to preserve the reasoning behind two related simplification hypotheses:

1. Hermes workflow should use upstream-native Kanban primitives much more directly instead of maintaining parallel Mission / Outcome / dogfood abstractions when native boards, orchestration cards, TRIAGE, DAGs, runs, reviews, attachments, artifacts, and tenants already express the required semantics.
2. Generic host ownership should stop being a large bespoke responsibility of GPT Hermes when a generic Device Owner / SSH backend can perform filesystem, shell, process, service, local-Git, and similar operations behind a narrow Hermes adapter.

The intended outcome is **less custom architecture**, not a larger replacement framework.

---

## 2. Executive direction

The preferred long-term shape is:

```text
                         ChatGPT
                            │
              ┌─────────────┴──────────────┐
              ▼                            ▼
       Hermes Control                    GitHub
              │
       ┌──────┴────────┐
       ▼               ▼
 Kanban / workflow   Hermes-specific admin
       │
       │ typed effects
       ▼
 DeviceOwnerAdapter
       │
       ▼
 generic sysadmin backend
 (initial candidate: ssh-mcp)
       │
       ▼
      OCI / managed hosts
```

This means:

- **Kanban remains the durable workflow/control plane and scheduler.**
- **GitHub remains the independent authority for remote branches, PRs, checks, merge state, and remote provenance.**
- **Generic host effects become replaceable infrastructure.**
- **Hermes-specific administration remains Hermes-specific.**
- ChatGPT may eventually see one coherent Hermes control surface, but internally the system keeps multiple explicit owners.

It explicitly does **not** mean:

```text
one connector
=
one process
=
one authority
=
one source of truth
```

A simplified external control surface is desirable. A monolithic internal owner is not.

---

## 3. Why reconsider the current architecture

The current ecosystem has accumulated useful functionality through several surfaces:

- Hermes Kanban / Canary for durable workflow state;
- GPT Hermes for filesystem, shell, local Git, worktrees, service/runtime inspection, configuration, profiles, skills, and operator functions;
- GitHub for independent remote provenance;
- custom Mission, Human Gate, evidence, incident, dogfood, and governance conventions around those systems.

This architecture works, but it carries increasing overlap.

Examples:

- Mission identity overlaps with an upstream orchestration/root card that remains alive across decomposed child work.
- Mission generations overlap with card DAGs, retries, remediation, and repeated execution attempts.
- custom dogfood intake overlaps with upstream TRIAGE.
- durable supporting documents overlap with attachments and artifacts.
- generic GPT Hermes filesystem/shell/runtime tools overlap with generic remote sysadmin capability.
- local Git and remote GitHub provenance are both called “Git” operationally even though they are different state dimensions and should have different owners.

The risk is not only code duplication. It is **semantic duplication**.

Each parallel abstraction adds:

- another identity;
- another lifecycle;
- another translation layer;
- another tool schema;
- another migration problem;
- another place where ChatGPT must remember routing rules;
- another opportunity for live state and remembered state to diverge.

The desired correction is therefore:

> Prefer the narrowest upstream/native primitive that already owns the concern; keep a custom extension only when a concrete governance or authority gap remains.

---

## 4. Design principles

### 4.1 Upstream where possible

Hermes should consume upstream improvements directly instead of reproducing them in a parallel local framework.

Examples include future improvements to:

- decomposition;
- card lifecycle;
- goal iteration;
- reviews;
- artifacts;
- events;
- workers;
- dispatch;
- board behavior;
- retries and remediation.

### 4.2 Hermes-specific where necessary

Upstream alignment must not weaken governance.

Thin custom semantics remain justified for requirements such as:

- exact Human Gate binding;
- candidate identity / digest binding;
- protected activation authority;
- independent review requirements;
- release semantics;
- source-of-truth separation;
- evidence provenance;
- state-dimension correctness.

### 4.3 Generic infrastructure outside Hermes

Filesystem access, shell execution, process inspection, service management, local Git, package inspection, and generic host operations are not inherently Hermes concepts.

They should be provided by a generic backend where practical.

### 4.4 Authority remains explicit

A façade may route operations, but must not blur which subsystem owns each fact or mutation.

### 4.5 Reconstruct state; do not preserve mutable state in architecture docs

This document must never be used to infer current:

- task IDs;
- Mission IDs;
- worker/run IDs;
- Human Gate IDs;
- board counts;
- branches;
- SHAs;
- active profiles;
- installed package versions;
- service state;
- connector availability.

Those remain live-state facts and must be reconstructed from their current authority.

---

## 5. Native Kanban primitives as the default workflow model

A major conclusion from this analysis is that a new generic `Outcome` subsystem should **not** be introduced before proving that native cards cannot express the requirement.

A candidate semantic mapping is:

| Framework concept | Preferred Hermes primitive |
|---|---|
| durable project/domain boundary | Board |
| Mission / outcome identity | root orchestration card |
| plan materialization | child cards + DAG/dependencies |
| execution attempt | run |
| retry / remediation | new attempt or linked remediation card |
| verification | review |
| raw idea / unresolved input | TRIAGE |
| dogfood observation | TRIAGE card after minimal dedupe |
| input/context document | attachment |
| produced evidence | artifact / durable attachment |
| collaboration / durable note | comment/activity |
| soft routing/data namespace | tenant |
| ingestion dedupe | idempotency key |
| bounded goal iteration | goal mode where appropriate |

The implication is significant:

> A root orchestration card can plausibly be the durable semantic object currently called a Mission.

---

## 6. Root orchestration card as Mission / outcome

The native shape is already close to the desired semantics:

```text
ROOT CARD
“Deliver governed web-specialist capability”
│
├── architecture
├── implementation
├── tests
├── adversarial review
├── real ChatGPT E2E
└── activation candidate
```

The root card carries the durable objective.

Its children represent the current decomposition of work.

Runs represent attempts.

Review and remediation can occur without changing the identity of the original objective.

Example:

```text
Root Card X
│
├── implementation attempt 1
│   └── review FAILED
│
├── remediation
│
├── implementation attempt 2
│   └── review PASS
│
└── activation verification
```

This should remain one durable outcome unless the semantic objective itself changes.

This avoids the tendency to create parallel identities such as:

```text
Mission X
Mission X-R1
Mission X-R2
Mission X-R3
```

when R1/R2/R3 are only execution generations or attempts.

### 6.1 Why this is preferable to a new Outcome object

A dedicated Outcome model can be attractive because it can encode obligations, constraints, plan generations, evidence, and completion policy.

But if the same semantics can be represented with native cards plus small metadata extensions, a new top-level object would add:

- a second durable work identity;
- a second lifecycle;
- new APIs;
- new migrations;
- new projections;
- permanent translation to upstream Kanban.

Therefore the correct sequence is:

```text
FIRST
native root card + DAG + runs + reviews + artifacts

THEN
identify concrete missing semantics

ONLY THEN
add the narrow missing extension
```

A future root-card model may still need a thin governed concept for obligations or protected completion. That should be demonstrated by real gaps rather than assumed in advance.

---

## 7. Board semantics

Boards should normally represent a durable **project, repository boundary where operationally independent, or workflow domain**.

A Board is therefore usually more durable than a Mission/outcome.

Good conceptual examples:

```text
hermes-chatgpt-mcp
profile-factory
hermes-free-model-fabric
hermes-web-consult
```

But “one repo = one board” should not be treated as a universal law.

The better question is:

> Does this work need shared dependencies, workers, evidence, graph visibility, and scheduling within one durable workflow domain?

If yes, it likely belongs on the same Board even if multiple repositories participate.

### 7.1 Why not Board = Mission by default

Using a Board for each Mission would create unnecessary hard isolation and likely lead to:

- board proliferation;
- fragmented dependency graphs;
- more navigation overhead;
- more databases/workspaces/log partitions;
- weaker reuse of native DAG semantics.

A Board should generally be a stable operating domain, not a disposable outcome instance.

---

## 8. TRIAGE as native intake and dogfood surface

TRIAGE is a particularly strong fit for dogfood and architecture intake.

Candidate flow:

```text
runtime/workflow observation
        │
        ▼
minimal deterministic dedupe
        │
        ▼
TRIAGE card
        │
        ├── duplicate → link/close
        ├── noise → close
        ├── needs human reasoning → remain TRIAGE
        ├── bounded work → specify
        └── larger objective → decompose
```

This could replace a substantial amount of bespoke dogfood-ledger behavior.

### 8.1 Important constraint

TRIAGE must not become an automatic work factory.

If an upstream configuration automatically decomposes TRIAGE cards, raw dogfood ingestion needs a safety mechanism such as:

- manual triage mode;
- an intake marker/type;
- deterministic dedupe/classification;
- or an explicit transition before decomposition.

Otherwise a transient observation can become duplicate or cosmetic work.

The project should preserve the invariant:

> Observing friction is not equivalent to authorizing remediation.

---

## 9. Tenant semantics

Tenant should remain a **soft namespace / filter / routing dimension**, not a substitute Mission identity and not a hard security boundary.

Potential valid uses include target or environment groupings such as:

```text
tenant=oci
tenant=surface
tenant=chatgpt
```

or, if consistent with upstream semantics:

```text
tenant=production
tenant=canary
tenant=development
```

Avoid using Tenant merely as:

```text
tenant=mission-123
```

if the only purpose is to recreate a Mission hierarchy through another field.

OS/security isolation must never rely on Tenant alone.

---

## 10. Attachments, artifacts, and evidence

Cards should carry more of their durable context natively.

A root card can be structured as:

```text
Root Card
│
├── body
│   ├── intent
│   ├── constraints
│   ├── success criteria
│   └── authority policy
│
├── attachments
│   ├── architecture.md
│   ├── requirements.md
│   └── external-input.pdf
│
├── artifacts
│   ├── benchmark.json
│   ├── test-report.md
│   └── candidate bundle
│
├── runs
├── reviews
└── comments/activity
```

The preferred semantic distinction is:

```text
Attachments = inputs/context
Artifacts   = produced outputs/evidence
```

where upstream supports it.

Evidence still needs exact bindings when material:

- board/card/run;
- candidate SHA/digest;
- attachment/artifact digest;
- checkout/worktree;
- local HEAD;
- remote PR/head;
- test command/result;
- reviewer/verdict;
- Human Gate.

Using native storage should reduce parallel document systems, but must not weaken provenance.

---

## 11. Human Gates remain a likely thin Hermes extension

Human Gates are one of the strongest cases for retaining Hermes-specific governance semantics.

A protected gate may require:

- exact candidate binding;
- exact evidence binding;
- fresh independent review;
- explicit human verdict;
- anti-self-approval guarantees;
- anti-completion semantics;
- inability for a worker to silently activate protected state.

If native card/review status cannot express these guarantees, Human Gate semantics should remain a thin extension **bound to native card/run/evidence identities**, not a competing workflow system.

A root card must not become semantically complete merely because all child execution cards have finished if a required Human Gate is unresolved.

---

## 12. Reframing GPT Hermes

GPT Hermes currently combines two substantially different responsibilities.

### 12.1 Generic Device Owner responsibilities

Examples:

- filesystem reads and writes;
- shell execution;
- workspace manipulation;
- process inspection;
- systemd/service status and control;
- logs/journal;
- local Git status/diff/commit operations;
- package operations;
- container runtime operations;
- generic host runtime inspection.

These are generic machine-management capabilities.

They are candidates to move behind a generic Device Owner backend once equivalence is proven.

### 12.2 Hermes-specific responsibilities

Examples:

- installed profiles;
- desired/effective profile resolution;
- skills;
- Hermes configuration semantics;
- Hermes environment resolution;
- gateway state;
- operator readiness;
- Hermes-specific fleet/peer concepts;
- Hermes credential/provider semantics where domain knowledge matters.

These should remain Hermes-specific.

The likely future is therefore **not** necessarily “delete GPT Hermes entirely.”

It is more plausibly:

```text
GPT Hermes today
│
├── generic owner layer       → progressively retire
└── Hermes-specific admin     → keep / thin / move to native Hermes admin
```

The end product may be a small Hermes Admin adapter rather than a broad second control plane.

---

## 13. Generic Device Owner research direction

A focused research pass examined current SSH/sysadmin MCP implementations specifically for use from ChatGPT Web, not only local clients such as Claude Desktop or editor-integrated MCPs.

The strongest candidate identified for a pilot was:

```text
tufantunc/ssh-mcp
```

A useful runner-up / design reference was:

```text
gbvolkov/sysadmin_mcp_kit
```

Other SSH MCP implementations were less attractive for this project because they exposed broad terminal power without an equivalent policy/audit model, or appeared insufficiently mature as a production Device Owner dependency.

This selection is time-sensitive and must be revalidated before implementation.

### 13.1 Why `ssh-mcp` is attractive

The researched implementation offers a useful combination of:

- SSH host profiles;
- one-shot command execution;
- background/persistent sessions;
- signal handling;
- SFTP;
- host/role policy;
- command classification;
- approvals;
- optional OPA integration;
- audit logging;
- telemetry;
- output limits;
- rate limiting;
- read-only modes.

That is a better starting point than building another bespoke remote shell wrapper.

### 13.2 Why it must not become the security authority

No lexical shell classifier can prove the semantic safety of arbitrary shell execution.

Aliases, shell functions, PATH changes, indirection, interpreters, symlinks, filesystem state, and equivalent command constructions make a command classifier unsuitable as the primary sandbox.

Therefore:

```text
ssh-mcp policy/classifier = defense in depth
Unix identity / ACL       = real execution boundary
sudoers                   = privilege boundary
network policy            = exfiltration boundary
Hermes gate               = workflow/release authority
```

This layering is a prerequisite, not an optional hardening detail.

---

## 14. Secure MCP Tunnel as the preferred transport direction

The OpenAI Secure MCP Tunnel materially improves the feasibility of a private Device Owner backend on OCI.

Instead of exposing a public MCP endpoint:

```text
Internet
   ↓
public reverse proxy
   ↓
public MCP
   ↓
OCI
```

a private topology can be used:

```text
ChatGPT
   │
OpenAI Secure MCP Tunnel
   │ outbound connection
   ▼
tunnel-client on OCI
   │
   ├── stdio backend
   ├── localhost backend
   └── private / Unix-socket backend
```

Benefits:

- no inbound MCP listener needs to be public for the pilot;
- transport complexity is reduced;
- backend identity and host permissions remain local;
- the pilot is easier to reverse;
- OAuth/public distribution can be deferred until it is actually required.

This does not remove the need for host authorization. It only narrows the network exposure.

Published ChatGPT product matrices and connector behavior change over time. The real authority for this project must remain **actual ChatGPT ↔ connector E2E evidence** rather than assumptions based on a generic product tier table.

---

## 15. Target Device Owner contract

Hermes should not expose the third-party backend schema directly as its long-term semantic contract.

Avoid:

```text
ChatGPT
   ↓
Hermes
   ↓
re-export all ssh-mcp tools unchanged
```

Prefer:

```text
Hermes semantic operation
        │
        ▼
DeviceOwnerAdapter
        │
        ├── MCP client → ssh-mcp
        └── another backend later
```

This preserves backend replaceability and prevents external tool naming, session semantics, and policy quirks from becoming permanent Hermes API.

### 15.1 Candidate semantic reads

A future Device Owner surface could remain small, for example:

```text
device_info(host)
list_dir(host, path, cursor?, limit?)
read_file(host, path, offset?, limit?)
stat_path(host, path)
process_list(host, filter?, cursor?)
service_status(host, service)
journal_query(host, unit?, since?, cursor?, limit?)
git_status(host, repo)
git_log(host, repo, limit?)
git_diff(host, repo, pathspec?)
```

### 15.2 Candidate bounded writes

```text
write_file(host, path, content, expected_sha256)
apply_patch(host, workspace, patch, expected_head?)
git_commit(host, repo, paths, message, expected_head)
```

Compare-and-swap style preconditions such as `expected_sha256` and `expected_head` are desirable because they reduce mutation against stale state.

### 15.3 Long-running operations

Do not make correctness depend on a long blocking tool call or a persistent PTY unless actual dogfood demonstrates the need.

Prefer an explicit job abstraction:

```text
job_start(...) → job_id
job_status(job_id)
job_output(job_id, cursor)
job_cancel(job_id)
```

### 15.4 Escape hatch

Unix is too rich to model completely as structured tools, so a bounded escape hatch is still useful.

Prefer an argv-oriented interface:

```text
exec(
  host,
  argv,
  cwd?,
  env?,
  timeout?,
  output_limit?
)
```

over a default unrestricted shell string such as:

```text
exec("sudo bash -c '...'")
```

A true shell capability can exist as a stronger explicit authority class.

---

## 16. Device Owner capability model

Avoid a single boolean such as:

```text
admin=true
```

Prefer orthogonal capability dimensions such as:

```text
host
workspace/path
filesystem.read
filesystem.write
exec.argv
exec.shell
session.interactive
service.read
service.write
process.read
process.signal
git.read
git.write
network.outbound
package.read
package.write
container.read
container.write
sudo
secrets.read
destructive
expires_at
effect_id
actor
root_card_id
run_id
max_runtime
max_output
```

The Device Owner must remain an execution layer, not a workflow system. These fields should carry authority and correlation context, not create another DAG or scheduler.

---

## 17. Security model and real sandbox

The most important security question is not:

> Can the command classifier recognize every dangerous spelling?

It is:

> If arbitrary computation executes as the Device Owner Unix user, what can that identity actually read, write, signal, reach, and escalate to?

Therefore the real sandbox should be built from:

- dedicated Unix identity;
- least privilege;
- explicit filesystem ownership/ACL;
- separate observer and writer identities where useful;
- exact sudoers rules;
- no unrestricted root shell;
- no broad credential access;
- network egress restrictions where justified;
- host-key pinning;
- bounded writable workspaces;
- output limits;
- timeouts;
- session TTL;
- tamper-resistant audit evidence.

The layered authority model is:

```text
ChatGPT confirmation
        │ UX safety
        ▼
Hermes authority / Human Gate
        │ workflow/release authority
        ▼
Device Owner policy
        │ execution authorization
        ▼
Unix identity / ACL / sudoers
        │ kernel-enforced blast radius
        ▼
Host
```

No layer should silently substitute for another.

---

## 18. Local Git and GitHub are different owners

The future architecture should keep a deliberate split:

```text
local checkout/worktree state
→ Device Owner
```

Examples:

- current local HEAD;
- worktree identity;
- local branch;
- `git status`;
- local diff;
- local commit creation.

Whereas:

```text
remote GitHub provenance
→ GitHub connector
```

Examples:

- remote branch/ref;
- PR head;
- PR state;
- CI/checks;
- merge state;
- remote commit provenance.

This is not redundant architecture. It is useful source separation.

Hiding GitHub behind a custom façade merely to reach “one connector total” would add maintenance without improving authority clarity.

---

## 19. Architecture options considered

### Option A — Current dual surface

```text
ChatGPT
├── Hermes Kanban
├── GPT Hermes
└── GitHub
```

**Strengths**

- already operational;
- broad coverage;
- established authority split;
- proven runtime behavior.

**Weaknesses**

- GPT Hermes contains substantial generic plumbing;
- large tool surface;
- duplicated semantics;
- high custom maintenance burden.

**Assessment:** preserve as baseline during evaluation.

---

### Option B — Kanban + visible generic Device Owner

```text
ChatGPT
├── Hermes Kanban
├── Device Owner
├── GPT Hermes
└── GitHub
```

Device Owner begins in SHADOW and later assumes selected generic operations.

**Strengths**

- easiest A/B comparison;
- clear failure attribution;
- independent rollback;
- backend capability gaps are visible.

**Weaknesses**

- temporarily larger tool catalogue;
- model can potentially bypass Kanban unless conductor policy is strong;
- duplicate execution paths during migration.

**Assessment:** best transition architecture.

---

### Option C — one visible Hermes control surface with isolated internal owners

```text
ChatGPT
├── Hermes Control
│   ├── Kanban
│   ├── Hermes Admin
│   └── DeviceOwnerAdapter
│        └── generic backend
└── GitHub
```

**Strengths**

- simpler model-facing semantics;
- centralized correlation and authority checks;
- backend replaceability;
- fewer duplicate public tools;
- internal owners remain separable.

**Risks**

- façade could accidentally become a second scheduler;
- authority boundaries could become hidden;
- poor implementation could couple independent availability domains.

**Assessment:** preferred long-term target if the control surface remains a thin semantic/effect router.

---

### Option D — monolithic Hermes owns everything

```text
ChatGPT
   ↓
Huge Hermes connector
   ↓
workflow + GitHub + shell + filesystem + runtime + root + everything
```

**Superficial benefit:** one connector.

**Actual cost:**

- large blast radius;
- poor failure isolation;
- duplicated GitHub capability;
- authority ambiguity;
- difficult auditing;
- high maintenance;
- strong internal coupling.

**Assessment:** reject.

---

## 20. Feasibility

### 20.1 Native Kanban workflow feasibility — HIGH

The required primitives already substantially exist:

- Board;
- root card;
- TRIAGE;
- decomposition;
- child DAG/dependencies;
- runs;
- reviews;
- attachments;
- tenant;
- idempotency;
- goal iteration.

The main unknown is not whether the primitives exist.

It is whether they can replace all current Mission semantics **without weakening governance**.

That requires real-workflow comparison, especially around:

- completion criteria;
- multiple attempts/generations;
- Human Gates;
- candidate binding;
- evidence projection;
- supersession.

### 20.2 Generic Device Owner feasibility — MEDIUM-HIGH

Reasons for confidence:

- mature-enough external SSH MCP candidates exist;
- Secure MCP Tunnel reduces networking complexity;
- generic host operations are separable by domain;
- GPT Hermes provides an existing baseline for A/B comparison.

Remaining uncertainties include:

- exact ChatGPT E2E behavior;
- persistent/background session recovery;
- confirmation/elicitation behavior;
- policy false positives/false negatives;
- hidden GPT Hermes edge capabilities;
- operational behavior under concurrent calls.

### 20.3 GPT Hermes reduction feasibility — HIGH for generic operations, MEDIUM for complete retirement

Generic host ownership is likely replaceable.

Hermes-specific administration still needs a domain-aware owner.

Therefore full GPT Hermes deletion is not the current architectural objective.

### 20.4 One visible Hermes surface — MEDIUM-HIGH

Technically straightforward, but only architecturally safe if:

- Kanban remains scheduler;
- Device Owner remains an effect executor;
- GitHub remains independent provenance;
- owners are routed rather than mirrored;
- degraded modes remain explicit;
- privileged bypasses fail closed.

---

## 21. Gains versus losses

| Dimension | Expected gain | Expected loss / cost |
|---|---|---|
| upstream compatibility | strong | less freedom to invent local semantics |
| long-term maintenance | lower | initial migration work |
| custom code | materially lower | thin adapters/extensions still required |
| cognitive load | lower in final architecture | temporarily higher during SHADOW |
| workflow coherence | higher | Mission/root-card equivalence must be proven |
| security | potentially higher through OS-scoped owner | new external backend dependency |
| failure isolation | high with separated backends | poor if façade becomes monolithic |
| upgradeability | higher | adapter compatibility must be maintained |
| dogfood handling | cleaner via TRIAGE | requires dedupe/decomposition discipline |
| evidence locality | better through cards/artifacts | large artifacts may still need external storage |
| source clarity | better if façade only routes | worse if it mirrors authoritative state |
| backend replaceability | higher | requires stable adapter contract |
| GitHub integration | stays native and independent | cannot claim literal one-connector total |
| near-term velocity | lower during pilot | expected long-term simplification |

---

## 22. Complexity versus robustness

### Current architecture

```text
visible complexity: medium-high
internal complexity: medium-high
robustness: high / proven
custom maintenance: high
```

### New custom Outcome framework + current GPT Hermes

```text
visible complexity: high
internal complexity: very high
robustness: uncertain
upstream divergence: high
custom maintenance: very high
```

This is the least attractive direction unless native primitives prove insufficient.

### Native Kanban + generic Device Owner

```text
transition complexity: high
steady-state complexity: medium
robustness potential: high
upstream alignment: high
```

### Monolithic single connector

```text
visible complexity: low
internal complexity: very high
blast radius: very high
failure isolation: poor
```

### Thin Hermes façade + isolated owners

```text
visible complexity: low-medium
internal complexity: medium
robustness potential: high
replaceability: high
authority clarity: high if implemented correctly
```

This currently offers the best expected long-term trade-off.

The governing principle is:

> Optimize for a simple external model plus explicit internal ownership, not a simple external model plus one internal owner.

---

## 23. Robustness and degraded operation

A future unified Hermes surface should not turn all components into one failure domain.

Expected degraded behavior should be explicit.

Examples:

```text
Device Owner unavailable
→ Kanban inspection remains available.

GitHub unavailable
→ local workflow remains inspectable; remote provenance is UNVERIFIED/BLOCKED.

Hermes Admin unavailable
→ workflow state remains available.

Kanban unavailable
→ protected durable mutations should generally fail closed rather than bypass workflow authority.
```

Potential control-plane modes:

```text
FULL
Kanban + Admin + Device Owner

DEGRADED_WORKFLOW_ONLY
workflow available, host effects unavailable

DEGRADED_READ_ONLY
state visible, protected mutations disabled

BLOCKED_EFFECTS
workflow present, execution backend unavailable
```

---

## 24. Device Owner pilot boundary implied by this analysis

This section records the **appropriate evaluation boundary**, not a committed implementation plan.

The first useful Device Owner candidate should be intentionally boring.

### Read-only initial capability

- host/system information;
- bounded filesystem reads;
- Git status/log/diff;
- process listing;
- service status;
- bounded journal/log reads.

### Initially excluded

- arbitrary sudo;
- root shell;
- persistent interactive PTY;
- SFTP upload;
- process signals;
- service restart;
- package mutation;
- container mutation;
- credential access;
- unrestricted network/port forwarding.

The first Unix identity should be a dedicated observer with no general sudo and no broad secret access.

A later writer should be a separate bounded identity rather than an observer silently upgraded into an administrator.

---

## 25. Explicitly dangerous capabilities

The following should not be part of the initial remote Device Owner authority:

- `sudo -i` or equivalent root shell;
- `NOPASSWD: ALL`;
- users/groups management;
- PAM changes;
- firewall changes;
- SSH daemon configuration;
- credential stores;
- `/root/.ssh` and equivalent private keys;
- raw block devices;
- kernel/module management;
- unrestricted sysctl;
- reboot/shutdown;
- unrestricted package removal;
- unrestricted Docker socket;
- privileged containers;
- arbitrary host port forwarding.

Any future inclusion requires a separately justified authority class and evidence.

---

## 26. Evidence required before replacing GPT Hermes capability

No generic GPT Hermes capability should be removed because a third-party MCP “supports the same command.”

Equivalence should include:

- successful real ChatGPT invocation;
- correctness;
- reliability;
- latency;
- bounded output behavior;
- timeout behavior;
- cancellation behavior;
- reconnection behavior;
- concurrent-call isolation;
- audit completeness;
- policy-denial correctness;
- secret-exposure resistance;
- host-key failure behavior;
- privilege-escalation resistance;
- operational recovery.

Useful A/B measures include:

```text
success rate
latency p50 / p95
tool calls
token / output volume
truncation
retries
reconnections
missing capability rate
policy false positives
unsafe false negatives
audit completeness
model confusion
fallback rate
```

Fallbacks should eventually be classified rather than silently routed, for example:

```text
missing_capability
transport_failure
policy_false_positive
session_failure
output_limit
hermes_specific
unexpected_backend_behavior
```

---

## 27. Migration maturity model

If this direction is adopted, the appropriate progression remains:

```text
SHADOW
   ↓
ASSISTED
   ↓
PRIMARY
   ↓
RETIRE OLD PATH
```

### SHADOW

GPT Hermes remains the current baseline/authority for generic owner behavior while the candidate backend is exercised and measured.

### ASSISTED

The Device Owner becomes preferred for a bounded set of reads and possibly approved workspace writes while GPT Hermes remains a classified fallback.

### PRIMARY

Generic host operations move to the Device Owner only after demonstrated equivalence and independent review.

### RETIRE OLD PATH

Generic GPT Hermes wrappers are removed only when their replacement is proven, observable, and reversible through a stabilization period.

This same maturity model can be used to compare Mission semantics with root orchestration cards.

---

## 28. Mission/root-card migration principle

Current Mission semantics should not disappear by assertion.

A safe conceptual comparison is:

```text
existing Mission semantics
        ↕
shadow projection
        ↕
root orchestration card + native graph
```

The comparison should determine whether native cards can explain:

- durable objective identity;
- active work generation;
- dependencies;
- retries/remediation;
- review state;
- evidence;
- unresolved gates;
- completion;
- supersession/abandonment.

Remaining Mission functionality should be classified as:

```text
DELETE
MAP TO UPSTREAM
THIN EXTENSION
KEEP
RESEARCH
```

The term **Mission** may remain a useful UX word even if the implementation becomes a root orchestration card. Naming and storage model need not be identical.

---

## 29. Expected long-term gains

### 29.1 Less accidental intelligence in the conductor

Today the ChatGPT conductor must often remember which connector owns which state dimension.

A future Hermes Control surface can resolve much of this mechanically without copying the underlying state.

### 29.2 Better upstream inheritance

Using native primitives means future upstream Kanban improvements are more likely to improve this system directly.

### 29.3 Better dogfood recursion

Workflow friction becomes normal TRIAGE work in the same workflow system rather than evidence stored in a separate meta-framework.

### 29.4 Smaller custom trust surface

Generic remote execution can use a separately hardened backend and Unix identity instead of being permanently coupled to the Hermes administration connector.

### 29.5 Replaceability

`ssh-mcp` can be replaced later if Hermes owns the semantic Device Owner contract rather than exposing the backend’s schema as public API.

---

## 30. Main risks and mitigations

### R1 — façade becomes a second scheduler

**Risk:** Hermes Control starts managing jobs/DAGs separately from Kanban.

**Mitigation:** Kanban remains the sole durable workflow scheduler. Device Owner job handles are execution mechanics only.

### R2 — façade becomes a monolithic authority

**Risk:** one external API is misinterpreted as one internal owner.

**Mitigation:** preserve explicit owner routing and source-dimension metadata.

### R3 — Device Owner becomes remote root

**Risk:** convenience pressure broadens permissions until the backend is effectively unrestricted.

**Mitigation:** Unix least privilege, separate identities, ACLs, exact sudoers, hard exclusions, independent security tests.

### R4 — command classifier is treated as sandbox

**Risk:** lexical policy is assumed to prevent semantic shell escape.

**Mitigation:** OS-level identity and filesystem/network boundaries remain authoritative.

### R5 — TRIAGE creates cosmetic work

**Risk:** every dogfood observation automatically becomes a decomposed DAG.

**Mitigation:** dedupe and explicit triage policy before decomposition.

### R6 — Mission is removed before equivalence is proven

**Risk:** useful completion/gate semantics are lost.

**Mitigation:** SHADOW projection and real gap analysis.

### R7 — third-party MCP schema becomes permanent Hermes API

**Risk:** upstream backend changes leak directly into ChatGPT semantics.

**Mitigation:** stable DeviceOwnerAdapter.

### R8 — single visible connector becomes single availability domain

**Risk:** failure of one backend takes down all workflow visibility.

**Mitigation:** isolated services and explicit degraded modes.

### R9 — GitHub gets proxied for aesthetic reasons

**Risk:** independent remote provenance becomes another custom integration to maintain.

**Mitigation:** keep the native GitHub connector independent.

### R10 — simplification creates another large framework

**Risk:** replacing Mission/GPT Hermes requires a new subsystem comparable in size to the old one.

**Mitigation:** treat this as failure of the simplification hypothesis and reassess.

---

## 31. Decision table

| Question | Candidate direction | Confidence |
|---|---|---|
| Board is a durable project/domain boundary | yes | high |
| Board should equal one Mission by default | no | high |
| root orchestration card can represent Mission/outcome | likely yes; validate | high |
| build a separate Outcome subsystem now | no | high |
| use TRIAGE for dogfood intake | yes, with dedupe controls | high |
| use Tenant as Mission identity | no | high |
| use Tenant as soft target/data namespace | possibly | medium |
| use attachments/artifacts more heavily | yes | high |
| Kanban remains scheduler | yes | very high |
| generic GPT Hermes owner functions should eventually move out | yes | high |
| delete GPT Hermes immediately | no | very high |
| keep/thin Hermes-specific admin | likely | high |
| pilot an external Device Owner backend | yes | high |
| current preferred backend candidate is `ssh-mcp` | yes, subject to revalidation | medium-high |
| Secure MCP Tunnel is preferred pilot transport | yes, subject to E2E | high |
| re-export backend MCP schemas publicly | no | high |
| create a stable DeviceOwnerAdapter | yes if pilot succeeds | high |
| keep GitHub independent | yes | very high |
| one visible Hermes surface is desirable eventually | yes | medium-high |
| one process should own everything | no | very high |

---

## 32. What remains genuinely open

The following questions require evidence, not more abstract architecture discussion:

1. Can several current real Missions be represented faithfully as root orchestration cards without losing protected completion semantics?
2. Which Mission features remain real gaps after that mapping?
3. Can dogfood reliably enter TRIAGE without unwanted auto-decomposition or duplicate remediation?
4. Which generic GPT Hermes operations are actually used often enough to justify replacement work?
5. Does the selected Device Owner backend match GPT Hermes reliability for those operations?
6. What is the exact ChatGPT Web behavior through Secure MCP Tunnel for the actual project connector surface?
7. How should long-running/background job identity survive connector/tunnel reconnection?
8. Which confirmation/elicitation mechanisms are reliable E2E in the actual harness?
9. What is the smallest useful Hermes-specific admin surface after generic owner operations move out?
10. What is the smallest useful future Hermes Control façade without becoming a new control plane in its own right?

---

## 33. Conditions that would invalidate this direction

This direction should be reconsidered if evidence shows that it requires:

- extensive ongoing patches against upstream Kanban semantics;
- a large compatibility layer merely to preserve normal Mission behavior;
- weaker Human Gate guarantees;
- broader host privileges than the current GPT Hermes owner model;
- unreliable ChatGPT ↔ Secure Tunnel behavior;
- an unstable or poorly governed third-party Device Owner dependency;
- loss of independent evidence/provenance;
- a new custom subsystem comparable in size to the architecture being removed.

Simplification that requires another large framework is not successful simplification.

---

## 34. Recommended target statement

The architectural direction can be summarized as:

> **Native Hermes primitives for common workflow semantics; thin Hermes-specific extensions for genuine governance semantics; replaceable external backends for generic infrastructure operations; explicit authority boundaries throughout.**

Or more compactly:

> **Upstream where possible. Hermes-specific where necessary. Generic infrastructure outside Hermes. Authority always explicit.**

---

## 35. Governance note

This document records analysis and a candidate direction only.

Adopting it would change core boundaries including:

- Mission semantics;
- stable control-plane separation;
- source/authority routing;
- GPT Hermes responsibilities;
- host security architecture.

Therefore adoption is a CORE change and must not occur through incidental drift.

Research, read-only SHADOW evaluation, and architecture comparison can proceed independently, but promotion of a new primary path requires candidate-bound evidence, independent review, relevant real ChatGPT E2E, and explicit Human Gate approval.

---

## 36. References informing this direction

Project-local architectural context:

- `docs/architecture/HERMES-INTEGRATION.md`
- `docs/SYSTEM_MAP.md`
- `docs/SPEC_INDEX.md`
- `docs/ADR_INDEX.md`

External/upstream references reviewed during the analysis:

- Hermes Agent Kanban documentation and current upstream behavior: <https://github.com/NousResearch/hermes-agent>
- OpenAI Secure MCP Tunnel client: <https://github.com/openai/tunnel-client>
- OpenAI ChatGPT developer mode / MCP app documentation: <https://help.openai.com/en/articles/12584461>
- `tufantunc/ssh-mcp`: <https://github.com/tufantunc/ssh-mcp>
- `tufantunc/ssh-mcp` security notes: <https://github.com/tufantunc/ssh-mcp/blob/main/SECURITY.md>
- `gbvolkov/sysadmin_mcp_kit`: <https://github.com/gbvolkov/sysadmin_mcp_kit>

External implementation details are time-sensitive. Revalidate them at the point of any pilot or adoption decision.
