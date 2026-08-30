from __future__ import annotations

KANBAN_UI_RESOURCE_URI = "ui://hermes/kanban/v1"
KANBAN_UI_MIME_TYPE = "text/html;profile=mcp-app"
KANBAN_UI_MAX_BYTES = 262_144
KANBAN_UI_RESOURCE_URI_V2 = "ui://hermes/kanban/v2"
KANBAN_UI_RESOURCE_URI_INTERACTIVE_R1 = "ui://hermes/kanban/interactive-r1"
HUMAN_GATE_RESOURCE_URI = "ui://hermes/human-gate/v1"

KANBAN_UI_HTML_V1 = r'''<!DOCTYPE html>
<html lang="en" data-ui-version="v1">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'"><meta name="referrer" content="no-referrer"><meta http-equiv="X-Frame-Options" content="DENY">
<title>Hermes Kanban board</title>
<style>
:root{color-scheme:light dark;font:14px system-ui,sans-serif}body{margin:0;padding:12px;color:#202124;background:#fff}header{display:flex;align-items:center;gap:10px;border-bottom:1px solid #ccd0d5;padding-bottom:10px}h1{font-size:18px;margin:0;flex:1}button,select{font:inherit;padding:6px 9px;border:1px solid #9aa0a6;border-radius:6px;background:#fff;color:inherit}#board{margin:12px 0;font-weight:600}.columns{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:8px}.column{min-height:70px;padding:8px;border:1px solid #d7dbe0;border-radius:8px;background:#f7f8f9}.column h2{font-size:13px;margin:0 0 8px;text-transform:capitalize}.count{font-size:24px}.cards{display:grid;gap:6px;margin-top:12px}.card{padding:8px;border:1px solid #d7dbe0;border-radius:6px}.muted{color:#687078;font-size:12px}.error{color:#a61b1b}
</style></head>
<body>
<header><h1>Hermes Kanban</h1><label for="board-picker">Board</label><select id="board-picker" aria-label="Board"></select><button id="refresh" type="button">Refresh</button></header>
<div id="board" class="muted">Loading board…</div><section id="columns" class="columns" aria-label="Status columns"></section><section id="cards" class="cards" aria-label="Cards"></section><p id="status" class="muted">Read-only view</p>
<script>
(function(){
  var state={board:null,boards:[],request:0};
  var picker=document.getElementById("board-picker"), boardNode=document.getElementById("board"), columns=document.getElementById("columns"), cards=document.getElementById("cards"), status=document.getElementById("status");
  function text(node,value){node.textContent=value==null?"":String(value);}
  function node(tag,cls,value){var el=document.createElement(tag);if(cls)el.className=cls;if(value!=null)text(el,value);return el;}
  function call(name,args){var id=++state.request;window.parent.postMessage({jsonrpc:"2.0",id:id,method:"tools/call",params:{name:name,arguments:args||{}}},"*");}
  function selected(){return picker.value||null;}
  function renderBoards(data){
    var items=(data&&data.items)||[]; state.boards=items; while(picker.firstChild)picker.removeChild(picker.firstChild);
    items.forEach(function(item){var option=node("option",null,item.name||item.slug);option.value=item.slug;picker.appendChild(option);});
    var wanted=state.board||(data&&data.default_board)||(items[0]&&items[0].slug); if(wanted){picker.value=wanted;state.board=wanted;}
  }
  function renderBoard(data){
    state.board=(data&&data.board)||selected()||state.board; text(boardNode,"Board: "+(state.board||"unspecified"));
    while(columns.firstChild)columns.removeChild(columns.firstChild);
    var counts=(data&&data.task_counts)||{}; ["triage","todo","ready","running","blocked","review","done"].forEach(function(key){var col=node("article","column"),heading=node("h2",null,key),count=node("div","count",counts[key]||0);col.appendChild(heading);col.appendChild(count);columns.appendChild(col);});
    text(status,"Read-only view · refreshed "+new Date().toLocaleTimeString());
  }
  function renderCards(data){
    while(cards.firstChild)cards.removeChild(cards.firstChild); var items=(data&&data.items)||[];
    items.forEach(function(item){var card=node("article","card"),title=node("strong",null,item.title||item.task_id||"Untitled card"),meta=node("div","muted",(item.task_id||item.id||"")+" · "+(item.status||""));card.appendChild(title);card.appendChild(meta);cards.appendChild(card);});
  }
  function refresh(){status.className="muted";text(status,"Refreshing…");call("get_board",{request:{board:selected()}});call("list_tasks",{request:{board:selected(),limit:100,order_by:"priority"}});}
  picker.addEventListener("change",function(){state.board=selected();refresh();}); document.getElementById("refresh").addEventListener("click",refresh);
  window.addEventListener("message",function(event){var message=event.data||{},result=message.result||message; if(message.method==="ui/notifications/tool-result")result=message.params||{}; if(message.error){status.className="error";text(status,"Unable to refresh board");return;} var data=result.structuredContent||result.data||result; if(data.items&&data.default_board)renderBoards(data); else if(data.items)renderCards(data); else if(data.task_counts||data.counts)renderBoard(data);});
  window.parent.postMessage({jsonrpc:"2.0",id:0,method:"ui/initialize",params:{protocolVersion:"2025-06-18"}},"*"); call("list_boards",{}); refresh();
}());
</script></body></html>'''


def build_kanban_ui_html() -> str:
    html = KANBAN_UI_HTML_V1
    if len(html.encode("utf-8")) > KANBAN_UI_MAX_BYTES:
        raise ValueError("Kanban UI resource exceeds size limit")
    return html


KANBAN_UI_HTML_V2 = r'''<!DOCTYPE html>
<html lang="en" data-ui-version="v2">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'"><meta name="referrer" content="no-referrer"><meta http-equiv="X-Frame-Options" content="DENY">
<title>Hermes Kanban board</title>
<style>
:root{color-scheme:light dark;font:14px system-ui,sans-serif}body{margin:0;padding:12px;color:#202124;background:#fff}header{display:flex;align-items:center;gap:10px;border-bottom:1px solid #ccd0d5;padding-bottom:10px}h1{font-size:18px;margin:0;flex:1}#status{margin:12px 0}.form-section{margin:12px 0}.form-section label{font-weight:600;display:block;margin-bottom:4px}.form-section input,.form-section textarea{font:inherit;padding:6px 9px;border:1px solid #9aa0a6;border-radius:6px;background:#fff;color:inherit;width:100%;box-sizing:border-box}.muted{color:#687078;font-size:12px}.error{color:#a61b1b}
</style></head>
<body>
<header><h1>Hermes Kanban</h1><span id="revision" class="muted">revision: pending readback</span></header>
<p id="status">Canonical readback required.</p>
<form id="create" class="form-section"><label class="form-section">Title <input name="title" required maxlength="512"></label>
<label class="form-section">Body <textarea name="body" maxlength="64000"></textarea></label>
<button id="submit" type="submit" disabled>Create task</button></form>
<p class="muted">Read-only board view is available at the V1 resource.</p>
<script>
(function(){
"use strict";
var f=document.getElementById("create"),s=document.getElementById("status"),revNode=document.getElementById("revision"),btn=document.getElementById("submit");
var state={submitInFlight:false,nextId:0,pendingSubmit:0,pendingRead:0,revision:null};
function genIdempotencyKey(){return "ui-"+crypto.randomUUID();}
function setStatus(text,isError){s.className=isError?"error":"muted";s.textContent=text;}
function applyRevision(value){if(typeof value!=="number"||value<0)return;state.revision=value;revNode.textContent="revision: "+value;btn.disabled=state.submitInFlight||false;}
function postCall(method,params,id){window.parent.postMessage({jsonrpc:"2.0",id:id,method:method,params:params},"*");}
function resultOf(message){var r=message.result||{};return r.structuredContent||r.data||r;}
function nextId(){return ++state.nextId;}
f.addEventListener("submit",function(e){
  e.preventDefault();
  if(state.submitInFlight){setStatus("Another request is in flight; please wait.",true);return;}
  if(state.revision===null){setStatus("Board revision not yet read; first create will follow readback.",true);return;}
  state.submitInFlight=true; btn.disabled=true; setStatus("Awaiting host consent…",false);
  var payload={request:{title:f.title.value,body:f.body.value||null,idempotency_key:genIdempotencyKey(),expected_board_revision:state.revision}};
  state.pendingSubmit=nextId();
  postCall("tools/call",{name:"create_task",arguments:payload},state.pendingSubmit);
});
window.addEventListener("message",function(e){
  var m=e.data||{}; if(!m.id)return;
  if(m.id===state.pendingRead){
    if(m.error){setStatus("Could not read current board revision; first create will be stale.",true);return;}
    var data=resultOf(m);
    if(data&&typeof data.board_revision==="number"){applyRevision(data.board_revision);setStatus("Canonical readback required.",false);}
    return;
  }
  if(m.id===state.pendingSubmit){
    state.submitInFlight=false; btn.disabled=false; state.pendingSubmit=0;
    if(m.error){setStatus("Create failed: "+(m.error.message||"host error"),true);return;}
    var r=resultOf(m);
    if(r&&typeof r.board_revision==="number"){applyRevision(r.board_revision);}
    if(r&&r.task_id){setStatus("Created task "+r.task_id+" (revision "+state.revision+").",false);f.reset();return;}
    setStatus("Create response missing task id.",true);
  }
});
// Initialize: ask the host for current board so we can prime expected_board_revision.
postCall("ui/initialize",{protocolVersion:"2025-06-18"},nextId());
state.pendingRead=nextId();
postCall("tools/call",{name:"get_board",arguments:{request:{}}},state.pendingRead);
}());
</script></body></html>'''


def build_kanban_ui_v2_html() -> str:
    """Minimal write-capable shell; all authority stays in the host bridge."""
    html = KANBAN_UI_HTML_V2
    if len(html.encode("utf-8")) > KANBAN_UI_MAX_BYTES:
        raise ValueError("Kanban UI resource exceeds size limit")
    return html


KANBAN_UI_HTML_INTERACTIVE_R1 = r'''<!DOCTYPE html>
<html lang="en" data-ui-version="interactive-r1">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'"><meta name="referrer" content="no-referrer"><meta http-equiv="X-Frame-Options" content="DENY">
<title>Hermes Kanban interactive</title>
<style>
:root{color-scheme:light dark;font:14px system-ui,sans-serif}*{box-sizing:border-box}body{margin:0;padding:12px;color:#202124;background:#fff}header{display:flex;align-items:center;gap:8px;flex-wrap:wrap;border-bottom:1px solid #ccd0d5;padding-bottom:10px}h1{font-size:18px;margin:0;flex:1}button,select,input,textarea{font:inherit;border:1px solid #9aa0a6;border-radius:6px;background:#fff;color:inherit}button,select,input{padding:6px 9px}button[disabled]{opacity:.45}textarea{padding:8px;width:100%;min-height:72px}.columns{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:8px;margin:12px 0}.column{padding:8px;border:1px solid #d7dbe0;border-radius:8px;background:#f7f8f9}.column h2{font-size:12px;margin:0;text-transform:capitalize}.count{font-size:22px}.layout{display:grid;grid-template-columns:minmax(220px,1fr) minmax(260px,1fr);gap:10px}.cards,.panel{display:grid;gap:6px}.card,.panel{padding:9px;border:1px solid #d7dbe0;border-radius:8px}.card{cursor:pointer}.card[aria-selected="true"]{outline:2px solid currentColor}.row{display:flex;gap:6px;align-items:center;flex-wrap:wrap}.row>*{min-width:0}.grow{flex:1}.muted{color:#687078;font-size:12px}.error{color:#a61b1b}.ok{color:#176b32}.banner{padding:7px;border:1px solid #d7dbe0;border-radius:6px;margin:10px 0}.hidden{display:none}@media(max-width:720px){.layout{grid-template-columns:1fr}}
</style></head>
<body>
<header><h1>Hermes Kanban</h1><select id="board-picker" aria-label="Board"></select><button id="refresh" type="button">Refresh</button><button id="live" type="button">Live sync (60s)</button><button id="create-toggle" type="button">Create card</button></header>
<div id="status" class="banner muted">Loading canonical board…</div>
<section id="create-panel" class="panel hidden"><strong>Create card</strong><label>Title <input id="create-title" maxlength="512"></label><label>Body <textarea id="create-body" maxlength="64000"></textarea></label><div class="row"><button id="create-submit" type="button">Create</button><button id="create-cancel" type="button">Cancel</button></div></section>
<section id="columns" class="columns" aria-label="Status counts"></section>
<div class="layout"><section id="cards" class="cards" aria-label="Cards"></section><aside id="inspector" class="panel"><strong>Inspector</strong><p class="muted">Select a card.</p></aside></div>
<script>
(function(){
"use strict";
var LIVE_INTERVAL_MS=3000,MAX_LIVE_CYCLES=20,LIVE_MAX_MS=60000;
var state={board:null,boards:[],tasks:[],selected:null,request:0,pending:{},inflightMutation:false,liveTimer:null,liveCycles:0,liveDeadline:0};
var picker=document.getElementById("board-picker"),columns=document.getElementById("columns"),cards=document.getElementById("cards"),inspector=document.getElementById("inspector"),status=document.getElementById("status"),liveBtn=document.getElementById("live"),createPanel=document.getElementById("create-panel");
function text(n,v){n.textContent=v==null?"":String(v)}
function node(tag,cls,value){var e=document.createElement(tag);if(cls)e.className=cls;if(value!=null)text(e,value);return e}
function setStatus(v,kind){status.className="banner "+(kind||"muted");text(status,v)}
function selectedBoard(){return picker.value||state.board||null}
function nextId(){return ++state.request}
function call(name,args,kind){var id=nextId();state.pending[id]={name:name,kind:kind||name};window.parent.postMessage({jsonrpc:"2.0",id:id,method:"tools/call",params:{name:name,arguments:args||{}}},"*");return id}
function resultOf(m){var r=m.result||m.params||m;return r.structuredContent||r.data||r}
function refresh(includeTask){var b=selectedBoard();call("get_board",{request:{board:b}},"board");call("list_tasks",{request:{board:b,limit:100,order_by:"priority"}},"tasks");if(includeTask&&state.selected)call("get_task",{request:{board:b,task_id:state.selected}},"task")}
function renderBoards(d){var items=(d&&d.items)||[];state.boards=items;while(picker.firstChild)picker.removeChild(picker.firstChild);items.forEach(function(it){var o=node("option",null,it.name||it.slug);o.value=it.slug;picker.appendChild(o)});var wanted=state.board||(d&&d.default_board)||(items[0]&&items[0].slug);if(wanted){picker.value=wanted;state.board=wanted}}
function renderBoard(d){state.board=(d&&d.slug)||selectedBoard()||state.board;while(columns.firstChild)columns.removeChild(columns.firstChild);var counts=(d&&d.task_counts)||{};["triage","todo","ready","running","blocked","review","done"].forEach(function(k){var c=node("article","column"),h=node("h2",null,k),n=node("div","count",counts[k]||0);c.appendChild(h);c.appendChild(n);columns.appendChild(c)});setStatus("Canonical board refreshed · "+new Date().toLocaleTimeString(),"ok")}
function renderTasks(d){state.tasks=(d&&d.items)||[];while(cards.firstChild)cards.removeChild(cards.firstChild);state.tasks.forEach(function(it){var id=it.task_id||it.id,card=node("article","card"),title=node("strong",null,it.title||id),meta=node("div","muted",id+" · "+(it.status||"")+" · "+(it.assignee||"unassigned"));card.dataset.id=id;card.setAttribute("aria-selected",String(id===state.selected));card.appendChild(title);card.appendChild(meta);card.addEventListener("click",function(){state.selected=id;renderTasks({items:state.tasks});call("get_task",{request:{board:selectedBoard(),task_id:id}},"task")});cards.appendChild(card)})}
function actionButton(label,fn,disabled){var b=node("button",null,label);b.type="button";b.disabled=!!disabled;b.addEventListener("click",fn);return b}
function mutate(name,args,taskId){if(state.inflightMutation){setStatus("Another mutation is in flight.","error");return}state.inflightMutation=true;setStatus("Action in flight — canonical readback required…","muted");call(name,args,"mutation:"+(taskId||""))}
function renderTask(t){while(inspector.firstChild)inspector.removeChild(inspector.firstChild);if(!t){inspector.appendChild(node("p","muted","Task readback unavailable."));return}state.selected=t.id||t.task_id||state.selected;inspector.appendChild(node("strong",null,t.title||state.selected));inspector.appendChild(node("div","muted",state.selected+" · "+(t.status||"")+" · "+(t.assignee||"unassigned")));if(t.body)inspector.appendChild(node("p",null,t.body));var comment=node("textarea");comment.placeholder="Comment";inspector.appendChild(comment);inspector.appendChild(actionButton("Add comment",function(){var v=comment.value.trim();if(!v)return;mutate("add_comment",{request:{board:selectedBoard(),task_id:state.selected,body:v}},state.selected)}));var assignRow=node("div","row"),assignee=node("input","grow");assignee.placeholder="Assignee profile";assignRow.appendChild(assignee);assignRow.appendChild(actionButton("Assign",function(){var v=assignee.value.trim();if(!v)return;mutate("assign_task",{request:{board:selectedBoard(),task_id:state.selected,assignee:v}},state.selected)}));inspector.appendChild(assignRow);var reason=node("input","grow");reason.placeholder="Reason (optional except changes)";inspector.appendChild(reason);var actions=node("div","row"),st=t.status||"";if(st==="blocked")actions.appendChild(actionButton("Unblock",function(){mutate("unblock_tasks",{request:{board:selectedBoard(),task_ids:[state.selected],reason:reason.value||"Unblocked from MCP Apps UI"}},state.selected)}));else actions.appendChild(actionButton("Block",function(){mutate("block_tasks",{request:{board:selectedBoard(),task_ids:[state.selected],kind:"manual",reason:reason.value||"Blocked from MCP Apps UI"}},state.selected)},st==="done"));actions.appendChild(actionButton("Request review",function(){mutate("request_review",{request:{board:selectedBoard(),task_id:state.selected,summary:reason.value||"Requested from MCP Apps UI",reviewer:"reviewer"}},state.selected)},st==="done"||st==="review"));actions.appendChild(actionButton("Request changes",function(){var r=reason.value.trim();if(!r){setStatus("Request changes requires a reason.","error");return}mutate("request_changes",{request:{board:selectedBoard(),task_id:state.selected,reason:r}},state.selected)},st!=="review"));actions.appendChild(actionButton("Reopen review",function(){mutate("reopen_review",{request:{board:selectedBoard(),task_ids:[state.selected],reason:reason.value||"Reopened from MCP Apps UI"}},state.selected)},st!=="review"));inspector.appendChild(actions);inspector.appendChild(node("p","muted","No complete/archive/delete/Human-Gate decision controls are exposed in Interactive R1."))}
function reconcile(taskId){state.inflightMutation=false;refresh(false);if(taskId)call("get_task",{request:{board:selectedBoard(),task_id:taskId}},"task");setStatus("Tool returned; reconciling canonical state…","muted")}
function stopLive(){if(state.liveTimer){clearInterval(state.liveTimer);state.liveTimer=null}state.liveCycles=0;liveBtn.textContent="Live sync (60s)"}
function liveTick(){if(document.hidden)return;if(Date.now()>state.liveDeadline||state.liveCycles>=MAX_LIVE_CYCLES){stopLive();return}state.liveCycles++;refresh(true)}
function startLive(){if(state.liveTimer){stopLive();return}state.liveCycles=0;state.liveDeadline=Date.now()+LIVE_MAX_MS;liveBtn.textContent="Stop live sync";liveTick();state.liveTimer=setInterval(liveTick,LIVE_INTERVAL_MS)}
picker.addEventListener("change",function(){state.board=selectedBoard();state.selected=null;refresh(false);renderTask(null)});document.getElementById("refresh").addEventListener("click",function(){refresh(true)});liveBtn.addEventListener("click",startLive);document.addEventListener("visibilitychange",function(){if(document.hidden)stopLive()});window.addEventListener("unload",stopLive);
document.getElementById("create-toggle").addEventListener("click",function(){createPanel.classList.remove("hidden")});document.getElementById("create-cancel").addEventListener("click",function(){createPanel.classList.add("hidden")});document.getElementById("create-submit").addEventListener("click",function(){var title=document.getElementById("create-title").value.trim(),body=document.getElementById("create-body").value;if(!title){setStatus("Title is required.","error");return}mutate("create_task",{request:{board:selectedBoard(),title:title,body:body||null,idempotency_key:"ui-"+crypto.randomUUID()}},null)});
window.addEventListener("message",function(e){var m=e.data||{};if(m.method==="ui/notifications/tool-result"&&m.params)m=m.params;var p=state.pending[m.id];if(!p)return;delete state.pending[m.id];if(m.error){if(p.kind.indexOf("mutation:")===0)state.inflightMutation=false;setStatus((p.name||"Tool")+" failed: "+(m.error.message||"host error"),"error");refresh(true);return}var d=resultOf(m);if(p.kind==="boards")renderBoards(d);else if(p.kind==="board")renderBoard(d);else if(p.kind==="tasks")renderTasks(d);else if(p.kind==="task")renderTask(d);else if(p.kind.indexOf("mutation:")===0)reconcile(p.kind.slice(9));});
window.parent.postMessage({jsonrpc:"2.0",id:0,method:"ui/initialize",params:{protocolVersion:"2025-06-18"}},"*");call("list_boards",{},"boards");refresh(false);
}());
</script></body></html>'''


def build_kanban_ui_interactive_r1_html() -> str:
    """Bounded shared-control UI using only canonical host-bridged Hermes tools."""
    html = KANBAN_UI_HTML_INTERACTIVE_R1
    if len(html.encode("utf-8")) > KANBAN_UI_MAX_BYTES:
        raise ValueError("Kanban UI resource exceeds size limit")
    return html


# Reuse the canonical, well-formed Human Gate readback HTML from human_gate_ui.
# Keeping a thin wrapper here preserves the ui.py public surface for existing
# importers without duplicating the (lengthy) HTML literal in two places.
from .human_gate_ui import build_human_gate_ui_html as _canonical_human_gate_html  # noqa: E402


def build_human_gate_ui_html() -> str:
    """Circle-3 Human Gate readback surface (separate URI from V1 Kanban)."""
    html = _canonical_human_gate_html()
    if len(html.encode("utf-8")) > KANBAN_UI_MAX_BYTES:
        raise ValueError("Kanban UI resource exceeds size limit")
    return html
