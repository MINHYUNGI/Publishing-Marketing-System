from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UI = ROOT / "ui" / "index.html"
MARKER = "v301-execution-reorder-and-button-lock"


def apply_patch() -> None:
    text = UI.read_text(encoding="utf-8")
    if MARKER in text:
        return

    css = r'''
<style>
/* v301-execution-reorder-and-button-lock */
.exec-plus{font-size:11px!important;line-height:1!important}
.exec-save{font-size:11px!important;line-height:1!important}
.exec-edit-btn{font-size:11px!important;line-height:1!important}
.exec-minus{font-size:15px!important;line-height:1!important}
.exec-restore{font-size:10px!important}
.exec-modal-close{font-size:24px!important;line-height:1!important}
.exec-order-wrap{display:flex;align-items:center;justify-content:center;gap:3px;white-space:nowrap}
.exec-order-btn{width:27px;height:27px;padding:0;border:1px solid #c9d3df;border-radius:6px;background:#fff;color:#536579;font-size:12px!important;line-height:1!important;font-weight:900;cursor:pointer}
.exec-order-btn:hover{background:#f2f6fa}
.exec-order-btn:disabled{opacity:.28;cursor:default}
</style>
'''
    text = text.replace("</head>", css + "\n</head>", 1)

    old = 'function activitiesForGroup(g){return (currentPerformanceData?.마케팅활동||[]).filter(g.match)}'
    new = '''function activitiesForGroup(g){return (currentPerformanceData?.마케팅활동||[]).filter(g.match).sort((a,b)=>{\n   const ao=Number(a.실행정렬순서??a.정렬순서??999999),bo=Number(b.실행정렬순서??b.정렬순서??999999);\n   return ao-bo;\n })}'''
    if old not in text:
        raise RuntimeError("활동 그룹 함수 기준점을 찾지 못했습니다.")
    text = text.replace(old, new, 1)

    old = 'return {execution_activity_id:a.실행활동ID||null,original_activity_id:a.활동ID||null,channel_or_media:a.채널또는매체||"",activity_name:a.활동명||"",actual_start_date:a.실제시작일||a.계획시작일||a.시작일||"",actual_end_date:a.실제종료일||a.계획종료일||a.종료일||"",actual_cost:Number(a.실제비용??a.계획비용??a.비용??0),execution_note:a.실행내용||"",execution_type:a.실행구분==="활동취소"?"활동취소":(a.실행구분==="활동추가"?"활동추가":"실행확인"),is_new:false};'
    new = 'return {execution_activity_id:a.실행활동ID||null,original_activity_id:a.활동ID||null,channel_or_media:a.채널또는매체||"",activity_name:a.활동명||"",actual_start_date:a.실제시작일||a.계획시작일||a.시작일||"",actual_end_date:a.실제종료일||a.계획종료일||a.종료일||"",actual_cost:Number(a.실제비용??a.계획비용??a.비용??0),execution_note:a.실행내용||"",execution_type:a.실행구분==="활동취소"?"활동취소":(a.실행구분==="활동추가"?"활동추가":"실행확인"),sort_order:Number(a.실행정렬순서??a.정렬순서??999999),is_new:false};'
    if old not in text:
        raise RuntimeError("실행 편집 항목 기준점을 찾지 못했습니다.")
    text = text.replace(old, new, 1)

    old = '<th style="min-width:180px">실행 내용/비고</th><th></th></tr>'
    new = '<th style="min-width:180px">실행 내용/비고</th><th style="width:72px">순서</th><th></th></tr>'
    if old not in text:
        raise RuntimeError("실행 편집 표 헤더 기준점을 찾지 못했습니다.")
    text = text.replace(old, new, 1)

    old = '<td><input data-f="note" value="${esc(o.execution_note)}" ${cancel?\'disabled\':\'\'}></td><td><button class="exec-minus ${cancel?\'exec-restore\':\'\'}" onclick="toggleExecutionActivity(${i})">${cancel?\'복원\':\'−\'}</button></td>'
    new = '<td><input data-f="note" value="${esc(o.execution_note)}" ${cancel?\'disabled\':\'\'}></td><td><div class="exec-order-wrap"><button class="exec-order-btn" onclick="moveExecutionActivity(${i},-1)" ${i===0?\'disabled\':\'\'}>▲</button><button class="exec-order-btn" onclick="moveExecutionActivity(${i},1)" ${i===execEditItems.length-1?\'disabled\':\'\'}>▼</button></div></td><td><button class="exec-minus ${cancel?\'exec-restore\':\'\'}" onclick="toggleExecutionActivity(${i})">${cancel?\'복원\':\'−\'}</button></td>'
    if old not in text:
        raise RuntimeError("실행 편집 표 행 기준점을 찾지 못했습니다.")
    text = text.replace(old, new, 1)

    anchor = 'window.addExecutionActivity=function(){pullExecInputs();execEditItems.push('
    insert = '''window.moveExecutionActivity=function(i,delta){\n   pullExecInputs();\n   const j=i+delta;if(j<0||j>=execEditItems.length)return;\n   const tmp=execEditItems[i];execEditItems[i]=execEditItems[j];execEditItems[j]=tmp;\n   execEditItems.forEach((o,idx)=>o.sort_order=(idx+1)*10);\n   renderExecModalTable();\n };\n '''
    if anchor not in text:
        raise RuntimeError("활동 추가 함수 기준점을 찾지 못했습니다.")
    text = text.replace(anchor, insert + anchor, 1)

    old = 'execEditItems.push({execution_activity_id:null,original_activity_id:null,channel_or_media:"",activity_name:"",actual_start_date:"",actual_end_date:"",actual_cost:0,execution_note:"",execution_type:"활동추가",is_new:true});'
    new = 'execEditItems.push({execution_activity_id:null,original_activity_id:null,channel_or_media:"",activity_name:"",actual_start_date:"",actual_end_date:"",actual_cost:0,execution_note:"",execution_type:"활동추가",sort_order:(execEditItems.length+1)*10,is_new:true});'
    if old not in text:
        raise RuntimeError("신규 실행활동 기준점을 찾지 못했습니다.")
    text = text.replace(old, new, 1)

    old = 'pullExecInputs();\n   for(const o of execEditItems){if(!o.delete_added&&!String(o.activity_name||"").trim()){toast("활동명을 입력해 주세요.");return;}}'
    new = 'pullExecInputs();\n   execEditItems.forEach((o,idx)=>o.sort_order=(idx+1)*10);\n   for(const o of execEditItems){if(!o.delete_added&&!String(o.activity_name||"").trim()){toast("활동명을 입력해 주세요.");return;}}'
    if old not in text:
        raise RuntimeError("실행 저장 함수 기준점을 찾지 못했습니다.")
    text = text.replace(old, new, 1)

    text = text.replace("</body>", f'<script>/* {MARKER} */</script>\n</body>', 1)
    UI.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    apply_patch()
