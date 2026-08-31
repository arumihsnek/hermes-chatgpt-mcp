from __future__ import annotations

KANBAN_UI_RESOURCE_URI = "ui://hermes/kanban/v1"
KANBAN_UI_MIME_TYPE = "text/html;profile=mcp-app"
KANBAN_UI_MAX_BYTES = 262_144
KANBAN_UI_RESOURCE_URI_V2 = "ui://hermes/kanban/v2"
KANBAN_UI_RESOURCE_URI_INTERACTIVE_R1 = "ui://hermes/kanban/interactive-r1"
KANBAN_UI_RESOURCE_URI_INTERACTIVE_R14 = "ui://hermes/kanban/interactive-r14-fresh-tool"
KANBAN_UI_RESOURCE_URI_INTERACTIVE_R16 = "ui://hermes/kanban/interactive-r16-ux"
KANBAN_UI_RESOURCE_URI_INTERACTIVE_R162 = "ui://hermes/kanban/interactive-r162-mobile-workbench"
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
<html lang="en" data-ui-version="interactive-r1.1">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'"><meta name="referrer" content="no-referrer"><meta http-equiv="X-Frame-Options" content="DENY">
<title>Hermes Kanban interactive</title>
<style>
:root{color-scheme:light dark;font:14px system-ui,sans-serif;--line:#d7dbe0;--muted:#687078;--accent:#315efb;--warn:#b7791f;--soft:#f7f8f9}*{box-sizing:border-box}body{margin:0;padding:12px 12px 72px;color:#202124;background:#fff}header{display:flex;align-items:center;gap:8px;flex-wrap:wrap;border-bottom:1px solid #ccd0d5;padding-bottom:9px}h1{font-size:18px;margin:0;flex:1}button,select,input,textarea{font:inherit;border:1px solid #9aa0a6;border-radius:7px;background:#fff;color:inherit}button,select,input{padding:6px 9px}button[disabled]{opacity:.45}textarea{padding:8px;width:100%;min-height:72px}.banner{padding:7px 9px;border:1px solid var(--line);border-radius:7px;margin:9px 0}.muted{color:var(--muted);font-size:12px}.error{color:#a61b1b}.ok{color:#176b32}.hidden{display:none!important}.row{display:flex;gap:6px;align-items:center;flex-wrap:wrap}.grow{flex:1;min-width:0}.panel{padding:9px;border:1px solid var(--line);border-radius:9px;background:#fff}.status-strip{display:flex;gap:6px;overflow-x:auto;white-space:nowrap;padding:2px 0 8px;scrollbar-width:thin}.status-toggle{display:inline-flex;gap:5px;align-items:center;border-radius:999px;padding:5px 9px;flex:0 0 auto;background:#fff}.status-toggle[aria-pressed="true"]{border-color:var(--accent);box-shadow:inset 0 0 0 1px var(--accent)}.status-toggle.dep-hidden{border-color:var(--warn);box-shadow:0 0 0 2px color-mix(in srgb,var(--warn) 24%,transparent)}.status-toggle.dep-visible{box-shadow:inset 0 0 0 1px var(--accent)}.status-toggle.pending-target{background:#eef2ff}.toggle-count{font-weight:700}.dep-marker{font-size:10px;font-weight:700;color:var(--warn)}.board-columns{display:grid;grid-template-columns:repeat(var(--visible-cols,3),minmax(220px,1fr));gap:9px;align-items:start}.kanban-column{min-width:0;border:1px solid var(--line);border-radius:10px;background:var(--soft);padding:8px;min-height:110px}.kanban-column.pending-incoming{border-color:var(--accent);box-shadow:inset 0 0 0 1px color-mix(in srgb,var(--accent) 50%,transparent)}.column-head{display:flex;align-items:center;gap:6px;margin-bottom:7px}.column-head strong{font-size:12px}.pending-incoming-badge{margin-left:auto;font-size:10px;color:var(--accent)}.column-cards{display:grid;gap:6px}.card{position:relative;padding:9px;border:1px solid var(--line);border-radius:8px;background:#fff;cursor:pointer;touch-action:manipulation;transition:box-shadow .12s,border-color .12s,transform .12s}.card:hover{border-color:#9aa0a6}.card[aria-selected="true"]{outline:2px solid currentColor}.card.dep-source{box-shadow:0 0 0 2px color-mix(in srgb,var(--accent) 35%,transparent)}.card.dep-highlight{border-color:var(--warn);box-shadow:0 0 0 2px color-mix(in srgb,var(--warn) 28%,transparent)}.card.staged{border-style:dashed;border-color:var(--accent);background:linear-gradient(135deg,#fff 0,#fff 86%,#eef2ff 86%)}.pending-badge{display:inline-flex;margin-top:6px;padding:3px 7px;border-radius:999px;background:#eef2ff;color:#2546b8;font-size:10px;font-weight:700}.card-meta{margin-top:3px}.empty{padding:12px 4px;text-align:center}.layout{display:grid;grid-template-columns:minmax(260px,1fr);gap:10px;margin-top:10px}.inspector{display:grid;gap:7px}.confirm-bar{position:fixed;left:12px;right:12px;bottom:10px;z-index:10;display:flex;align-items:center;gap:8px;padding:9px 10px;border:1px solid #8ea2ff;border-radius:10px;background:#fff;box-shadow:0 8px 30px rgba(0,0,0,.16)}.confirm-bar strong{flex:1}.confirm-primary{background:#315efb;color:#fff;border-color:#315efb}.staged-list{font-size:11px;color:var(--muted);max-width:46vw;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}@media(max-width:760px){body{padding:10px 10px 76px}.board-columns{display:grid;grid-auto-flow:column;grid-auto-columns:minmax(82vw,1fr);grid-template-columns:none;overflow-x:auto;scroll-snap-type:x proximity;padding-bottom:5px}.kanban-column{scroll-snap-align:start}.confirm-bar{left:8px;right:8px;bottom:8px}.staged-list{display:none}header h1{flex-basis:100%}}
</style></head>
<body>
<header><h1>Hermes Kanban</h1><select id="board-picker" aria-label="Board"></select><button id="refresh" type="button">Refresh</button><button id="live" type="button">Live sync (60s)</button><button id="create-toggle" type="button">Create card</button></header>
<div id="status" class="banner muted">Loading canonical board…</div>
<section id="create-panel" class="panel hidden"><strong>Create card</strong><label>Title <input id="create-title" maxlength="512"></label><label>Body <textarea id="create-body" maxlength="64000"></textarea></label><div class="row"><button id="create-submit" type="button">Mark create</button><button id="create-cancel" type="button">Cancel</button></div></section>
<nav id="status-strip" class="status-strip" aria-label="Visible status columns"></nav>
<section id="board-columns" class="board-columns" aria-label="Kanban columns"></section>
<div class="layout"><aside id="inspector" class="panel inspector"><strong>Inspector</strong><p class="muted">Select a card.</p></aside></div>
<div id="confirm-bar" class="confirm-bar hidden" role="region" aria-label="Pending actions"><strong id="confirm-count">0 pending</strong><span id="staged-list" class="staged-list"></span><button id="undo-all" type="button">Undo</button><button id="confirm-all" class="confirm-primary" type="button">Confirm</button></div>
<script>
(function(){
"use strict";
var LIVE_INTERVAL_MS=3000,MAX_LIVE_CYCLES=20,LIVE_MAX_MS=60000;
var STATUS_ORDER=["triage","todo","ready","running","blocked","review","scheduled","done"],STATUS_LABEL={triage:"Triage",todo:"Todo",ready:"Ready",running:"In progress",blocked:"Blocked",review:"Review",scheduled:"Scheduled",done:"Done"};
var state={board:null,boards:[],counts:{},tasksByStatus:{},selected:null,selectedTask:null,visible:{todo:true,ready:true,running:true},request:0,pending:{},graphs:{},hovered:null,staged:{},confirmQueue:[],activeAction:null,inflightMutation:false,liveTimer:null,liveCycles:0,liveDeadline:0};
var picker=document.getElementById("board-picker"),strip=document.getElementById("status-strip"),columns=document.getElementById("board-columns"),inspector=document.getElementById("inspector"),status=document.getElementById("status"),liveBtn=document.getElementById("live"),createPanel=document.getElementById("create-panel"),confirmBar=document.getElementById("confirm-bar"),confirmCount=document.getElementById("confirm-count"),stagedList=document.getElementById("staged-list");
function text(n,v){n.textContent=v==null?"":String(v)}
function node(tag,cls,value){var e=document.createElement(tag);if(cls)e.className=cls;if(value!=null)text(e,value);return e}
function setStatus(v,kind){status.className="banner "+(kind||"muted");text(status,v)}
function selectedBoard(){return picker.value||state.board||null}
function nextId(){return ++state.request}
function call(name,args,kind,meta){var id=nextId();state.pending[id]={name:name,kind:kind||name,meta:meta||null};window.parent.postMessage({jsonrpc:"2.0",id:id,method:"tools/call",params:{name:name,arguments:args||{}}},"*");return id}
function resultOf(m){var r=m.result||m.params||m;return r.structuredContent||r.data||r}
function visibleStatuses(){return STATUS_ORDER.filter(function(k){return !!state.visible[k]})}
function loadStatus(k){call("list_tasks",{request:{board:selectedBoard(),status:k,limit:100,order_by:"priority"}},"tasks:"+k)}
function refresh(includeTask){var b=selectedBoard();call("get_board",{request:{board:b}},"board");visibleStatuses().forEach(loadStatus);if(includeTask&&state.selected)call("get_task",{request:{board:b,task_id:state.selected}},"task")}
function renderBoards(d){var items=(d&&d.items)||[];state.boards=items;while(picker.firstChild)picker.removeChild(picker.firstChild);items.forEach(function(it){var o=node("option",null,it.name||it.slug);o.value=it.slug;picker.appendChild(o)});var wanted=state.board||(d&&d.default_board)||(items[0]&&items[0].slug);if(wanted){picker.value=wanted;state.board=wanted}}
function ensureToggle(k){return Array.prototype.find.call(strip.querySelectorAll(".status-toggle"),function(b){return b.dataset.status===k})}
function clearDependencyHighlights(){Array.prototype.forEach.call(columns.querySelectorAll(".card"),function(c){c.classList.remove("dep-highlight","dep-source")});Array.prototype.forEach.call(strip.querySelectorAll(".status-toggle"),function(b){b.classList.remove("dep-hidden","dep-visible");var m=b.querySelector(".dep-marker");if(m)m.remove()})}
function renderStatusStrip(){while(strip.firstChild)strip.removeChild(strip.firstChild);STATUS_ORDER.forEach(function(k){var b=node("button","status-toggle"),label=node("span",null,STATUS_LABEL[k]||k),count=node("span","toggle-count",state.counts[k]||0);b.type="button";b.dataset.status=k;b.setAttribute("aria-pressed",String(!!state.visible[k]));b.appendChild(label);b.appendChild(count);b.addEventListener("click",function(){state.visible[k]=!state.visible[k];b.setAttribute("aria-pressed",String(!!state.visible[k]));if(state.visible[k]&&!state.tasksByStatus[k])loadStatus(k);renderColumns();applyDependencyHighlight(state.hovered||state.selected)});strip.appendChild(b)});renderPendingTargets()}
function renderBoard(d){state.board=(d&&d.slug)||selectedBoard()||state.board;state.counts=(d&&d.task_counts)||{};renderStatusStrip();setStatus("Canonical board refreshed · "+new Date().toLocaleTimeString(),"ok")}
function stagedForTask(id){return state.staged[id]||null}
function incomingCount(k){var n=0;Object.keys(state.staged).forEach(function(key){if(state.staged[key].targetStatus===k)n++});return n}
function cardForId(id){var found=null;Array.prototype.some.call(columns.querySelectorAll(".card"),function(c){if(c.dataset.id===id){found=c;return true}return false});return found}
function stageLabel(a){return a.targetStatus?"→ "+(STATUS_LABEL[a.targetStatus]||a.targetStatus):a.label}
function renderColumns(){while(columns.firstChild)columns.removeChild(columns.firstChild);var visible=visibleStatuses();columns.style.setProperty("--visible-cols",String(Math.max(1,visible.length)));visible.forEach(function(k){var col=node("article","kanban-column"),head=node("div","column-head"),title=node("strong",null,STATUS_LABEL[k]||k),incoming=incomingCount(k),wrap=node("div","column-cards");col.dataset.status=k;head.appendChild(title);if(incoming){col.classList.add("pending-incoming");head.appendChild(node("span","pending-incoming-badge","+"+incoming+" pending"))}col.appendChild(head);var items=state.tasksByStatus[k]||[];if(!items.length)wrap.appendChild(node("div","empty muted","No cards"));items.forEach(function(it){var id=it.task_id||it.id,card=node("article","card"),strong=node("strong",null,it.title||id),meta=node("div","muted card-meta",id+" · "+(it.assignee||"unassigned")),staged=stagedForTask(id);card.dataset.id=id;card.dataset.status=k;card.tabIndex=0;card.setAttribute("aria-selected",String(id===state.selected));card.appendChild(strong);card.appendChild(meta);if(staged){card.classList.add("staged");card.appendChild(node("span","pending-badge",stageLabel(staged)))}card.addEventListener("pointerenter",function(){state.hovered=id;ensureGraph(id);applyDependencyHighlight(id)});card.addEventListener("pointerleave",function(){state.hovered=null;applyDependencyHighlight(state.selected)});card.addEventListener("focus",function(){state.hovered=id;ensureGraph(id);applyDependencyHighlight(id)});card.addEventListener("touchstart",function(){state.hovered=id;ensureGraph(id);applyDependencyHighlight(id)},{passive:true});card.addEventListener("click",function(){state.selected=id;state.hovered=id;renderColumns();ensureGraph(id);applyDependencyHighlight(id);call("get_task",{request:{board:selectedBoard(),task_id:id}},"task")});wrap.appendChild(card)});col.appendChild(wrap);columns.appendChild(col)});renderPendingTargets()}
function renderPendingTargets(){Array.prototype.forEach.call(strip.querySelectorAll(".status-toggle"),function(b){b.classList.toggle("pending-target",incomingCount(b.dataset.status)>0)})}
function graphDependencies(d){var root=(d&&d.root_task_id)||null,nodes=(d&&d.nodes)||[],rootNode=null;nodes.forEach(function(n){if(n.id===root)rootNode=n});if(!rootNode)return[];var out=[];(rootNode.parents||[]).forEach(function(x){out.push({id:x.id,status:x.status,kind:"parent"})});(rootNode.children||[]).forEach(function(x){out.push({id:x.id,status:x.status,kind:"child"})});return out}
function ensureGraph(id){if(!id||state.graphs[id])return;call("get_task_graph",{request:{board:selectedBoard(),task_id:id,depth:1,max_nodes:64}},"graph",{taskId:id})}
function applyDependencyHighlight(id){clearDependencyHighlights();if(!id)return;var source=cardForId(id);if(source)source.classList.add("dep-source");var deps=state.graphs[id]||[],hiddenCounts={};deps.forEach(function(dep){if(state.visible[dep.status]){var c=cardForId(dep.id);if(c)c.classList.add("dep-highlight");var vb=ensureToggle(dep.status);if(vb)vb.classList.add("dep-visible")}else{hiddenCounts[dep.status]=(hiddenCounts[dep.status]||0)+1}});Object.keys(hiddenCounts).forEach(function(k){var b=ensureToggle(k);if(!b)return;b.classList.add("dep-hidden");b.appendChild(node("span","dep-marker","↗"+hiddenCounts[k]))})}
function actionButton(label,fn,disabled){var b=node("button",null,label);b.type="button";b.disabled=!!disabled;b.addEventListener("click",fn);return b}
function stageAction(action){var key=action.taskId||("create:"+crypto.randomUUID());action.key=key;state.staged[key]=action;renderColumns();renderConfirmBar();if(action.taskId&&state.selected===action.taskId)renderTask(state.selectedTask);setStatus("Action marked — confirm to apply canonical mutation.","muted")}
function clearStaged(key){delete state.staged[key];renderColumns();renderConfirmBar();if(state.selected)renderTask(state.selectedTask)}
function renderConfirmBar(){var keys=Object.keys(state.staged),labels=keys.map(function(k){return stageLabel(state.staged[k])});confirmBar.classList.toggle("hidden",keys.length===0);text(confirmCount,keys.length+" pending action"+(keys.length===1?"":"s"));text(stagedList,labels.join(" · "));document.getElementById("confirm-all").disabled=state.inflightMutation||keys.length===0;document.getElementById("undo-all").disabled=state.inflightMutation||keys.length===0}
function confirmStaged(){if(state.inflightMutation){setStatus("Another mutation is in flight.","error");return}state.confirmQueue=Object.keys(state.staged);runNextConfirmed()}
function runNextConfirmed(){if(!state.confirmQueue.length){state.inflightMutation=false;state.activeAction=null;renderConfirmBar();setStatus("Confirmed actions reconciled from canonical board.","ok");refresh(true);return}var key=state.confirmQueue.shift(),a=state.staged[key];if(!a){runNextConfirmed();return}state.inflightMutation=true;state.activeAction=key;renderConfirmBar();setStatus("Confirming "+a.label+" — canonical readback required…","muted");call(a.tool,a.args,"confirm",{actionKey:key,taskId:a.taskId||null})}
function renderTask(t){while(inspector.firstChild)inspector.removeChild(inspector.firstChild);if(!t){inspector.appendChild(node("strong",null,"Inspector"));inspector.appendChild(node("p","muted","Select a card."));state.selectedTask=null;return}state.selectedTask=t;state.selected=t.id||t.task_id||state.selected;inspector.appendChild(node("strong",null,t.title||state.selected));inspector.appendChild(node("div","muted",state.selected+" · "+(t.status||"")+" · "+(t.assignee||"unassigned")));if(t.body)inspector.appendChild(node("p",null,t.body));if(stagedForTask(state.selected)){var p=node("div","banner",stageLabel(stagedForTask(state.selected)));p.appendChild(actionButton("Clear",function(){clearStaged(state.selected)},false));inspector.appendChild(p)}var comment=node("textarea");comment.placeholder="Comment";inspector.appendChild(comment);inspector.appendChild(actionButton("Mark comment",function(){var v=comment.value.trim();if(!v)return;stageAction({taskId:state.selected,label:"Comment",tool:"add_comment",args:{request:{board:selectedBoard(),task_id:state.selected,body:v}}})}));var assignRow=node("div","row"),assignee=node("input","grow");assignee.placeholder="Assignee profile";assignRow.appendChild(assignee);assignRow.appendChild(actionButton("Mark assign",function(){var v=assignee.value.trim();if(!v)return;stageAction({taskId:state.selected,label:"Assign → "+v,tool:"assign_task",args:{request:{board:selectedBoard(),task_id:state.selected,assignee:v}}})}));inspector.appendChild(assignRow);var reason=node("input","grow");reason.placeholder="Reason (optional except changes)";inspector.appendChild(reason);var actions=node("div","row"),st=t.status||"";if(st==="blocked")actions.appendChild(actionButton("Mark unblock",function(){stageAction({taskId:state.selected,label:"Unblock",tool:"unblock_tasks",args:{request:{board:selectedBoard(),task_ids:[state.selected],reason:reason.value||"Unblocked from MCP Apps UI"}}})}));else actions.appendChild(actionButton("Mark block",function(){stageAction({taskId:state.selected,label:"Move to Blocked",targetStatus:"blocked",tool:"block_tasks",args:{request:{board:selectedBoard(),task_ids:[state.selected],kind:"needs_input",reason:reason.value||"Blocked from MCP Apps UI"}}})},st==="done"));actions.appendChild(actionButton("Mark review",function(){stageAction({taskId:state.selected,label:"Move to Review",targetStatus:"review",tool:"request_review",args:{request:{board:selectedBoard(),task_id:state.selected,summary:reason.value||"Requested from MCP Apps UI",reviewer:"reviewer"}}})},st==="done"||st==="review"));actions.appendChild(actionButton("Mark changes",function(){var v=reason.value.trim();if(!v){setStatus("Reason is required for request changes.","error");return}stageAction({taskId:state.selected,label:"Request changes",tool:"request_changes",args:{request:{board:selectedBoard(),task_id:state.selected,reason:v}}})},st!=="review"));actions.appendChild(actionButton("Mark reopen",function(){stageAction({taskId:state.selected,label:"Reopen review",targetStatus:"review",tool:"reopen_review",args:{request:{board:selectedBoard(),task_ids:[state.selected],reason:reason.value||"Reopened from MCP Apps UI"}}})},st!=="todo"));inspector.appendChild(actions)}
function reconcile(taskId){refresh(false);if(taskId){call("get_task",{request:{board:selectedBoard(),task_id:taskId}},"task");delete state.graphs[taskId];ensureGraph(taskId)}setStatus("Tool returned; reconciling canonical state…","muted")}
function stopLive(){if(state.liveTimer){clearInterval(state.liveTimer);state.liveTimer=null}state.liveCycles=0;liveBtn.textContent="Live sync (60s)"}
function liveTick(){if(document.hidden)return;if(Date.now()>state.liveDeadline||state.liveCycles>=MAX_LIVE_CYCLES){stopLive();return}state.liveCycles++;refresh(true)}
function startLive(){if(state.liveTimer){stopLive();return}state.liveCycles=0;state.liveDeadline=Date.now()+LIVE_MAX_MS;liveBtn.textContent="Stop live sync";liveTick();state.liveTimer=setInterval(liveTick,LIVE_INTERVAL_MS)}
picker.addEventListener("change",function(){state.board=selectedBoard();state.selected=null;state.selectedTask=null;state.tasksByStatus={};state.graphs={};refresh(false);renderTask(null)});document.getElementById("refresh").addEventListener("click",function(){refresh(true)});liveBtn.addEventListener("click",startLive);document.addEventListener("visibilitychange",function(){if(document.hidden)stopLive()});window.addEventListener("unload",stopLive);
document.getElementById("create-toggle").addEventListener("click",function(){createPanel.classList.remove("hidden")});document.getElementById("create-cancel").addEventListener("click",function(){createPanel.classList.add("hidden")});document.getElementById("create-submit").addEventListener("click",function(){var title=document.getElementById("create-title").value.trim(),body=document.getElementById("create-body").value;if(!title){setStatus("Title is required.","error");return}stageAction({label:"Create “"+title+"”",tool:"create_task",args:{request:{board:selectedBoard(),title:title,body:body||null,idempotency_key:"ui-"+crypto.randomUUID()}}});createPanel.classList.add("hidden")});document.getElementById("undo-all").addEventListener("click",function(){if(state.inflightMutation)return;state.staged={};renderColumns();renderConfirmBar();if(state.selected)renderTask(state.selectedTask);setStatus("Pending actions cleared.","muted")});document.getElementById("confirm-all").addEventListener("click",confirmStaged);
window.addEventListener("message",function(e){var m=e.data||{};if(m.method==="ui/notifications/tool-result"&&m.params)m=m.params;var p=state.pending[m.id];if(!p)return;delete state.pending[m.id];if(m.error){if(p.kind==="confirm"){state.inflightMutation=false;state.confirmQueue=[];state.activeAction=null;renderConfirmBar()}setStatus((p.name||"Tool")+" failed: "+(m.error.message||"host error"),"error");refresh(true);return}var d=resultOf(m);if(p.kind==="boards")renderBoards(d);else if(p.kind==="board")renderBoard(d);else if(p.kind.indexOf("tasks:")===0){var k=p.kind.slice(6);state.tasksByStatus[k]=(d&&d.items)||[];renderColumns();applyDependencyHighlight(state.hovered||state.selected)}else if(p.kind==="task")renderTask(d);else if(p.kind==="graph"){state.graphs[p.meta.taskId]=graphDependencies(d);applyDependencyHighlight(state.hovered||state.selected)}else if(p.kind==="confirm"){var key=p.meta.actionKey,taskId=p.meta.taskId;delete state.staged[key];state.inflightMutation=false;state.activeAction=null;renderConfirmBar();renderColumns();reconcile(taskId);runNextConfirmed()}});
window.parent.postMessage({jsonrpc:"2.0",id:0,method:"ui/initialize",params:{protocolVersion:"2025-06-18"}},"*");call("list_boards",{},"boards");refresh(false);
}());
</script></body></html>'''


from .interactive_ui import (  # noqa: E402
    KANBAN_UI_HTML_INTERACTIVE_R16,
    build_kanban_ui_interactive_r16_html,
)

# Preserve the existing public symbol while advancing the interactive component.
KANBAN_UI_HTML_INTERACTIVE_R1 = KANBAN_UI_HTML_INTERACTIVE_R16


def build_kanban_ui_interactive_r1_html() -> str:
    """Return the current bounded shared-control MCP App UI."""
    html = build_kanban_ui_interactive_r16_html()
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
