from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UI = ROOT / "ui" / "index.html"
MARKER = "p282-execution-budget-ratio"


def apply_patch() -> None:
    text = UI.read_text(encoding="utf-8")
    if MARKER in text:
        return

    helper_anchor = ' const buyerHtml=buyer&&buyer.구매자반응ID?`'
    helper = r''' const executionGroupDefs=[
  {key:"서점 마케팅",tone:"store",match:a=>(a.활동분류||"").includes("서점")},
  {key:"SNS 바이럴 마케팅",tone:"sns",match:a=>(a.활동분류||"").includes("SNS")},
  {key:"추가 마케팅",tone:"extra",match:a=>!(a.활동분류||"").includes("서점")&&!(a.활동분류||"").includes("SNS")}
 ];
 const executionGroups=executionGroupDefs.map(g=>({name:g.key,tone:g.tone,items:acts.filter(g.match)})).filter(g=>g.items.length);
 const executionTableHtml=executionGroups.length?executionGroups.map(g=>{
   const groupBudget=g.items.reduce((s,a)=>s+perfNum(a.비용),0);
   const groupActual=g.items.reduce((s,a)=>s+perfNum(a.실제비용),0);
   const groupRate=groupBudget>0?(groupActual/groupBudget*100):null;
   return `<div class="p281-exec-group p282-${g.tone}">
    <div class="p281-exec-group-head"><strong>${esc(g.name)}</strong><span>${g.items.length}건 · 계획 예산 ${detailMoney(groupBudget)}${groupRate!==null?` · 집행률 ${groupRate.toFixed(1)}%`:""}</span></div>
    <div class="p271-table-wrap p281-exec-wrap"><table class="p271-table p281-exec-table p282-exec-table">
     <thead><tr><th>채널 / 매체</th><th>활동 내용</th><th>실제 시작일</th><th>실제 종료일</th><th class="p271-money">집행 비용</th><th class="p271-money">계획 당시 예산</th><th class="p271-money">집행률</th></tr></thead>
     <tbody>${g.items.map(a=>{const planned=perfNum(a.비용),actual=perfNum(a.실제비용),rate=planned>0?(actual/planned*100):null;return `<tr>
      <td>${esc(a.채널또는매체||"—")}</td>
      <td><strong>${esc(a.활동명||"활동")}</strong>${a.비고?`<small>${esc(a.비고)}</small>`:""}</td>
      <td>${esc(a.실제시작일||"—")}</td>
      <td>${esc(a.실제종료일||a.실제시작일||"—")}</td>
      <td class="p271-money">${a.실제비용!=null?detailMoney(a.실제비용):"—"}</td>
      <td class="p271-money">${detailMoney(a.비용)}</td>
      <td class="p271-money p282-rate">${rate!==null?rate.toFixed(1)+"%":"—"}</td>
     </tr>`}).join("")}</tbody>
    </table></div>
   </div>`;
 }).join(""):`<div class="perf-empty">등록된 마케팅 활동이 없습니다.</div>`;
'''

    if helper_anchor not in text:
        raise RuntimeError("성과 화면 기준점을 찾지 못했습니다.")
    text = text.replace(helper_anchor, helper + "\n" + helper_anchor, 1)

    old = r'''<div class="p271-two-col">
  <section class="p271-panel"><div class="p271-panel-head"><div><h3>3. 계획 대비 실제 실행</h3><p>출간 전에 등록한 일정과 실제 진행일을 비교합니다.</p></div><span class="p271-panel-tag">PLAN → EXECUTION</span></div>
   <div class="p271-table-wrap"><table class="p271-table"><thead><tr><th>마케팅 활동</th><th>계획 일정</th><th>실제 일정</th><th>계획비</th><th>실제비</th><th>상태</th></tr></thead><tbody>
   ${acts.map(a=>{const st=perfActivityStatus(a);return `<tr><td><strong>${esc(a.활동명||"활동")}</strong><br><span class="p271-placeholder">${esc(a.채널또는매체||detailGroupName(a.활동분류||""))}</span></td><td>${esc(a.시작일||"미정")}${a.종료일&&a.종료일!==a.시작일?`~${esc(a.종료일)}`:""}</td><td>${esc(a.실제시작일||"—")}${a.실제종료일&&a.실제종료일!==a.실제시작일?`~${esc(a.실제종료일)}`:""}</td><td>${detailMoney(a.비용)}</td><td>${a.실제비용!=null?detailMoney(a.실제비용):"—"}</td><td><span class="p271-status ${perfStatusClass(st)}">${esc(st)}</span></td></tr>`}).join("")||'<tr><td colspan="6">등록된 활동이 없습니다.</td></tr>'}
   </tbody></table></div>
  </section>
  <section class="p271-panel"><div class="p271-panel-head"><div><h3>4. 예산 집행 현황</h3><p>계획비와 실제비용을 활동별로 합산합니다.</p></div><span class="p271-panel-tag">Supabase</span></div>
   <div class="p271-budget"><div><span>계획 예산</span><strong>${perfMoneyWon(budget)}</strong></div><div><span>실제 집행</span><strong class="good">${actualBudget?perfMoneyWon(actualBudget):"—"}</strong></div><div><span>집행률</span><strong>${actualBudget&&budget?execRate.toFixed(1)+"%":"—"}</strong></div><div><span>잔여</span><strong>${actualBudget&&budget?perfMoneyWon(Math.max(0,budget-actualBudget)):"—"}</strong></div></div>
  </section>
 </div>'''

    new = r'''<section class="p271-panel p281-execution-panel"><div class="p271-panel-head"><div><h3>3. 계획 대비 실제 실행</h3><p>실제 실행 일정과 집행 비용을 계획 당시 예산과 비교합니다.</p></div><span class="p271-panel-tag">PLAN → EXECUTION</span></div>
  <div class="p281-exec-body">${executionTableHtml}</div>
 </section>

 <section class="p271-panel"><div class="p271-panel-head"><div><h3>4. 예산 집행 현황</h3><p>계획비와 실제비용을 활동별로 합산합니다.</p></div><span class="p271-panel-tag">Supabase</span></div>
  <div class="p271-budget"><div><span>계획 예산</span><strong>${perfMoneyWon(budget)}</strong></div><div><span>실제 집행</span><strong class="good">${actualBudget?perfMoneyWon(actualBudget):"—"}</strong></div><div><span>집행률</span><strong>${actualBudget&&budget?execRate.toFixed(1)+"%":"—"}</strong></div><div><span>잔여</span><strong>${actualBudget&&budget?perfMoneyWon(Math.max(0,budget-actualBudget)):"—"}</strong></div></div>
 </section>'''

    if old not in text:
        raise RuntimeError("성과 화면 계획 대비 실행 원본 구간을 찾지 못했습니다.")
    text = text.replace(old, new, 1)

    css = r'''
/* v2.8.2 계획 대비 실제 실행 - 기획 상세 컬러/집행률 */
.p281-execution-panel{overflow:hidden}
.p281-exec-body{padding:14px 12px 16px;background:#f8fafc}
.p281-exec-group{border:1px solid #c9d9e8;border-radius:10px;overflow:hidden;background:#fff;margin-bottom:12px}
.p281-exec-group:last-child{margin-bottom:0}
.p281-exec-group-head{display:flex;align-items:center;justify-content:space-between;gap:14px;padding:12px 14px;border-bottom:1px solid}
.p281-exec-group-head strong{font-size:16px;font-weight:900}
.p281-exec-group-head span{font-size:13px;font-weight:800;white-space:nowrap}
.p282-store{border-color:#bfd5e8}.p282-store .p281-exec-group-head{background:#eaf3fa;border-color:#d5e4ef}.p282-store .p281-exec-group-head strong,.p282-store .p281-exec-group-head span{color:#174d78}
.p282-sns{border-color:#bfded4}.p282-sns .p281-exec-group-head{background:#edf7f3;border-color:#d7eae3}.p282-sns .p281-exec-group-head strong,.p282-sns .p281-exec-group-head span{color:#176b55}
.p282-extra{border-color:#ead4ad}.p282-extra .p281-exec-group-head{background:#fbf4e7;border-color:#efe1c7}.p282-extra .p281-exec-group-head strong,.p282-extra .p281-exec-group-head span{color:#8a5a10}
.p281-exec-wrap{max-height:none;overflow-x:auto}
.p281-exec-table{min-width:1120px;table-layout:fixed}
.p281-exec-table th{position:static;background:#f6f8fb;color:#344054;font-size:13px;padding:11px 10px}
.p281-exec-table td{font-size:14px;padding:12px 10px;vertical-align:middle;color:#26384a}
.p282-exec-table th:nth-child(1){width:15%}.p282-exec-table th:nth-child(2){width:31%}
.p282-exec-table th:nth-child(3),.p282-exec-table th:nth-child(4){width:11%}
.p282-exec-table th:nth-child(5),.p282-exec-table th:nth-child(6){width:12%}.p282-exec-table th:nth-child(7){width:8%}
.p281-exec-table td:nth-child(2) strong{display:block;font-size:14px;color:#23364b}
.p281-exec-table td:nth-child(2) small{display:block;margin-top:4px;font-size:12px;line-height:1.45;color:#6b7a8c}
.p282-exec-table td:nth-child(n+3){white-space:nowrap}
.p282-rate{font-weight:900;color:#255fa8}
.p282-sns .p282-rate{color:#16805f}.p282-extra .p282-rate{color:#9a6516}
/* p282-execution-budget-ratio */
'''
    text = text.replace("</style>", css + "\n</style>", 1)
    text = text.replace("<title>v2.8.0 ·", "<title>v2.8.2 ·", 1)
    UI.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    apply_patch()
