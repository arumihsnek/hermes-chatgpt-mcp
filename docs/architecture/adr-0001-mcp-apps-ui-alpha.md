# ADR-0001 — Read-only MCP Apps UI alpha

Status: frozen candidate v1, architecture review PASS (t_e76513cd).

## Decision

Add one static MCP Apps resource, `ui://hermes/kanban/v1`, and link it only to the existing canonical `get_board` read tool. The resource uses `text/html;profile=mcp-app` and a self-contained vanilla HTML implementation. Existing structured output and meaningful text fallback are unchanged.

The widget composes bounded read tools over the MCP Apps bridge to show board selection, status columns, card identity, and dispatch/dependency context. It has an explicit Refresh action. It never calls `get_activity`, writes data, persists content, opens links, updates model context, or presents Human Gate approval controls.

## Rationale and consequences

This is the smallest reversible seam: no new data tool, no transport/auth/deployment changes, and no duplicated adapter policy. The versioned URI is the host cache key; content or behavior changes require a URI bump. The single-file implementation keeps static purity and no-egress checks deterministic. A future write-capable UI requires a separately reviewed contract and all W1–W7 controls.

## Verification

`pytest -q` is the implementation gate. The resource test verifies tool/resource registration, exact MIME and URI metadata, fallback, byte bound, and forbidden static patterns. Reference-host rendering is intentionally local-only; no stable deployment or promotion is performed by this ADR.
