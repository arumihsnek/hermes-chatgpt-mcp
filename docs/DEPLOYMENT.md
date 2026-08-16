# OCI deployment

The OCI machine runs the existing HermesKanban UI on loopback port 8790 and terminates TLS in a 1Panel OpenResty container. This integration uses loopback port 8789 and path-specific routing on the existing `kanban.hermesinthenight.duckdns.org` TLS server, so it does not expose a new Hermes process or require a new certificate name.

## Install

Run from the integration repository as `ubuntu` with non-interactive sudo available:

```bash
./scripts/install_oci.sh
```

The installer:

1. installs the systemd unit and root-owned OpenResty location include;
2. creates `/home/ubuntu/.hermes/hermes-chatgpt-mcp.env` as `ubuntu:ubuntu` mode 0600 if it does not exist, generating private credentials without printing them;
3. uses the configured `codex_app_server` board and loopback `127.0.0.1:8789` defaults;
4. validates OpenResty inside the running 1Panel container;
5. restarts the MCP unit, waits for `/healthz`, and reloads OpenResty through `/usr/local/bin/reload-openresty-1panel.sh`.

The `.locations` suffix is intentional: 1Panel's `conf.d/*.conf` include runs at HTTP scope, while this file contains `location` blocks and is included only inside the existing Kanban server block.

## Verification

```bash
sudo systemd-analyze verify /etc/systemd/system/hermes-chatgpt-mcp.service
sudo systemctl is-active hermes-chatgpt-mcp.service
sudo journalctl -u hermes-chatgpt-mcp.service -n 50 --no-pager
```

The edge check must be performed with the OpenResty container's actual executable, not the failed host `nginx.service`:

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
```

The MCP endpoint itself must return `401` without a bearer token. Use the OAuth flow, not a copied secret in a shell history, to obtain a ChatGPT token.

## SQLite sandbox note

The application always opens Hermes with SQLite URI `mode=ro` and immediately sets `PRAGMA query_only=ON`. The systemd unit permits writes only to the selected board directory so SQLite can create transient WAL/SHM coordination sidecars when Hermes uses WAL; no Hermes table/row mutation API is reachable and the read-only tests fingerprint the state before/after every operation. Change the `ReadWritePaths` line whenever the configured board changes.

## TLS and rollback

The existing Kanban certificate must be a valid server chain, not just a leaf certificate. The installer does not mint or copy certificates. If the edge config or certificate needs repair, back it up first and validate inside the OpenResty container before reloading. The integration deployment keeps timestamped backups of the edited `hermes-subdomains.conf`.

To remove only this integration:

```bash
./scripts/uninstall_oci.sh
```

This stops/removes only `hermes-chatgpt-mcp.service` and its managed include. It preserves the environment file and never deletes Hermes databases, logs, source, or the existing Kanban service.
