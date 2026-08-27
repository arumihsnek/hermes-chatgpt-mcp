# OCI deployment

**Status:** V0.4 DEPLOYMENT CONTRACT (dated 2026-08-16; **SUPERSEDED for current runtime by the 2026-08-27 V4 stable cutover**). See [## V4 stable runtime (2026-08-27)](#v4-stable-runtime-2026-08-27) below for the current runtime truth. The v0.4 deployment procedure (systemd unit, root-owned OpenResty location include, env file, state directory, OAuth signing key) remains the **operational procedure** for the 8791 beta deployment unit when it is resurrected; the V4 stable cutover uses the canary + 8789 override model (see §V4 stable runtime below).

The OCI host runs HermesKanban and terminates TLS in the existing 1Panel
OpenResty container. `hermes-chatgpt-mcp` remains an independent systemd
service on `127.0.0.1:8789`; OpenResty forwards only the MCP/OAuth/health
paths for `kanban.hermesinthenight.duckdns.org`.

## Stable and beta deployment boundary

The stable and beta deployments are intentionally parallel:

| Surface | Public MCP origin | Loopback listener | Systemd unit | OAuth state |
| --- | --- | --- | --- | --- |
| Stable | `https://kanban.hermesinthenight.duckdns.org/mcp` | `127.0.0.1:8789` | `hermes-chatgpt-mcp.service` | `/var/lib/hermes-chatgpt-mcp/oauth-state.json` |
| Beta | `https://kanban-beta.hermesinthenight.duckdns.org/mcp` | `127.0.0.1:8791` | `hermes-chatgpt-mcp-beta.service` | `/var/lib/hermes-chatgpt-mcp-beta/oauth-state.json` |

Stable exposes eight tools (seven reads plus `create_task`) and its three
scopes. Beta exposes eleven tools (the same seven reads plus `create_task`,
`create_board`, `add_comment`, and `assign_task`) and its five scopes. The beta
unit and OpenResty include own their service name, port, public hostname,
environment file, state path, and OAuth signing key. Installing beta does not
modify the stable unit or stable OAuth state. Beta DNS/TLS/OCI availability is
not verified by this repository task and remains pending operator validation.

## Install or update

Run from this repository as `ubuntu` with non-interactive sudo:

```bash
./scripts/install_oci.sh
```

The installer:

1. installs the systemd unit and root-owned OpenResty location include;
2. creates or preserves `/home/ubuntu/.hermes/hermes-chatgpt-mcp.env` as
   `ubuntu:ubuntu`, mode `0600`, without printing its values;
3. configures the canonical board resolver to discover all active boards by
   default and keeps loopback port 8789;
4. validates OpenResty inside the running 1Panel container;
5. reloads systemd and restarts the service;
6. waits for loopback health and reloads OpenResty through
   `/usr/local/bin/reload-openresty-1panel.sh`.

The systemd unit declares `StateDirectory=hermes-chatgpt-mcp`, which creates
`/var/lib/hermes-chatgpt-mcp` as a private `0700` directory. The OAuth state
file is `/var/lib/hermes-chatgpt-mcp/oauth-state.json` with mode `0600`.
`MCP_OAUTH_STATE_FILE` is also explicit in the unit, so an old env file cannot
silently restore the v0.1 in-memory behavior.

## Beta install or update

Run this only as a separately authorized deployment action; it was not run for
this documentation task:

```bash
./scripts/install_oci_beta.sh <exact-beta-commit>
```

The installer requires the candidate Git worktree to be clean and exactly at
the requested commit. It validates the beta OpenResty include before copying
artifacts, installs only `hermes-chatgpt-mcp-beta.service` and its beta include,
creates `/var/lib/hermes-chatgpt-mcp-beta` with restrictive ownership, and
creates or preserves the private environment file
`/home/ubuntu/.hermes/hermes-chatgpt-mcp-beta.env` at mode `0600`. The private
file contains the beta public origin, loopback port `8791`,
`MCP_SURFACE=beta`, `MCP_BOARD_CREATE_ENABLED=1`, the beta OAuth state path,
and a signing key separate from stable. Credential values are never printed or
committed.

It also writes the non-secret `/var/lib/hermes-chatgpt-mcp-beta/build.json`
manifest containing the requested commit, `surface: beta`, and deployment
time. The loopback health check requires those values to match the candidate;
the public counterpart is verified with
`python scripts/verify_beta_release.py --url https://kanban-beta.hermesinthenight.duckdns.org --commit "$CANDIDATE_SHA"`.

The beta unit keeps `ProtectSystem=full`, `ProtectHome=read-only`,
`NoNewPrivileges`, private devices/temp space, and write access only to
canonical named-board storage plus the beta state directory. Its OpenResty
include owns only `/mcp`, `/healthz`, OAuth discovery, and `/oauth/` for the
beta hostname; it does not proxy a general Hermes UI route.

After the beta artifacts are installed, the script reloads systemd, enables and
restarts only the beta unit, checks the beta loopback health response
`status=ok` with the exact build attestation on `127.0.0.1:8791`, and reloads
the existing OpenResty hook.
The installer does not restart `hermes-chatgpt-mcp.service`. The 2026-08-19
dogfood release also passed the public HTTPS verifier and MCP discovery probe;
this does not claim that a ChatGPT connector has refreshed cached OAuth or
tool-schema state.

## Sandbox boundary

The unit keeps `NoNewPrivileges`, `ProtectSystem=full`, `ProtectHome=read-only`,
`PrivateDevices`, `PrivateTmp`, and restricted address families. The Hermes
write allowance is limited to named canonical board storage:

```text
/home/ubuntu/.hermes/kanban/boards
```

That directory is needed by Hermes' canonical command connection for its
normal SQLite/WAL operation. The query adapter still opens its own connection
with URI `mode=ro` and immediately sets `PRAGMA query_only=ON`; it never uses
the writable command connection. The second write allowance is only the
service-owned OAuth state directory. Optional `MCP_KANBAN_*_BOARDS` values can
still narrow the deployment, but are not required for normal all-named-board
read and single-board OAuth write grants. Hermes' legacy `default` root
database is intentionally not exposed because its sidecars are shared with
other Hermes processes.

## Verification

```bash
sudo systemd-analyze verify /etc/systemd/system/hermes-chatgpt-mcp.service
sudo systemctl is-enabled hermes-chatgpt-mcp.service
sudo systemctl is-active hermes-chatgpt-mcp.service
stat -c '%A %U:%G %n' /var/lib/hermes-chatgpt-mcp
sudo journalctl -u hermes-chatgpt-mcp.service -n 50 --no-pager
```

Check the actual OpenResty executable in the container:

```bash
sudo ctr -n moby containers list
sudo ctr -n moby tasks exec --exec-id mcp-syntax-check <openresty-container-id> \
  /usr/local/openresty/bin/openresty -t -c /usr/local/openresty/nginx/conf/nginx.conf
```

Then verify from a CA-valid client:

```text
GET https://kanban.hermesinthenight.duckdns.org/healthz
GET https://kanban.hermesinthenight.duckdns.org/.well-known/oauth-protected-resource
GET https://kanban.hermesinthenight.duckdns.org/.well-known/oauth-authorization-server
POST https://kanban.hermesinthenight.duckdns.org/oauth/register
POST https://kanban.hermesinthenight.duckdns.org/oauth/token
POST https://kanban.hermesinthenight.duckdns.org/mcp
```

The MCP endpoint must return `401` without a bearer token. A complete test
must use DCR + PKCE, choose read-only or read+write in the OAuth consent page,
verify eight tools (seven read plus `create_task`) and their annotations, call
`list_boards`, read two canonical boards, and for write testing use separate
board-bound grants—one grant per selected board. Never copy the runtime
password, refresh token, or bearer token into shell history or logs.

For a controlled live check, use clearly prefixed test cards and remove them
afterward only through Hermes' native administrative/test cleanup path. Never
add a public delete tool to make cleanup convenient.

The repository includes a bounded endpoint smoke:

```bash
set -a; . /home/ubuntu/.hermes/hermes-chatgpt-mcp.env; set +a
HERMES_LIVE_TEST=1 /home/ubuntu/hermes-agent/venv/bin/python \
  scripts/live_multiboard_smoke.py
HERMES_LIVE_TEST=1 HERMES_LIVE_WRITE_TEST=1 \
  /home/ubuntu/hermes-agent/venv/bin/python scripts/live_multiboard_smoke.py
```

The second command performs one idempotent create per controlled board and
cleans both cards with Hermes-native administrative functions in `finally`.

For the beta deployment, the corresponding local checks are:

```bash
sudo systemd-analyze verify /etc/systemd/system/hermes-chatgpt-mcp-beta.service
sudo systemctl is-active hermes-chatgpt-mcp-beta.service
curl --fail http://127.0.0.1:8791/healthz
```

An operator should separately re-run the configured beta HTTPS verifier and
OAuth metadata checks after every deployment. The repository tests prove
configuration shape and ASGI behavior; the public release gate is the exact
SHA read back from `/healthz` and verified by `scripts/verify_beta_release.py`.

## Restart persistence check

Before a production restart, register a temporary public test client with a
local/controlled callback and obtain a refresh token through the normal PKCE
flow. Record only the client ID (not tokens), then run:

```bash
sudo systemctl restart hermes-chatgpt-mcp.service
```

Use the same client ID and refresh token against `/oauth/token`. Success proves
that DCR registration and refresh rotation survived the restart. The old
refresh token must be rejected after rotation, and the new token must carry
the same requested scopes. Authorization codes are intentionally not persisted
and should expire or become invalid across a restart.

The current deployment persists DCR registrations and refresh-token hashes in
the state file. A service restart must therefore preserve the registered
`client_id`; only authorization codes are intentionally lost. A ChatGPT
connection that was authorized without `hermes:create` still requires an
explicit OAuth reauthorization to gain that scope, even though its DCR client
survives. DCR scope metadata is a default, while `/oauth/authorize` validates
against the server's advertised scopes and the resulting token scope is still
limited to the explicitly requested and approved values.

The beta service applies the same persistence rule to its own state file, but
does not read the stable state file. Beta DCR registrations, refresh-grant
records, revoked-grant IDs, and the beta signing key are separate from stable;
authorization codes remain in memory. A stable ChatGPT connection therefore
needs a separate beta connector authorization, and changing a beta write board
needs a new authorization that selects exactly one board.

`hermes:board:create` is a global beta scope. A board-creation grant has no
board claim and `create_board` does not grant task-write access to the new
board. `hermes:create` and `hermes:manage` are the one-board command scopes;
`add_comment` and `assign_task` require `hermes:manage`, while `create_task`
requires `hermes:create`.

## Rollback and removal

The installer creates timestamped backups of the edited OpenResty host config.
To remove only this integration:

```bash
./scripts/uninstall_oci.sh
```

Removal preserves the environment file, OAuth state, Hermes source, databases,
logs, and the existing Kanban service. Do not delete the state directory if a
future rollback must preserve ChatGPT registrations.

## Beta rollback to the stable endpoint

The beta installer is transactional. If validation, artifact installation,
OpenResty syntax checking, beta restart, or the local health check fails after
mutation starts, its exit trap restores the previous beta unit/include/edge
configuration/environment and service state. If an edge reload was attempted,
it validates and reloads the restored edge before returning the failure. This
rollback is beta-only and does not restart or rewrite the stable unit.

For a deliberate user-facing fallback after a beta installation, keep the
stable unit and stable state intact and reconnect ChatGPT to
`https://kanban.hermesinthenight.duckdns.org/mcp`. Stable OAuth authorization
is independent of beta OAuth authorization. Disablement or removal of the beta
unit/include is a separate change-controlled operator action; no live rollback
was performed or verified for this task.

## OAuth handshake diagnostics

OAuth diagnostics are disabled in the normal systemd unit. If a future
controlled handshake diagnosis needs them, set `MCP_OAUTH_DIAGNOSTICS=1` only
for that experiment, then restore `0` and restart. Diagnostics do not grant
scope or change OAuth decisions; they emit only bounded scope/board names,
safe status fields, and short one-way fingerprints for DCR, `/authorize`,
`/token`, refresh, revocation, and MCP bearer verification events.

After installing the committed unit, verify the service and inspect only the
diagnostic marker:

```bash
sudo systemd-analyze verify /etc/systemd/system/hermes-chatgpt-mcp.service
sudo systemctl daemon-reload
sudo systemctl restart hermes-chatgpt-mcp.service
sudo journalctl -u hermes-chatgpt-mcp.service -g hermes_oauth_diagnostic --since '5 minutes ago' --no-pager
```

Do not copy general Uvicorn access logs into evidence. The server disables
Uvicorn access logging because OAuth query strings can contain PKCE and
authorization state values. Never record token values or the OAuth state file.

---

## V4 stable runtime (2026-08-27)

**This is the current runtime truth.** The v0.4 deployment procedure above remains the **operational procedure** (systemd unit, root-owned OpenResty location include, env file, state directory, OAuth signing key) for the `8791` beta deployment unit when it is resurrected. The V4 stable cutover uses a **canary + 8789 override** model: the same `4ae5060` candidate image is served at `127.0.0.1:8789` (public, via override) and at `127.0.0.1:8792` (canary, isolated), with `8791` dormant.

### Topology

| Surface | Loopback | Process | Working dir | Public route | Identity |
|---------|----------|---------|-------------|---------------|----------|
| Stable (public) | `127.0.0.1:8789` | `hermes-chatgpt-mcp.service` (MainPID 2505228) | `/opt/hermes-chatgpt-mcp-canary` (override-redirected; see `/etc/systemd/system/hermes-chatgpt-mcp.service.d/override.conf`) | OpenResty `hermes-chatgpt-mcp.locations` (SHA-256 `27caf874…0816`, unchanged) | `4ae5060931a64741185c5c8deb3886a5901f21cc` / `beta` / `v4.wave0` |
| Canary (isolated) | `127.0.0.1:8792` | `hermes-chatgpt-mcp-canary.service` (MainPID 2506251) | `/opt/hermes-chatgpt-mcp-canary` | none (systemd disabled; no public route) | `4ae5060931a64741185c5c8deb3886a5901f21cc` / `beta` / `v4.wave0` |
| Pre-V4 `8791` beta | **not running** | `hermes-chatgpt-mcp-beta.service` (dormant; unit + `/var/lib/hermes-chatgpt-mcp-beta` state dir still on disk) | n/a | n/a (pre-V4 v0.4 topology) | n/a — superseded by the canary + 8789 override model |

### Public origin (current)

- `https://kanban.hermesinthenight.duckdns.org/mcp` (MCP)
- `https://kanban.hermesinthenight.duckdns.org/healthz` (healthz; identity headers: `x-v4-provenance: 4ae5060931a6/d7eba25/beta`, `x-api-version: v4.wave0`, `x-baseline-branch: v4/baseline-post-update-885e9ef`, `x-baseline-mcp: d7eba25ea8f6`)
- `https://kanban.hermesinthenight.duckdns.org/.well-known/oauth-authorization-server` (OAuth discovery)
- `https://kanban.hermesinthenight.duckdns.org/.well-known/oauth-protected-resource` (OAuth protected-resource metadata)

### Rollback path (executable, byte-anchored, no installer run)

The V4 stable rollback is **three reversible mutations only**:

1. **Delete the override drop-in** at `/etc/systemd/system/hermes-chatgpt-mcp.service.d/override.conf` (SHA-256 `d8d87c59…1d90a`).
2. **Restore the prior-good `build.json`** from the in-place backup `/var/lib/hermes-chatgpt-mcp/build.json.pre-surface-rectification-20260826T103951Z.bak` (commit `d7eba25ea8f6`, surface `stable`, deployed_at `2026-08-25T15:13:56Z`).
3. **One bounded `systemctl restart hermes-chatgpt-mcp.service`** (the only restart; no daemon-reload, no OpenResty reload).

No installer run, no wheel re-hash, no OAuth state rewrite, no credential rotation, no OpenResty mutation, no schema migration. The pre-promotion venv `/opt/venvs/hermes-chatgpt-mcp` is on disk (mtime 2026-08-17) and is reused. The pre-promotion env file `/home/ubuntu/.hermes/hermes-chatgpt-mcp.env` is on disk and is reused.

### V4 stable identity (durable binding)

- Connector: `4ae5060931a64741185c5c8deb3886a5901f21cc` (branch `v4-candidate-integration`)
- Phase-S source bundle: `9a8410b4e883e27a4e0572951ee00f9faf4f3d19` (branch `release/source-bundle-phase-s`)
- Hermes Core MCP baseline: `d7eba25ea8f692d2d0b65d7e5044df79e94c8a92` (header short `d7eba25ea8f6`; branch `v4/baseline-post-update-885e9ef`)
- Surface: `beta` (controller classifies as STABLE; `Kanban_Beta` discovery label is stale naming metadata)
- API version: `v4.wave0`
- Live MCP `tools/list` tool count: **71** (vs the 2026-08-19 54-tool discovery)
- v4.wave0 required tools (all 6 present): `list_boards`, `get_board`, `list_tasks`, `get_task`, `create_task`, `add_comment`

### Authoritative references

- **[RELEASE-STABLE-V4.md](../RELEASE-STABLE-V4.md)** — durable release anchor.
- **[CHECKPOINT-2026-08-27-V4-STABLE.md](v4/CHECKPOINT-2026-08-27-V4-STABLE.md)** — full truth-sync checkpoint, including live readback, topology narrative, rollback path, residuals register, dogfood lessons.
- **[CURRENT_STATE.md](v4/CURRENT_STATE.md) §17** — V4 stable reconciliation summary in the canonical source-of-truth doc.
- **[EVIDENCE_AND_OPEN_QUESTIONS.md](v4/EVIDENCE_AND_OPEN_QUESTIONS.md) §2 + §9** — `STILL_NOT_PROVEN` register + V4 stable residual register.
- **[STALE_DOCS.md](v4/STALE_DOCS.md)** — explicit classification of the v0.4 `8791` topology descriptions as **RETAIN / LINK; SUPERSEDE for current runtime**.

### Historical context (preserved)

The pre-V4 `8791` beta deployment procedure (systemd unit `hermes-chatgpt-mcp-beta.service`, env file `/home/ubuntu/.hermes/hermes-chatgpt-mcp-beta.env`, state dir `/var/lib/hermes-chatgpt-mcp-beta`, OpenResty include, etc.) is **preserved unchanged** in the v0.4 section above. The v0.4 procedure is the operational procedure to use when the `8791` beta is resurrected; it is **not** the current runtime. The 2026-08-27 V4 stable cutover chose the canary + 8789 override model (one candidate image at `4ae5060`, served both at 8792 isolated and at 8789 via override) rather than a parallel stable/beta dual-deployment.
