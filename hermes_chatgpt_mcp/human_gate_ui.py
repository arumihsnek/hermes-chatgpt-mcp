"""Non-authoritative Human Gate readback surface for the MCP App.

This module intentionally contains no mutation, authentication, registry, or DB
code. The dashboard remains the only Circle 1 authority; this surface renders
server-provided evidence and hands the human to the exact dashboard card.
"""
from __future__ import annotations

import json
from typing import Any
from urllib.parse import quote, urlsplit, urlunsplit

HUMAN_GATE_READBACK_TOOL = "get_human_gate_readback"
READBACK_STATES = frozenset({"not_authorized", "needs_input", "authorized", "expired_or_no"})
READBACK_KEYS = ("gate_state", "binding_fingerprint", "consumed_at", "consumed_by_principal", "window")


def deep_link(dashboard_origin: str, task_id: str) -> str:
    """Build a target-only link; no registry-owned or principal fields are accepted."""
    parsed = urlsplit(str(dashboard_origin).rstrip("/"))
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("dashboard origin must be an absolute HTTP(S) URL")
    safe_task = quote(str(task_id), safe="A-Za-z0-9_.:-")
    return urlunsplit((parsed.scheme, parsed.netloc, f"/tasks/{safe_task}", "", f"human-gate-{safe_task}"))


def render_readback(value: Any) -> dict[str, Any]:
    """Return only the typed, redacted readback slots, fail-closed on bad input."""
    if not isinstance(value, dict):
        value = {}
    state = value.get("gate_state")
    if state not in READBACK_STATES:
        state = "needs_input"
    fingerprint = value.get("binding_fingerprint")
    if not isinstance(fingerprint, str) or len(fingerprint) != 8 or any(c not in "0123456789abcdef" for c in fingerprint):
        fingerprint = None
    principal = value.get("consumed_by_principal")
    if principal != "user":
        principal = None
    consumed_at = value.get("consumed_at") if isinstance(value.get("consumed_at"), str) else None
    window = value.get("window")
    if not isinstance(window, dict) or not isinstance(window.get("window_start"), str) or not isinstance(window.get("window_end"), str):
        window = None
    return {"gate_state": state, "binding_fingerprint": fingerprint, "consumed_at": consumed_at,
            "consumed_by_principal": principal, "window": window}


def _json(value: Any) -> str:
    return json.dumps(value, separators=(",", ":"), ensure_ascii=True)


def build_human_gate_ui_html() -> str:
    """Return the Circle 3 UI shell with bounded, generation-safe readback polling."""
    return r'''<!DOCTYPE html>
<html lang="en" data-ui-version="v1" data-human-gate="circle-3">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'">
<meta name="referrer" content="no-referrer"><meta http-equiv="X-Frame-Options" content="DENY"><title>Hermes Human Gate readback</title>
<style>body{font:14px system-ui,sans-serif;margin:0;padding:16px;color:#202124;background:#fff}h1{font-size:18px}.banner{padding:12px;border:2px solid #b45309;background:#fff7ed;border-radius:8px;font-weight:600}.grid{display:grid;grid-template-columns:minmax(120px,180px) 1fr;gap:8px;margin:16px 0}.label{font-weight:600}.muted{color:#687078}.evidence{white-space:pre-wrap;overflow-wrap:anywhere}.handoff{display:inline-block;padding:8px 10px;border:1px solid #697386;border-radius:6px;text-decoration:none;color:inherit}.error{color:#a61b1b}</style>
</head><body>
<h1>Human Gate readback</h1>
<div id="banner" class="banner">Awaiting human authority on the dashboard. This view cannot resolve the gate.</div>
<section class="grid" aria-label="Human Gate evidence">
<div class="label">Exact card</div><div id="target" class="evidence">Loading…</div>
<div class="label">Decision state</div><div id="gate-state">needs_input</div>
<div class="label">Binding fingerprint</div><div id="fingerprint">none</div>
<div class="label">Consumed at</div><div id="consumed-at">none</div>
<div class="label">Consumed by</div><div id="consumed-by">none</div>
<div class="label">Window</div><div id="window">none</div>
<div class="label">Evidence</div><div id="evidence" class="evidence">Readback is server-provided.</div>
</section>
<a id="dashboard" class="handoff" rel="noreferrer noopener" target="_blank" hidden>Open exact card on dashboard</a>
<p id="status" class="muted">Readback only · no gate action is available here.</p>
<p class="muted">Bootstrap is out of scope; it is one-shot and extinguished.</p>
<script>(function(){"use strict";
var s={generation:0,inflight:false,attempt:0,identity:null,readback:null},states=["not_authorized","needs_input","authorized","expired_or_no"],status=document.getElementById("status");
function text(id,v){document.getElementById(id).textContent=v==null?"none":String(v);}
function call(args){if(s.inflight)return;s.inflight=true;var g=++s.generation,id=Date.now();s.attempt++;window.parent.postMessage({jsonrpc:"2.0",id:id,method:"tools/call",params:{name:"get_human_gate_readback",arguments:{request:args}}},"*");s.identity={generation:g,id:id,board:args.board||null,tenant:args.tenant||null,revision:args.revision};}
function schedule(args){if(s.attempt>=5)return;var delays=[250,500,1000,2000,4000];setTimeout(function(){call(args);},delays[s.attempt]);}
function render(d){if(!d||!s.identity||d.board!==s.identity.board||d.tenant!==s.identity.tenant||d.revision!==s.identity.revision)return;var r=d.readback||d;if(!r.gate_state)return;s.readback=r;text("target",d.task_id);text("gate-state",r.gate_state);text("fingerprint",r.binding_fingerprint||"none");text("consumed-at",r.consumed_at||"none");text("consumed-by",r.consumed_by_principal||"none");text("window",r.window?JSON.stringify(r.window):"none");if(d.evidence)text("evidence",d.evidence);if(d.deep_link){var a=document.getElementById("dashboard");a.href=d.deep_link;a.hidden=false;}if(r.gate_state!=="needs_input"&&r.gate_state!=="not_authorized")document.getElementById("banner").textContent="Gate state is authoritative on the dashboard; this view remains read-only.";}
window.addEventListener("message",function(e){var m=e.data||{};if(s.identity&&m.id&&m.id!==s.identity.id)return;s.inflight=false;if(m.error){status.className="error";status.textContent="Readback unavailable; gate remains unresolved.";return;}var d=(m.result&& (m.result.structuredContent||m.result.data))||m.result||m;if(!s.identity&&d&&d.task_id&&d.board)call({task_id:d.task_id,board:d.board,tenant:d.tenant||null,revision:Number(d.revision||0)});render(d);if(s.identity)schedule({task_id:d.task_id,board:s.identity.board,tenant:s.identity.tenant,revision:s.identity.revision});});
window.parent.postMessage({jsonrpc:"2.0",id:0,method:"ui/initialize",params:{protocolVersion:"2025-06-18"}},"*");
window.parent.postMessage({jsonrpc:"2.0",id:1,method:"ui/request-initial-data",params:{}},"*");
}());</script></body></html>'''


def readback_payload(*, task_id: str, board: str, tenant: str | None, revision: int, readback: Any,
                     dashboard_origin: str, evidence: str = "") -> dict[str, Any]:
    """Compose the server response while keeping registry secrets out of the payload."""
    return {"task_id": task_id, "board": board, "tenant": tenant, "revision": revision,
            "readback": render_readback(readback), "deep_link": deep_link(dashboard_origin, task_id),
            "evidence": evidence}
