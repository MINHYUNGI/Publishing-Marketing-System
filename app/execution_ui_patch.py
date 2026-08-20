from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UI = ROOT / "ui" / "index.html"
MARKER = "v294-marketing-execution-editor"


def apply_patch() -> None:
    text = UI.read_text(encoding="utf-8")
    if MARKER in text:
        return

    css = r'''
<style>
/* v294-marketing-execution-editor */
.exec-groups{padding:12px 18px 18px;display:flex;flex-direction:column;gap:10px}
.exec-group{border:1px solid #dfe5ec;border-radius:10px;overflow:hidden;background:#fff}
.exec-group-head{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:11px 13px}
.exec-group-head.store{background:#eaf3fa}.exec-group-head.sns{background:#eaf5f0}.exec-group-head.extra{background:#f8f0df}
.exec-group-title{display:flex;align-items:center;gap:8px;min-width:0}.exec-group-title b{font-size:13px}.exec-group-title span{font-size:10px;color:#6c7887}
.exec-edit-btn{height:29px;padding:0 10px;border:1px solid #b9c7d6;border-radius:6px;background:#fff;color:#425466;font-weight:800;cursor:pointer}
.exec-table{width:100%;border-collapse:collapse;table-layout:auto;min-width:760px}.exec-table th{position:static;background:#fafbfc;font-size:10px;color:#667485;padding:8px 9px}.exec-table td{font-size:11px;padding:9px;border-top:1px solid #edf0f3;color:#405064}.exec-table .money{text-align:right;white-space:nowrap}
.exec-badge{display:inline-flex;margin-left:6px;padding:2px 6px;border-radius:999px;font-size:9px;font-weight:900;vertical-align:middle}.exec-badge.add{background:#e8f5ee;color:#2f7458}.exec-badge.cancel{background:#fbecec;color:#a74747}.exec-badge.pending{background:#f1f3f5;color:#7a8490}
.exec-cancel-row{opacity:.55;text-decoration:line-through}.exec-summary-muted{color:#8a95a3}
.exec-modal-backdrop{display:none;position:fixed;inset:0;background:rgba(18,28,40,.48);z-index:10000;align-items:center;justify-content:center;padding:24px}.exec-modal-backdrop.show{display:flex}
.exec-modal{width:min(1180px,96vw);max-height:88vh;background:#fff;border-radius:14px;box-shadow:0 24px 70px rgba(0,0,0,.28);display:flex;flex-direction:column;overflow:hidden}
.exec-modal-head{display:flex;justify-content:space-between;align-items:center;padding:15px 18px;border-bottom:1px solid #dfe5ec}.exec-modal-head h3{margin:0;font-size:17px}.exec-modal-close{border:0;background:transparent;font-size:24px;cursor:pointer;color:#697586}
.exec-modal-body{padding:14px 18px;overflow:auto}.exec-edit-table{width:100%;border-collapse:collapse;min-width:980px}.exec-edit-table th{position:sticky;top:0;background:#f7f9fc;z-index:2;font-size:10px;padding:8px}.exec-edit-table td{padding:7px;border-bottom:1px solid #edf0f3;vertical-align:middle}.exec-edit-table input{width:100%;height:34px;border:1px solid #cbd4df;border-radius:6px;padding:0 7px;font-size:11px}.exec-edit-table input[type=number]{text-align:right}.exec-row-cancelled{opacity:.5;background:#fafafa}.exec-row-added{background:#f7fbf9}
.exec-minus{width:32px;height:32px;border:1px solid #d7a7a7;border-radius:6px;background:#fff;color:#a74747;font-size:17px;font-weight:900;cursor:pointer}.exec-restore{width:auto;padding:0 8px;color:#556576;border-color:#c7d0da;font-size:10px}
.exec-modal-foot{display:flex;justify-content:space-between;align-items:center;gap:10px;padding:12px 18px;border-top:1px solid #dfe5ec;background:#fbfcfd}.exec-plus{height:34px;border:1px solid #8eb7a4;border-radius:7px;background:#f3faf6;color:#36705a;padding:0 12px;font-weight:900;cursor:pointer}.exec-save{height:36px;border:0;border-radius:7px;background:#316fc8;color:#fff;padding:0 16px;font-weight:900;cursor:pointer}
.p271-activity-label .exec-badge,.p271-actbar .exec-badge{font-size:8px;margin-left:5px;padding:1px 5px;flex:0 0 auto}.p271-activity-label.exec-cancelled,.p271-actbar.exec-cancelled{opacity:.42}.p271-actbar.exec-cancelled{border-style:dashed!important;text-decoration:line-through}
</style>
'''

    script = r'''
<script>
// v294-marketing-execution-editor
(function(){
 let execEditCategory="";
 let execEditItems=[];
 const groupDefs=[
  {key:"store",label:"서점 마케팅",match:a=>String(a.활동분류||"").includes("서점")},
  {key:"sns",label:"SNS·바이럴 마케팅",match:a=>String(a.활동분류||"").includes("SNS")||String(a.활동분류||"").includes("바이럴")},
  {key:"extra",label:"추가 마케팅",match:a=>!(String(a.활동분류||"").includes("서점")||String(a.활동분류||"").includes("SNS")||String(a.활동분류||"").includes("바이럴"))}
 ];
 function money(v){const n=Number(v||0);return n?n.toLocaleString("ko-KR")+"원":"—"}
 function execBadge(a){
   if(a.실행구분==="활동추가")return '<span class="exec-badge add">활동추가</span>';
   if(a.실행구분==="활동취소")return '<span class="exec-badge cancel">활동취소</span>';
   if(!a.실행확인여부)return '<span class="exec-badge pending">미확인</span>';
   return "";
 }
 function groupOf(a){return groupDefs.find(g=>g.match(a))||groupDefs[2]}
 function activitiesForGroup(g){return (currentPerformanceData?.마케팅활동||[]).filter(g.match)}
 function actualRate(a){const p=Number(a.계획비용??a.비용??0),x=Number(a.실제비용??0);return p?`${(x/p*100).toFixed(1)}%`:"—"}
 function confirmedCost(items){return items.filter(a=>a.실행확인여부&&a.실행구분!=="활동취소").reduce((s,a)=>s+Number(a.실제비용||0),0)}

 function renderExecutionPanel(){
   const panel=[...document.querySelectorAll("#performanceContent .p271-panel")].find(p=>p.querySelector("h3")?.textContent.trim().startsWith("3."));
   if(!panel)return;
   const acts=currentPerformanceData?.마케팅활동||[];
   const groups=groupDefs.map(g=>({...g,items:activitiesForGroup(g)})).filter(g=>g.items.length);
   panel.innerHTML=`<div class="p271-panel-head"><div><h3>3. 계획 대비 실제 실행</h3><p>기획값을 기본값으로 보여주며, 수정·추가·취소한 내용은 실제 실행 데이터에만 저장합니다.</p></div><span class="p271-panel-tag">PLAN → EXECUTION</span></div>
   <div class="exec-groups">${groups.map(g=>{
      const planBudget=g.items.filter(a=>a.실행구분!=="활동추가").reduce((s,a)=>s+Number(a.계획비용??a.비용??0),0);
      const actual=confirmedCost(g.items),rate=planBudget?actual/planBudget*100:0;
      return `<div class="exec-group"><div class="exec-group-head ${g.key}"><div class="exec-group-title"><b>${g.label}</b><span>${g.items.length}건 · 계획 예산 ${money(planBudget)} · 예산 집행률 ${actual?rate.toFixed(1)+"%":"0.0%"}</span></div><button class="exec-edit-btn" onclick="openExecutionEditor('${g.key}')">수정</button></div>
      <div style="overflow:auto"><table class="exec-table"><thead><tr><th>마케팅 활동</th><th>실제 시작일</th><th>실제 종료일</th><th class="money">집행 비용</th><th class="money">계획 당시 예산</th><th>예산 집행률</th></tr></thead><tbody>${g.items.map(a=>`<tr class="${a.실행구분==='활동취소'?'exec-cancel-row':''}"><td><strong>${esc(a.활동명||"활동")}</strong>${execBadge(a)}<br><span class="p271-placeholder">${esc(a.채널또는매체||"")}</span></td><td>${esc(a.실제시작일||a.계획시작일||a.시작일||"—")}</td><td>${esc(a.실제종료일||a.계획종료일||a.종료일||"—")}</td><td class="money">${money(a.실제비용)}</td><td class="money">${a.실행구분==='활동추가'?"—":money(a.계획비용??a.비용)}</td><td>${a.실행구분==='활동취소'?"—":actualRate(a)}</td></tr>`).join("")}</tbody></table></div></div>`;
   }).join("")||'<div class="perf-empty">등록된 마케팅 활동이 없습니다.</div>'}</div>`;
   if(window.applyGlobalFontScale) setTimeout(()=>window.applyGlobalFontScale(),0);
 }

 function ensureExecModal(){
   if(document.getElementById("execModalBackdrop"))return;
   const wrap=document.createElement("div");wrap.id="execModalBackdrop";wrap.className="exec-modal-backdrop";
   wrap.innerHTML=`<div class="exec-modal"><div class="exec-modal-head"><h3 id="execModalTitle">실제 실행 수정</h3><button class="exec-modal-close" onclick="closeExecutionEditor()">×</button></div><div class="exec-modal-body"><div id="execModalTable"></div></div><div class="exec-modal-foot"><button class="exec-plus" onclick="addExecutionActivity()">+ 활동 추가</button><div><button class="exec-edit-btn" onclick="closeExecutionEditor()">취소</button> <button class="exec-save" onclick="saveExecutionEditor()">저장</button></div></div></div>`;
   document.body.appendChild(wrap);
 }
 function editItemFromActivity(a){
   return {execution_activity_id:a.실행활동ID||null,original_activity_id:a.활동ID||null,channel_or_media:a.채널또는매체||"",activity_name:a.활동명||"",actual_start_date:a.실제시작일||a.계획시작일||a.시작일||"",actual_end_date:a.실제종료일||a.계획종료일||a.종료일||"",actual_cost:Number(a.실제비용??a.계획비용??a.비용??0),execution_note:a.실행내용||"",execution_type:a.실행구분==="활동취소"?"활동취소":(a.실행구분==="활동추가"?"활동추가":"실행확인"),is_new:false};
 }
 window.openExecutionEditor=function(key){
   ensureExecModal();const g=groupDefs.find(x=>x.key===key);if(!g)return;
   execEditCategory=g.label;execEditItems=activitiesForGroup(g).map(editItemFromActivity);
   document.getElementById("execModalTitle").textContent=`${g.label} · 실제 실행 수정`;
   document.getElementById("execModalBackdrop").classList.add("show");renderExecModalTable();
 };
 window.closeExecutionEditor=function(){document.getElementById("execModalBackdrop")?.classList.remove("show")};
 function pullExecInputs(){
   document.querySelectorAll("#execModalTable tr[data-i]").forEach(tr=>{const i=Number(tr.dataset.i),o=execEditItems[i];if(!o||o.delete_added)return;const q=n=>tr.querySelector(`[data-f='${n}']`)?.value??"";o.channel_or_media=q("channel");o.activity_name=q("name");o.actual_start_date=q("start");o.actual_end_date=q("end");o.actual_cost=Number(q("cost")||0);o.execution_note=q("note");});
 }
 function renderExecModalTable(){
   const box=document.getElementById("execModalTable");if(!box)return;
   box.innerHTML=`<table class="exec-edit-table"><thead><tr><th>채널/매체</th><th style="min-width:220px">활동명</th><th>실제 시작일</th><th>실제 종료일</th><th>집행비용</th><th style="min-width:180px">실행 내용/비고</th><th></th></tr></thead><tbody>${execEditItems.map((o,i)=>{if(o.delete_added)return"";const cancel=o.execution_type==="활동취소",added=o.execution_type==="활동추가";return `<tr data-i="${i}" class="${cancel?'exec-row-cancelled':added?'exec-row-added':''}"><td><input data-f="channel" value="${esc(o.channel_or_media)}" ${cancel?'disabled':''}></td><td><input data-f="name" value="${esc(o.activity_name)}" ${cancel?'disabled':''}>${added?'<span class="exec-badge add">활동추가</span>':cancel?'<span class="exec-badge cancel">활동취소</span>':''}</td><td><input data-f="start" type="date" value="${esc(o.actual_start_date)}" ${cancel?'disabled':''}></td><td><input data-f="end" type="date" value="${esc(o.actual_end_date)}" ${cancel?'disabled':''}></td><td><input data-f="cost" type="number" min="0" step="1000" value="${Number(o.actual_cost||0)}" ${cancel?'disabled':''}></td><td><input data-f="note" value="${esc(o.execution_note)}" ${cancel?'disabled':''}></td><td><button class="exec-minus ${cancel?'exec-restore':''}" onclick="toggleExecutionActivity(${i})">${cancel?'복원':'−'}</button></td></tr>`}).join("")}</tbody></table>`;
 }
 window.addExecutionActivity=function(){pullExecInputs();execEditItems.push({execution_activity_id:null,original_activity_id:null,channel_or_media:"",activity_name:"",actual_start_date:"",actual_end_date:"",actual_cost:0,execution_note:"",execution_type:"활동추가",is_new:true});renderExecModalTable()};
 window.toggleExecutionActivity=function(i){pullExecInputs();const o=execEditItems[i];if(!o)return;if(o.execution_type==="활동추가"){if(o.execution_activity_id)o.delete_added=true;else execEditItems.splice(i,1);}else{o.execution_type=o.execution_type==="활동취소"?"실행확인":"활동취소";}renderExecModalTable()};
 window.saveExecutionEditor=async function(){
   pullExecInputs();
   for(const o of execEditItems){if(!o.delete_added&&!String(o.activity_name||"").trim()){toast("활동명을 입력해 주세요.");return;}}
   try{
     const registrarId=document.getElementById("registrar")?.value||null;
     const r=await pywebview.api.save_marketing_execution_group(currentPerformanceCode,execEditCategory,execEditItems,registrarId);
     if(!r.ok){toast(r.message||"저장 실패");return;}
     closeExecutionEditor();toast(`실제 실행 ${r.saved||0}건을 저장했습니다.`);await loadPerformanceDetail(currentPerformanceCode);
   }catch(e){toast("실제 실행 저장 실패: "+e)}
 };

 function enhanceExecutionTimeline(){
   const acts=currentPerformanceData?.마케팅활동||[];
   const byName=new Map();acts.forEach(a=>{if(a.활동명)byName.set(String(a.활동명),a)});
   document.querySelectorAll("#p271SalesGrid .p271-activity-label b,#p271SalesGrid .p271-actbar").forEach(el=>{
     const raw=[...el.childNodes].filter(n=>n.nodeType===3).map(n=>n.textContent).join("").trim()||el.textContent.trim();
     const a=byName.get(raw);if(!a)return;
     if(a.실행구분==="활동추가"&&!el.querySelector(".exec-badge"))el.insertAdjacentHTML("beforeend",'<span class="exec-badge add">활동추가</span>');
     if(a.실행구분==="활동취소"){el.classList.add("exec-cancelled");if(!el.querySelector(".exec-badge"))el.insertAdjacentHTML("beforeend",'<span class="exec-badge cancel">활동취소</span>');}
   });
 }

 const oldRender=window.renderPerformancePage;
 if(typeof oldRender==="function")window.renderPerformancePage=function(r){oldRender(r);setTimeout(()=>{renderExecutionPanel();enhanceExecutionTimeline()},0)};
 const oldGrid=window.renderP271SalesGrid;
 if(typeof oldGrid==="function")window.renderP271SalesGrid=function(){oldGrid();setTimeout(enhanceExecutionTimeline,0)};
 window.renderExecutionPanel=renderExecutionPanel;
})();
</script>
'''

    if "</head>" not in text or "</body>" not in text:
        raise RuntimeError("HTML 기준점을 찾지 못했습니다.")
    text = text.replace("</head>", css + "\n</head>", 1)
    text = text.replace("</body>", script + "\n</body>", 1)
    UI.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    apply_patch()
