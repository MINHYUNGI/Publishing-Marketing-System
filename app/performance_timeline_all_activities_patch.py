from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UI = ROOT / "ui" / "index.html"
MARKER = "v291-performance-timeline-all-activities"


def apply_patch() -> None:
    text = UI.read_text(encoding="utf-8")
    if MARKER in text:
        return

    script = r'''
<script>
// v291-performance-timeline-all-activities
(function(){
 function groupInfo(a){
   const raw=String(a?.활동분류||"");
   if(raw.includes("서점")) return {key:"store",label:"서점 마케팅"};
   if(raw.includes("SNS")||raw.includes("바이럴")) return {key:"sns",label:"SNS·바이럴 마케팅"};
   return {key:"extra",label:"추가 마케팅"};
 }
 function sortWithinGroup(arr){
   return [...arr].sort((a,b)=>{
     const ad=String(a?.실제시작일||a?.시작일||"9999-12-31");
     const bd=String(b?.실제시작일||b?.시작일||"9999-12-31");
     return ad.localeCompare(bd)||String(a?.활동명||"").localeCompare(String(b?.활동명||""),"ko");
   });
 }
 window.renderP271SalesGrid=function(){
   const root=document.getElementById("p271SalesGrid");if(!root)return;
   const rows=performanceVisibleSeries(),allActs=currentPerformanceData?.마케팅활동||[];
   if(!rows.length){root.innerHTML='<div class="perf-empty">이 조회기간에 ERP 일별 판매 데이터가 없습니다.</div>';const t=document.getElementById("p271PeriodText");if(t)t.textContent="";return;}
   const dayMs=86400000,startDate=perfDate(rows[0].date),endDate=perfDate(rows.at(-1).date),n=rows.length;
   const cellPct=100/n,centerPct=i=>(i+.5)*cellPct,centerX=i=>(i+.5)/n*1000;
   const dayIndex=d=>Math.round((perfDate(d)-startDate)/dayMs);
   const pub=currentPerformanceData?.기본정보?.출간일,pubDate=perfDate(pub),pubIdx=pubDate?dayIndex(pubDate):-1,pubPct=pubIdx>=0&&pubIdx<n?centerPct(pubIdx):null;
   const max=Math.max(10,...rows.flatMap(x=>[perfNum(x.scm),perfNum(x.erp)]))*1.12;
   const H=220,T=20,B=34,ph=H-T-B,y=v=>T+ph-(perfNum(v)/max)*ph;
   const grids=[.25,.5,.75,1].map(t=>`<line x1="0" y1="${T+ph*(1-t)}" x2="1000" y2="${T+ph*(1-t)}"/>`).join("");
   const bw=Math.max(4,Math.min(16,760/n));
   const bars=rows.map((r,i)=>`<rect x="${centerX(i)-bw/2}" y="${y(r.erp)}" width="${bw}" height="${Math.max(0,T+ph-y(r.erp))}" rx="2"/>`).join("");
   const hasScm=rows.some(r=>perfNum(r.scm)!==0);
   const scmLine=hasScm?`<polyline fill="none" stroke="#316fc8" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round" points="${rows.map((r,i)=>`${centerX(i)},${y(r.scm)}`).join(" ")}"/>`:"";

   const calendarBands=[],mondayLabels=[],mondayLines=[];
   rows.forEach((r,i)=>{
     const d=perfDate(r.date);if(!d)return;const dow=d.getDay(),left=i*cellPct;
     if(dow===6)calendarBands.push(`<span class="p289-dayband p289-sat" style="left:${left}%;width:${cellPct}%"></span>`);
     if(dow===0)calendarBands.push(`<span class="p289-dayband p289-sun" style="left:${left}%;width:${cellPct}%"></span>`);
     if(dow===1){const label=`${d.getMonth()+1}/${d.getDate()}(월)`;let cls="p289-monday-label";if(left<2)cls+=" edge-left";else if(left>91)cls+=" edge-right";mondayLabels.push(`<span class="${cls}" style="left:${left}%">${label}</span>`);mondayLines.push(`<span class="p289-monday-line" style="left:${left}%"></span>`);}
   });

   const buckets=[{key:"store",label:"서점 마케팅",items:[]},{key:"sns",label:"SNS·바이럴 마케팅",items:[]},{key:"extra",label:"추가 마케팅",items:[]}];
   allActs.forEach(a=>{const g=groupInfo(a);buckets.find(x=>x.key===g.key).items.push(a)});
   const leftParts=[],rightParts=[];
   buckets.forEach(g=>{
     if(!g.items.length)return;
     const items=sortWithinGroup(g.items);
     leftParts.push(`<div class="p290-group-head ${g.key}"><b>${g.label}</b><span>${items.length}건</span></div>`);
     rightParts.push(`<div class="p290-group-track ${g.key}"><span>${g.label}</span></div>`);
     items.forEach(a=>{
       const s=a.실제시작일||a.시작일||"",e=a.실제종료일||a.종료일||s;
       leftParts.push(`<div class="p271-activity-label"><b>${esc(a.활동명||"활동")}</b><small>${esc(s||"일정 미정")}${e&&e!==s?`~${esc(e)}`:""}</small></div>`);
       const ss=perfDate(s),ee=perfDate(e)||ss;
       if(!ss){rightParts.push('<div class="p271-activity-track p291-outside"><span class="p291-status">일정 미정</span></div>');return;}
       if(ee<startDate||ss>endDate){rightParts.push('<div class="p271-activity-track p291-outside"><span class="p291-status">조회기간 밖</span></div>');return;}
       const clippedStart=ss<startDate?startDate:ss,clippedEnd=ee>endDate?endDate:ee;
       const sIdx=Math.max(0,Math.min(n-1,Math.round((clippedStart-startDate)/dayMs)));
       const eIdx=Math.max(0,Math.min(n-1,Math.round((clippedEnd-startDate)/dayMs)));
       const left=sIdx*cellPct,width=Math.max(cellPct,(eIdx-sIdx+1)*cellPct);
       const before=ss<startDate,after=ee>endDate;
       rightParts.push(`<div class="p271-activity-track"><div class="p271-actbar ${g.key} ${before?'p291-clip-before':''} ${after?'p291-clip-after':''}" style="left:${left}%;width:${Math.min(100-left,width)}%">${esc(a.활동명||"")}</div></div>`);
     });
   });

   root.innerHTML=`<div class="p271-sales-grid p289-sales-grid p290-sales-grid p291-sales-grid"><div class="p271-sales-left"><div class="p271-chart-label">일별 판매·출고</div>${leftParts.join("")||'<div class="p271-activity-label"><b>등록된 활동 없음</b></div>'}</div><div class="p271-timeline-area p289-timeline-area"><div class="p289-calendar-bg">${calendarBands.join("")}${mondayLines.join("")}</div><div class="p271-chart p289-chart"><svg viewBox="0 0 1000 220" preserveAspectRatio="none"><g stroke="#e9edf2">${grids}</g><g fill="#a2adbb" opacity=".82">${bars}</g>${scmLine}</svg><div class="p289-date-axis">${mondayLabels.join("")}</div>${pubPct!==null?`<div class="p271-publine" style="left:${pubPct}%"></div><div class="p271-pubbadge" style="left:${pubPct}%">${perfDateText(pub)} 출간</div>`:""}</div>${rightParts.join("")||'<div class="p271-activity-track"></div>'}</div></div>`;
   const t=document.getElementById("p271PeriodText");if(t)t.textContent=`${perfDateText(rows[0].date)}~${perfDateText(rows.at(-1).date)}`;
 };
})();
</script>
'''
    css = r'''
<style>
/* v291-performance-timeline-all-activities */
.p291-outside{display:flex;align-items:center;justify-content:flex-end;padding-right:10px;background:rgba(248,250,252,.72)!important}
.p291-status{font-size:10px;font-weight:700;color:#98a2b3;border:1px solid #e1e6ec;background:#fff;border-radius:999px;padding:3px 8px}
.p291-clip-before{border-left-style:dashed!important}.p291-clip-after{border-right-style:dashed!important}
</style>
'''
    if "</head>" not in text or "</body>" not in text:
        raise RuntimeError("HTML 기준점을 찾지 못했습니다.")
    text=text.replace("</head>",css+"\n</head>",1)
    text=text.replace("</body>",script+"\n</body>",1)
    UI.write_text(text,encoding="utf-8")


if __name__ == "__main__":
    apply_patch()
