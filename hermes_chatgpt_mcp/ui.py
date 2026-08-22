from __future__ import annotations

KANBAN_UI_RESOURCE_URI = "ui://hermes/kanban/v1"
KANBAN_UI_MIME_TYPE = "text/html;profile=mcp-app"
KANBAN_UI_MAX_BYTES = 262_144

KANBAN_UI_HTML_V1 = r'''<!DOCTYPE html>
<html lang="en" data-ui-version="v1">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
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
