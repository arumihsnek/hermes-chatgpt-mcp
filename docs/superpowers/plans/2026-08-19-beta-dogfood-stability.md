# Beta Dogfood Stability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add release provenance, fail-closed beta deployment verification, and dogfood guidance without changing the protected MCP command surface.

**Architecture:** A small release-metadata loader supplies an optional immutable manifest to the FastMCP health route. The beta installer writes and validates that manifest, while a standalone no-secret verifier checks the public health endpoint. Documentation records the OAuth and safety gates that are outside the MCP runtime.

**Tech Stack:** Python 3, FastAPI/FastMCP, Pydantic, pytest, shell, systemd, OpenResty.

**Spec:** `docs/superpowers/specs/2026-08-19-beta-dogfood-stability-design.md`

## Global Constraints

- Work only in the isolated `beta/board-management` worktree.
- Preserve the 51 canonical leaves, 11 existing tool contracts, strict schemas, and elevated scopes.
- Do not print credentials, tokens, auth files, raw environment assignments, or filesystem paths in public health output.
- Deployment must be fast-forward only and must verify the exact remote SHA.
- Destructive and worker-launching operations remain fail-closed and are not executed by the release probe.

---

### Task 1: Release metadata model and loader

**Files:**
- Create: `hermes_chatgpt_mcp/release.py`
- Modify: `hermes_chatgpt_mcp/config.py`
- Test: `tests/test_release.py`

**Interfaces:**
- `BuildMetadata` is an immutable dataclass with `build_commit: str | None`, `surface: str | None`, and `deployed_at: str | None`.
- `load_build_metadata(path: Path | None) -> BuildMetadata` returns empty metadata for a missing file and rejects malformed metadata without exposing its contents.
- `Settings.build_metadata_file` reads `MCP_BUILD_METADATA_FILE` and defaults to `None`.

- [ ] **Step 1: Write the failing tests**

Add tests for missing metadata, valid metadata, malformed JSON, and rejection of extra/path-like fields in the public projection.

- [ ] **Step 2: Run the focused tests to verify RED**

Run: `pytest -q tests/test_release.py`

Expected: collection or assertion failures because `release.py` and the new setting do not exist.

- [ ] **Step 3: Implement the minimal loader and setting**

Implement strict JSON loading with bounded string fields and an explicit public dictionary containing only `build_commit`, `surface`, and `deployed_at`.

- [ ] **Step 4: Run the focused tests to verify GREEN**

Run: `pytest -q tests/test_release.py`

Expected: all release metadata tests pass.

- [ ] **Step 5: Commit the self-contained change**

Run: `git add hermes_chatgpt_mcp/release.py hermes_chatgpt_mcp/config.py tests/test_release.py && git commit -m "feat: add beta release metadata loader"`

### Task 2: Health endpoint attestation

**Files:**
- Modify: `hermes_chatgpt_mcp/server.py`
- Create: `tests/test_health.py`

**Interfaces:**
- Beta `/healthz` returns `{"status":"ok","build":{...}}` using `BuildMetadata.public_dict()`.
- Stable `/healthz` remains exactly `{"status":"ok"}` for backwards compatibility.
- Existing local beta health behavior remains valid when no manifest is configured.

- [ ] **Step 1: Write the failing health assertion**

In `tests/test_health.py`, build the existing temporary Hermes fixture with `_settings()`, replace `build_metadata_file` with a temporary JSON manifest, construct the beta app, and assert that `GET /healthz` returns `status == "ok"`, `build.surface == "beta"`, and the exact test SHA. Also assert that the response contains no `path`, `token`, `secret`, or environment fields.

- [ ] **Step 2: Run the focused test to verify RED**

Run: `pytest -q tests/test_health.py::test_healthz_includes_public_beta_build_metadata`

Expected: the response lacks the `build` object.

- [ ] **Step 3: Add the health projection**

Load metadata once during app construction and include only its public projection in the health response.

- [ ] **Step 4: Run the focused test to verify GREEN**

Run: `pytest -q tests/test_health.py::test_healthz_includes_public_beta_build_metadata`

Expected: PASS with no secret or path fields.

- [ ] **Step 5: Commit the self-contained change**

Run: `git add hermes_chatgpt_mcp/server.py tests && git commit -m "feat: expose beta build attestation in health"`

### Task 3: Installer and systemd provenance gate

**Files:**
- Modify: `deploy/systemd/hermes-chatgpt-mcp-beta.service`
- Modify: `scripts/install_oci_beta.sh`
- Modify: `tests/test_deployment.py`

**Interfaces:**
- The unit sets `MCP_BUILD_METADATA_FILE=/var/lib/hermes-chatgpt-mcp-beta/build.json`.
- The installer writes JSON with the candidate SHA, `surface: beta`, and UTC timestamp before restart.
- The loopback health assertion requires the exact candidate SHA and beta surface.

- [ ] **Step 1: Write failing deployment assertions**

Assert the unit declares the metadata path and the installer writes/checks the candidate SHA and beta surface.

- [ ] **Step 2: Run focused deployment tests to verify RED**

Run: `pytest -q tests/test_deployment.py`

Expected: failures for the absent metadata path and installer attestation.

- [ ] **Step 3: Implement the minimal unit and installer changes**

Use the existing dedicated runtime and state directory; write only non-secret release metadata and make the existing health loop parse and compare it.

- [ ] **Step 4: Run focused deployment tests to verify GREEN**

Run: `pytest -q tests/test_deployment.py`

Expected: all deployment tests pass.

- [ ] **Step 5: Commit the deployment gate**

Run: `git add deploy/systemd/hermes-chatgpt-mcp-beta.service scripts/install_oci_beta.sh tests/test_deployment.py && git commit -m "feat: attest beta deployment commit"`

### Task 4: Public release verifier

**Files:**
- Create: `scripts/verify_beta_release.py`
- Test: `tests/test_release_verifier.py`

**Interfaces:**
- `python scripts/verify_beta_release.py --url URL --commit SHA` performs a bounded unauthenticated GET to `URL/healthz` and exits nonzero for network errors, wrong surface, wrong SHA, malformed JSON, or non-OK status.
- Output contains only the URL host, status, surface, and abbreviated/expected-safe release fields; never headers, tokens, or environment values.

- [ ] **Step 1: Write failing verifier tests**

Test accepted matching health, wrong SHA, wrong surface, malformed JSON, and non-200 response using a local temporary HTTP server or injected transport.

- [ ] **Step 2: Run focused tests to verify RED**

Run: `pytest -q tests/test_release_verifier.py`

Expected: failures because the verifier module/script does not exist.

- [ ] **Step 3: Implement the bounded verifier**

Use the standard library HTTP client, a short timeout, strict JSON checks, and explicit exit codes.

- [ ] **Step 4: Run focused tests to verify GREEN**

Run: `pytest -q tests/test_release_verifier.py`

Expected: all verifier tests pass.

- [ ] **Step 5: Commit the verifier**

Run: `git add scripts/verify_beta_release.py tests/test_release_verifier.py && git commit -m "feat: add public beta release verifier"`

### Task 5: Dogfood runbook and release evidence

**Files:**
- Modify: `README.md`
- Modify: `docs/DEPLOYMENT.md`
- Create: `docs/BETA_DOGFOOD.md`
- Test: `tests/test_beta_docs.py`

**Interfaces:**
- Documentation states the exact OAuth selection/scopes, read-only preflight, connector-stale classification, admin boundaries, public verifier command, and rollback/readback requirements.
- No credential or private path is included in the dogfood instructions.

- [ ] **Step 1: Write documentation assertions**

Assert the runbook contains the selected-board requirement, `hermes:create`/`hermes:manage`, explicit `hermes:admin` warning, `AUTH_READ_ONLY`, `BLOCKED_PLATFORM`, and the verifier invocation.

- [ ] **Step 2: Run focused docs tests to verify RED**

Run: `pytest -q tests/test_beta_docs.py`

Expected: failures for the absent runbook sections.

- [ ] **Step 3: Add the concise runbook and deployment references**

Document only the supported current behavior and label the external ChatGPT discovery cache as external evidence.

- [ ] **Step 4: Run focused docs tests to verify GREEN**

Run: `pytest -q tests/test_beta_docs.py`

Expected: all documentation assertions pass.

- [ ] **Step 5: Commit the documentation**

Run: `git add README.md docs/DEPLOYMENT.md docs/BETA_DOGFOOD.md tests/test_beta_docs.py && git commit -m "docs: define beta dogfood release gate"`

### Task 6: Full verification, publication, and remote readback

**Files:**
- No planned source changes; only release evidence and Git state.

- [ ] **Step 1: Run the complete test and static verification set**

Run: `pytest -q`, `PYTHONDONTWRITEBYTECODE=1 python3 -m compileall -q hermes_chatgpt_mcp scripts`, `bash -n scripts/install_oci_beta.sh`, and `git diff --check`.

- [ ] **Step 2: Confirm exact ancestry and clean worktree**

Run: `git merge-base --is-ancestor c9ce66e25e55332b557b6af4471fbcdee377902 HEAD`, `git status --short --branch`, and `git log -1 --format=%H`.

- [ ] **Step 3: Push fast-forward and deploy the exact SHA**

Use the existing installer with the exact candidate SHA; do not force push or deploy another branch.

- [ ] **Step 4: Verify live service and public release attestation**

Check systemd state, loopback health, public health, OAuth metadata, and run `scripts/verify_beta_release.py` against the public hostname.

- [ ] **Step 5: Record evidence and final status**

Record changed files, exact SHA, test commands/results, runtime, health response summary, scope matrix, and remaining external connector limitation. Do not declare full 51/51 PASS unless independently demonstrated.
