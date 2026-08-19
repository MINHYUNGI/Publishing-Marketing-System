from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UI = ROOT / "ui" / "index.html"
MARKER = "v289-performance-timeline-aligned-calendar"


def apply_patch() -> None:
    text = UI.read_text(encoding="utf-8")
    if MARKER in text:
        return

    start_token = "function renderP271SalesGrid(){"
    end_token = "async function savePerformanceNotes(){"
    start = text.find(start_token)
    end = text.find(end_token, start)
    if start < 0 or end < 0:
        raise RuntimeError("성과 타임라인 함수 기준점을 찾지 못했습니다.")

    new_func = r'''// v289-performance-timeline-aligned-calendar
function renderP271SalesGrid(){
 const root=document.getElementById("p271SalesGrid");if(!root)return;
 const rows=performanceVisibleSeries(),acts=sortDetailActivities(currentPerformanceData?.마케팅활동||[]);
 if(!rows.length){
   root.innerHTML='<div class="perf-empty">이 조회기간에 ERP 일별 판매 데이터가 없습니다.</div>';
   const t=document.getElementById("p271PeriodText");if(t)t.textContent="";return;
 }
 const dayMs=86400000;
 const startDate=perfDate(rows[0].date),endDate=perfDate(rows.at(-1).date),n=rows.length;
 const cellPct=100/n, centerPct=i=>(i+.5)*cellPct, centerX=i=>(i+.5)/n*1000;
 const dayIndex=d=>Math.round((perfDate(d)-startDate)/dayMs);
 const clampIndex=i=>Math.max(0,Math.min(n-1,i));
 const pub=currentPerformanceData?.기본정보?.출간일,pubDate=perfDate(pub),pubIdx=pubDate?dayIndex(pubDate):-1;
 const pubPct=pubIdx>=0&&pubIdx<n?centerPct(pubIdx):null;

 const max=Math.max(10,...rows.flatMap(x=>[perfNum(x.scm),perfNum(x.erp)]))*1.12;
 const H=220,T=20,B=34,ph=H-T-B,y=v=>T+ph-(perfNum(v)/max)*ph;
 const grids=[.25,.5,.75,1].map(t=>`<line x1="0" y1="${T+ph*(1-t)}" x2="1000" y2="${T+ph*(1-t)}"/>`).join("");
 const bw=Math.max(4,Math.min(16,760/n));
 const bars=rows.map((r,i)=>`<rect x="${centerX(i)-bw/2}" y="${y(r.erp)}" width="${bw}" height="${Math.max(0,T+ph-y(r.erp))}" rx="2"/>`).join("");
 const hasScm=rows.some(r=>perfNum(r.scm)!==0);
 const scmLine=hasScm?`<polyline fill="none" stroke="#316fc8" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round" points="${rows.map((r,i)=>`${centerX(i)},${y(r.scm)}`).join(" ")}"/>`:"";

 const calendarBands=[],mondayLabels=[],mondayLines=[];
 rows.forEach((r,i)=>{
   const d=perfDate(r.date);if(!d)return;
   const dow=d.getDay(),left=i*cellPct;
   if(dow===6)calendarBands.push(`<span class="p289-dayband p289-sat" style="left:${left}%;width:${cellPct}%"></span>`);
   if(dow===0)calendarBands.push(`<span class="p289-dayband p289-sun" style="left:${left}%;width:${cellPct}%"></span>`);
   if(dow===1){
     const label=`${d.getMonth()+1}/${d.getDate()}(월)`;
     let cls="p289-monday-label";
     if(left<2)cls+=" edge-left";else if(left>91)cls+=" edge-right";
     mondayLabels.push(`<span class="${cls}" style="left:${left}%">${label}</span>`);
     mondayLines.push(`<span class="p289-monday-line" style="left:${left}%"></span>`);
   }
 });

 const visible=acts.filter(a=>{
   const ss=perfDate(a.실제시작일||a.시작일),ee=perfDate(a.실제종료일||a.종료일)||ss;
   return ss&&ee>=startDate&&ss<=endDate;
 });
 const labels=visible.map(a=>{
   const s=a.실제시작일||a.시작일||"",e=a.실제종료일||a.종료일||s;
   return `<div class="p271-activity-label"><b>${esc(a.활동명||"활동")}</b><small>${esc(s)}${e&&e!==s?`~${esc(e)}`:""}</small></div>`;
 }).join("");
 const tracks=visible.map(a=>{
   const s0=a.실제시작일||a.시작일,e0=a.실제종료일||a.종료일||s0;
   const sIdx=clampIndex(dayIndex(s0)),eIdx=clampIndex(dayIndex(e0));
   const left=sIdx*cellPct,width=Math.max(cellPct,(eIdx-sIdx+1)*cellPct);
   const cl=(a.활동분류||"").includes("SNS")?"sns":(a.활동분류||"").includes("서점")?"store":"extra";
   return `<div class="p271-activity-track"><div class="p271-actbar ${cl}" style="left:${left}%;width:${Math.min(100-left,width)}%">${esc(a.활동명||"")}</div></div>`;
 }).join("");

 root.innerHTML=`<div class="p271-sales-grid p289-sales-grid">
   <div class="p271-sales-left">
     <div class="p271-chart-label">일별 판매·출고</div>
     ${labels||'<div class="p271-activity-label"><b>조회기간 활동 없음</b></div>'}
   </div>
   <div class="p271-timeline-area p289-timeline-area">
     <div class="p289-calendar-bg">${calendarBands.join("")}${mondayLines.join("")}</div>
     <div class="p271-chart p289-chart">
       <svg viewBox="0 0 1000 220" preserveAspectRatio="none"><g stroke="#e9edf2">${grids}</g><g fill="#a2adbb" opacity=".82">${bars}</g>${scmLine}</svg>
       <div class="p289-date-axis">${mondayLabels.join("")}</div>
       ${pubPct!==null?`<div class="p271-publine" style="left:${pubPct}%"></div><div class="p271-pubbadge" style="left:${pubPct}%">${perfDateText(pub)} 출간</div>`:""}
     </div>
     ${tracks||'<div class="p271-activity-track"></div>'}
   </div>
 </div>`;
 const t=document.getElementById("p271PeriodText");if(t)t.textContent=`${perfDateText(rows[0].date)}~${perfDateText(rows.at(-1).date)}`;
}

'''
    text = text[:start] + new_func + text[end:]

    css = r'''
<style>
/* v289-performance-timeline-aligned-calendar */
.p289-sales-grid{align-items:start}
.p289-sales-grid .p271-chart-label{height:220px}
.p289-sales-grid .p271-activity-label,.p289-timeline-area .p271-activity-track{height:48px}
.p289-timeline-area{position:relative;overflow:hidden;background:#fff}
.p289-chart{height:220px!important;position:relative;background:transparent!important;z-index:2;overflow:visible}
.p289-chart svg{position:relative;z-index:2}
.p289-calendar-bg{position:absolute;inset:0;z-index:1;pointer-events:none}
.p289-dayband{position:absolute;top:0;bottom:0}
.p289-sat{background:rgba(75,132,186,.10)}
.p289-sun{background:rgba(218,88,88,.10)}
.p289-monday-line{position:absolute;top:0;bottom:0;width:1px;background:rgba(70,91,111,.20)}
.p289-date-axis{position:absolute;left:0;right:0;bottom:0;height:30px;border-top:1px solid #dfe5ec;background:rgba(251,252,253,.94);z-index:5;overflow:visible}
.p289-monday-label{position:absolute;bottom:7px;transform:translateX(-50%);font-size:11px;font-weight:800;color:#536579;white-space:nowrap}
.p289-monday-label.edge-left{transform:none}.p289-monday-label.edge-right{transform:translateX(-100%)}
.p289-timeline-area .p271-actbar{z-index:4;top:10px;height:27px}
.p289-timeline-area .p271-publine{z-index:7}
.p289-timeline-area .p271-pubbadge{z-index:8;top:7px}
/* 기존 별도 날짜축은 사용하지 않습니다. 날짜는 그래프 하단에 겹쳐 표시합니다. */
.p289-sales-grid .p271-axis,.p289-sales-grid .p288-axis-spacer{display:none!important}
</style>
'''
    if "</head>" not in text:
        raise RuntimeError("HTML head 종료 태그를 찾지 못했습니다.")
    text = text.replace("</head>", css + "\n</head>", 1)
    UI.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    apply_patch()
