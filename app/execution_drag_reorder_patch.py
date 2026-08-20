from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UI = ROOT / "ui" / "index.html"
MARKER = "v302-execution-drag-reorder"


def apply_patch() -> None:
    text = UI.read_text(encoding="utf-8")
    if MARKER in text:
        return

    css = r'''
<style>
/* v302-execution-drag-reorder */
.exec-order-wrap{display:none!important}
.exec-drag-cell{width:42px;text-align:center;padding-left:4px!important;padding-right:4px!important}
.exec-drag-handle{display:inline-flex;align-items:center;justify-content:center;width:28px;height:30px;border-radius:6px;color:#75869a;font-size:16px!important;line-height:1!important;cursor:grab;user-select:none}
.exec-drag-handle:hover{background:#eef3f8;color:#425466}
.exec-drag-handle:active{cursor:grabbing;background:#e4ebf3}
.exec-edit-table tr.exec-dragging{opacity:.42;background:#edf4fb!important}
.exec-edit-table tr.exec-drag-over{box-shadow:inset 0 2px 0 #4f86c6}
</style>
'''
    if "</head>" not in text:
        raise RuntimeError("HTML head 종료 태그를 찾지 못했습니다.")
    text = text.replace("</head>", css + "\n</head>", 1)

    old = '<th style="min-width:180px">실행 내용/비고</th><th style="width:72px">순서</th><th></th></tr>'
    new = '<th style="width:42px"></th><th>채널/매체</th><th style="min-width:220px">활동명</th><th>실제 시작일</th><th>실제 종료일</th><th>집행비용</th><th style="min-width:180px">실행 내용/비고</th><th></th></tr>'
    # execution_reorder_ui_patch가 이미 첫 6개 헤더를 포함한 문자열에 위 old를 붙이는 구조라 전체 헤더를 교체합니다.
    full_old = '<th>채널/매체</th><th style="min-width:220px">활동명</th><th>실제 시작일</th><th>실제 종료일</th><th>집행비용</th><th style="min-width:180px">실행 내용/비고</th><th style="width:72px">순서</th><th></th></tr>'
    if full_old not in text:
        raise RuntimeError("실행 편집 표 순서 헤더 기준점을 찾지 못했습니다.")
    text = text.replace(full_old, new, 1)

    old_row = '<tr data-i="${i}" class="${cancel?\'exec-row-cancelled\':added?\'exec-row-added\':\'\'}"><td><input data-f="channel" value="${esc(o.channel_or_media)}" ${cancel?\'disabled\':\'\'}></td>'
    new_row = '<tr data-i="${i}" class="${cancel?\'exec-row-cancelled\':added?\'exec-row-added\':\'\'}" ondragover="executionDragOver(event,${i})" ondragleave="executionDragLeave(event)" ondrop="executionDrop(event,${i})"><td class="exec-drag-cell"><span class="exec-drag-handle" draggable="true" ondragstart="executionDragStart(event,${i})" ondragend="executionDragEnd(event)" title="드래그해서 순서 변경">⋮⋮</span></td><td><input data-f="channel" value="${esc(o.channel_or_media)}" ${cancel?\'disabled\':\'\'}></td>'
    if old_row not in text:
        raise RuntimeError("실행 편집 표 행 시작 기준점을 찾지 못했습니다.")
    text = text.replace(old_row, new_row, 1)

    old_order = '<td><div class="exec-order-wrap"><button class="exec-order-btn" onclick="moveExecutionActivity(${i},-1)" ${i===0?\'disabled\':\'\'}>▲</button><button class="exec-order-btn" onclick="moveExecutionActivity(${i},1)" ${i===execEditItems.length-1?\'disabled\':\'\'}>▼</button></div></td><td><button class="exec-minus ${cancel?\'exec-restore\':\'\'}" onclick="toggleExecutionActivity(${i})">${cancel?\'복원\':\'−\'}</button></td>'
    new_order = '<td><button class="exec-minus ${cancel?\'exec-restore\':\'\'}" onclick="toggleExecutionActivity(${i})">${cancel?\'복원\':\'−\'}</button></td>'
    if old_order not in text:
        raise RuntimeError("기존 위아래 순서 버튼 기준점을 찾지 못했습니다.")
    text = text.replace(old_order, new_order, 1)

    anchor = 'window.moveExecutionActivity=function(i,delta){'
    if anchor not in text:
        raise RuntimeError("기존 순서 이동 함수 기준점을 찾지 못했습니다.")

    insert = r'''let execDragIndex=null;
 window.executionDragStart=function(ev,i){
   pullExecInputs();
   execDragIndex=i;
   try{ev.dataTransfer.effectAllowed="move";ev.dataTransfer.setData("text/plain",String(i));}catch(e){}
   ev.target.closest("tr")?.classList.add("exec-dragging");
 };
 window.executionDragOver=function(ev,i){
   if(execDragIndex===null)return;
   ev.preventDefault();
   try{ev.dataTransfer.dropEffect="move";}catch(e){}
   document.querySelectorAll("#execModalTable tr.exec-drag-over").forEach(r=>r.classList.remove("exec-drag-over"));
   ev.currentTarget?.classList.add("exec-drag-over");
 };
 window.executionDragLeave=function(ev){
   ev.currentTarget?.classList.remove("exec-drag-over");
 };
 window.executionDrop=function(ev,targetIndex){
   ev.preventDefault();
   const from=execDragIndex;
   if(from===null||from<0||from>=execEditItems.length)return;
   const row=ev.currentTarget;
   const rect=row.getBoundingClientRect();
   const after=ev.clientY>rect.top+rect.height/2;
   const item=execEditItems.splice(from,1)[0];
   let insertAt=targetIndex;
   if(from<targetIndex)insertAt-=1;
   if(after)insertAt+=1;
   insertAt=Math.max(0,Math.min(execEditItems.length,insertAt));
   execEditItems.splice(insertAt,0,item);
   execEditItems.forEach((o,idx)=>o.sort_order=(idx+1)*10);
   execDragIndex=null;
   renderExecModalTable();
 };
 window.executionDragEnd=function(){
   execDragIndex=null;
   document.querySelectorAll("#execModalTable tr.exec-dragging,#execModalTable tr.exec-drag-over").forEach(r=>r.classList.remove("exec-dragging","exec-drag-over"));
 };
 '''
    text = text.replace(anchor, insert + anchor, 1)

    if "</body>" not in text:
        raise RuntimeError("HTML body 종료 태그를 찾지 못했습니다.")
    text = text.replace("</body>", f'<script>/* {MARKER} */</script>\n</body>', 1)
    UI.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    apply_patch()
