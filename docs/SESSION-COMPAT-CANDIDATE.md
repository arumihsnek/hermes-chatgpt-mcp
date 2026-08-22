# Streamable HTTP compatibility candidate

This candidate is based on commit `9a8410b` and `mcp==1.28.1`. It does not
restart or mutate the stable service.

## Frozen connector contract

With `MCP_SURFACE=beta` and `MCP_CHATGPT_COMPAT_MODE=true`, `tools/list`
advertises exactly:

```
list_boards, get_board, list_tasks, get_task, get_task_graph, get_dispatch,
get_activity, create_task, create_board, add_comment, assign_task
```

The handlers retain the existing beta OAuth scopes (`hermes:read`,
`hermes:create`, `hermes:manage`, `hermes:board:create`, and `hermes:admin`)
and selected-board write grant checks. The mode is opt-in and is rejected on
the stable surface.

## Transport decision and matrix

The candidate uses `stateless_http=True` with JSON responses. This is a
compatibility choice for an API-style connector: the 11 tools do not require
server-to-client sampling, elicitation, roots, resumability, or session-local
state. Every request is independently authenticated and routed to canonical
Hermes adapters.

The regression suite exercises the real ASGI transport and covers:

| Case | Expected result |
| --- | --- |
| initialize without `mcp-session-id` | 200 JSON response; no session is issued |
| initialize with a client-supplied ID | request is handled independently; ID is not trusted or echoed |
| correct, wrong, or stale ID | no state lookup; request remains independent |
| repeated `tools/list` / `tools/call` | each request succeeds without replaying an ID |
| ChatGPT-style list/read/write/readback | each request is independently authenticated and reaches the handler |
| 404/reinitialize behavior | transport has no stateful session to reinitialize; normal HTTP routing/auth errors remain 404/401 |

The existing MCP integration tests (`tests/test_mcp_beta.py`,
`tests/test_mcp_readonly.py`, and `tests/test_oauth_http.py`) provide the
request matrix and consecutive-call coverage. The exact eleven-tool contract
has a dedicated assertion in `test_chatgpt_compat_mode_freezes_exact_eleven_tool_contract`.

## Stateful retention evidence

FastMCP 1.28.1 does not expose `session_idle_timeout` in its constructor. Its
pinned `StreamableHTTPSessionManager` source shows that stateful mode creates a
new transport whenever the request omits `mcp-session-id` and stores it in
`_server_instances`; with the default timeout of `None`, those transports have
no automatic idle reaper. Consequently, an omitted-ID workload grows the
stateful registry once per request. Correct IDs reuse a transport; wrong/stale
IDs return 404. The candidate avoids this unbounded retention class entirely
by using the SDK's stateless path, which creates and terminates one transport per
request and never populates the session registry.

## Safe observability

`_McpObservabilityMiddleware` logs only request path, negotiated protocol
version, response status, and a 16-hex-character SHA-256 fingerprint of the
incoming session ID. It never logs authorization headers, tokens, raw session
IDs, or request bodies.

## Verification

- `pytest -q`: 199 passed.
- Targeted exact-contract test: 1 passed.
- Clean dependency install was attempted in the workspace-local `.venv-clean`,
but the Kanban execution sandbox denies package-manager mutation even inside a
workspace. The declared dependency set includes `PyYAML>=6.0,<7`; the existing
runtime test suite imports the package successfully. A release operator must
run `pip install -e '.[test]'` in the isolated deployment venv before rollout.
