# ChatGPT ↔ Hermes Sessions MCP

Documentation for a **session-only, read-only** MCP connector between ChatGPT and Hermes Agent.
This repository currently contains documentation only; it does not claim to implement an MCP
server or alter Hermes.

## Scope

The connector design covers three read operations:

- `list_sessions` — enumerate sessions through a canonical Hermes read interface.
- `get_session` — retrieve metadata for one session.
- `get_session_output` — retrieve/export the recorded conversation for one session.

Sending input, creating sessions, and starting/resuming sessions are **not available as safe
external connector capabilities** in the verified Hermes source. They must not be implemented by
substituting shell, tmux, SSH, filesystem, or process-control access.

This project intentionally excludes Kanban boards/tasks, scheduling, planner/controller flows,
workflow DAGs, and arbitrary host access. See [SPEC.md](SPEC.md), [SECURITY.md](SECURITY.md), and
the [source-provenance record](docs/HERMES-SESSION-INTEGRATION.md).

## Verified source basis

The documented behavior is pinned to the real Hermes Agent source repository
[`NousResearch/hermes-agent`](https://github.com/NousResearch/hermes-agent) at:

`19b846543cff0da8a7e74cc4517b1ccb3f4d14f9`

The provenance record lists the exact files and symbols inspected, the read contract, state and
cursor model, authentication boundaries, and evidence gaps. Claims about this connector's own
implementation are intentionally absent because no implementation is present yet.

## Status

Design/documentation candidate only. The read contract is grounded in verified Hermes CLI, REST,
and state-store paths; transport, MCP schema, packaging, and write operations require a separate
implementation and review.
