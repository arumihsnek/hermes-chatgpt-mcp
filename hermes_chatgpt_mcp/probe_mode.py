"""Opt-in fail-closed probe mode for authority-bearing MCP tools.

Design
------

The parity report (``V4-CHATGPT-TOOL-PARITY-P0``) showed that an authenticated
admin-scope caller can trigger real, durable side effects on the production
Hermes board by simply calling authority-bearing MCP tools.  Probe mode
addresses this without weakening normal OAuth scope enforcement: the caller
opts in by passing ``probe: true`` on the tool request body, and every
authority-bearing (non-read) tool then refuses to execute its side effect
and returns a deterministic, typed ``ProbeModeRefusal`` instead.

Invariants
----------

* Probe mode is **opt-in only** — the absence of ``probe`` is treated as
  ``False``; the default is real execution.
* Probe mode is **fail-closed** — when ``probe=True`` the tool raises before
  the adapter call, never partially.  No side effect is observable in the
  Hermes DB, kanban events, attachment store, or control plane.
* Probe mode **does not weaken OAuth scope enforcement** — scope checks run
  first; a probe-mode caller without the required scope still gets
  ``SCOPE_REQUIRED``.
* Probe mode **does not enable Human Gate self-approval** — the
  ``human-gate-decide`` tool keeps its existing actor != requester check.
* Probe mode **leaves read tools unaffected** — read tools do not need
  ``probe: true`` to be called and will never refuse.

The refusal payload is encoded as a JSON ``ToolError`` whose body is the
serialized ``ProbeModeRefusal`` model.  MCP renders this as a structured
``isError`` response that never includes stack traces, internal paths, or
the original request body.
"""

from __future__ import annotations

import json
from typing import Any

from mcp.server.fastmcp.exceptions import ToolError

from .schemas import ProbeModeRefusal


def is_probe_request(request: Any) -> bool:
    """Return True iff the request body explicitly opts in to probe mode.

    The check is defensive: any request model that does not declare a
    ``probe`` attribute is treated as a non-probe call.  This keeps probe
    mode strictly opt-in and never activates from a legacy client that
    simply omits the field.
    """
    return bool(getattr(request, "probe", False))


def enforce_probe_safe(request: Any, tool_name: str) -> None:
    """Raise a deterministic ``PROBE_MODE_REFUSAL`` if probe mode is active.

    Called from each authority-bearing tool **after** scope and board
    resolution and **before** the adapter call.  The refusal is encoded as
    a ``ToolError`` whose JSON body is the serialized
    ``ProbeModeRefusal`` model so MCP clients see a typed, deterministic
    refusal instead of a stack trace.
    """
    if not is_probe_request(request):
        return
    refusal = ProbeModeRefusal(tool_name=tool_name)
    raise ToolError(json.dumps(refusal.model_dump(), separators=(",", ":")))


def probe_refusal_payload(tool_name: str) -> dict[str, Any]:
    """Return the JSON-serializable refusal body for tests and auditors.

    The shape mirrors what an MCP client would receive over the wire when
    an authority-bearing tool is invoked under probe mode.
    """
    refusal = ProbeModeRefusal(tool_name=tool_name)
    return json.loads(refusal.model_dump_json())


__all__ = [
    "is_probe_request",
    "enforce_probe_safe",
    "probe_refusal_payload",
]
