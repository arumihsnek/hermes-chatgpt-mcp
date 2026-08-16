# OCI deployment

The OCI host runs HermesKanban and terminates TLS in the existing 1Panel
OpenResty container. `hermes-chatgpt-mcp` remains an independent systemd
service on `127.0.0.1:8789`; OpenResty forwards only the MCP/OAuth/health
paths for `kanban.hermesinthenight.duckdns.org`.

## Install or update

Run from this repository as `ubuntu` with non-interactive sudo:

```bash
./scripts/install_oci.sh
```

The installer:

1. installs the systemd unit and root-owned OpenResty location include;
2. creates or preserves `/home/ubuntu/.hermes/hermes-chatgpt-mcp.env` as
   `ubuntu:ubuntu`, mode `0600`, without printing its values;
3. configures the canonical board resolver with the bounded OCI allowlists
   `codex_app_server,dashboard` and loopback port;
4. validates OpenResty inside the running 1Panel container;
5. reloads systemd and restarts the service;
6. waits for loopback health and reloads OpenResty through
   `/usr/local/bin/reload-openresty-1panel.sh`.

The systemd unit declares `StateDirectory=hermes-chatgpt-mcp`, which creates
`/var/lib/hermes-chatgpt-mcp` as a private `0700` directory. The OAuth state
file is `/var/lib/hermes-chatgpt-mcp/oauth-state.json` with mode `0600`.
`MCP_OAUTH_STATE_FILE` is also explicit in the unit, so an old env file cannot
silently restore the v0.1 in-memory behavior.

## Sandbox boundary

The unit keeps `NoNewPrivileges`, `ProtectSystem=full`, `ProtectHome=read-only`,
`PrivateDevices`, `PrivateTmp`, and restricted address families. The only
Hermes write allowances are:

```text
/home/ubuntu/.hermes/kanban/boards/codex_app_server
/home/ubuntu/.hermes/kanban/boards/dashboard
```

That directory is needed by Hermes' canonical command connection for its
normal SQLite/WAL operation. The query adapter still opens its own connection
with URI `mode=ro` and immediately sets `PRAGMA query_only=ON`; it never uses
the writable command connection. The third write allowance is only the
service-owned OAuth state directory. Keep `ReadWritePaths`,
`MCP_KANBAN_READ_BOARDS`, and `MCP_KANBAN_CREATE_BOARDS` synchronized.

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
must use DCR + PKCE, request `hermes:read hermes:create`, verify eight tools
(seven read plus `create_task`) and their annotations, call `list_boards`,
read both allowlisted boards explicitly, create one idempotent test task on
each controlled board, and read both tasks back. Never copy the runtime
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
survives.

## Rollback and removal

The installer creates timestamped backups of the edited OpenResty host config.
To remove only this integration:

```bash
./scripts/uninstall_oci.sh
```

Removal preserves the environment file, OAuth state, Hermes source, databases,
logs, and the existing Kanban service. Do not delete the state directory if a
future rollback must preserve ChatGPT registrations.

## Temporary OAuth handshake diagnostics

The current diagnosis branch temporarily enables
`MCP_OAUTH_DIAGNOSTICS=1` in the systemd unit. This does not grant any scope or
change OAuth decisions. It emits only bounded scope names, safe status fields,
and short one-way fingerprints for DCR, `/authorize`, `/token`, refresh, and
MCP bearer verification events.

After installing the committed unit, verify the service and inspect only the
diagnostic marker:

```bash
sudo systemd-analyze verify /etc/systemd/system/hermes-chatgpt-mcp.service
sudo systemctl daemon-reload
sudo systemctl restart hermes-chatgpt-mcp.service
sudo journalctl -u hermes-chatgpt-mcp.service -g hermes_oauth_diagnostic --since '5 minutes ago' --no-pager
```

Do not copy general Uvicorn access logs into evidence. The server disables
Uvicorn access logging while this diagnostic build is running because OAuth
query strings can contain PKCE and authorization state values. Once the one
fresh ChatGPT authorization has been captured, remove the temporary
`MCP_OAUTH_DIAGNOSTICS=1` unit line, restore normal deployment logging policy,
reload systemd, and restart the service.
