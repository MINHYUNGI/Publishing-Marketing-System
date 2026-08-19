from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UI = ROOT / "ui" / "index.html"
MARKER = "v288-performance-timeline-weekly-axis"


def apply_patch() -> None:
    text = UI.read_text(encoding="utf-8")
    if MARKER in text:
        return

    script = r'''
<script>
// v288-performance-timeline-weekly-axis
(function(){
 const dayMs=86400000;
 function dayIndex(d,start){return Math.round((perfDate(d)-start)/dayMs);}
 function mondayText(d){const x=perfDate(d);return x?`${x.getMonth()+1}/${x.getDate()}(월)`:"";}

 window.renderP271SalesGrid=function(){
   const root=document.getElementById("p271SalesGrid");if(!root)return;
   const rows=performanceVisibleSeries(),acts=sortDetailActivities(currentPerformanceData?.마케팅활동||[]);
   if(!rows.length){
     root.innerHTML='<div class="perf-empty">이 조회기간에 ERP 일별 판매 데이터가 없습니다.</div>';
     const t=document.getElementById("p271PeriodText");if(t)t.textContent="";return;
   }

   const start=perfDate(rows[0].date),end=perfDate(rows.at(-1).date),n=rows.length;
   const cellPct=100/n;
   const centerPct=i=>(i+.5)*cellPct;
   const centerX=i=>(i+.5)/n*1000;
   const clampIndex=i=>Math.max(0,Math.min(n-1,i));

   const pub=currentPerformanceData?.기본정보?.출간일;
   const pubDate=perfDate(pub);
   const pubIdx=pubDate?dayIndex(pubDate,start):-1;
   const pubPct=pubIdx>=0&&pubIdx<n?centerPct(pubIdx):null;

   const max=Math.max(10,...rows.flatMap(x=>[x.scm,x.erp]))*1.12;
   const H=220,T=20,B=28,ph=H-T-B,y=v=>T+ph-(v/max)*ph;
   const grids=[.25,.5,.75,1].map(t=>`<line x1="0" y1="${T+ph*(1-t)}" x2="1000" y2="${T+ph*(1-t)}"/>`).join("");
   const bw=Math.max(5,Math.min(18,760/n));
   const bars=rows.map((r,i)=>`<rect x="${centerX(i)-bw/2}" y="${y(r.erp)}" width="${bw}" height="${Math.max(0,T+ph-y(r.erp))}" rx="2"/>`).join("");
   const hasScm=rows.some(r=>perfNum(r.scm)!==0);
   const scmLine=hasScm?`<polyline fill="none" stroke="#316fc8" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round" points="${rows.map((r,i)=>`${centerX(i)},${y(r.scm)}`).join(" ")}"/>`:"";

   const mondayTicks=[];
   const calendarBg=[];
   const weekLines=[];
   rows.forEach((r,i)=>{
     const d=perfDate(r.date);if(!d)return;
     const dow=d.getDay();
     const left=i*cellPct;
     if(dow===6)calendarBg.push(`<span class="p288-weekend p288-sat" style="left:${left}%;width:${cellPct}%"></span>`);
     if(dow===0)calendarBg.push(`<span class="p288-weekend p288-sun" style="left:${left}%;width:${cellPct}%"></span>`);
     if(dow===1){
       const transform=left<2?"translateX(0)":left>91?"translateX(-100%)":"translateX(-50%)";
       mondayTicks.push(`<span class="p271-tick p288-monday" style="left:${left}%;transform:${transform}">${mondayText(r.date)}</span>`);
       weekLines.push(`<span class="p288-weekline" style="left:${left}%"></span>`);
     }
   });

   const visible=acts.filter(a=>{
     const ss=perfDate(a.실제시작일||a.시작일),ee=perfDate(a.실제종료일||a.종료일)||ss;
     return ss&&ee>=start&&ss<=end;
   });

   const labels=visible.map(a=>{
     const s=a.실제시작일||a.시작일||"",e=a.실제종료일||a.종료일||s;
     return `<div class="p271-activity-label"><b>${esc(a.활동명||"활동")}</b><small>${esc(s)}${e&&e!==s?`~${esc(e)}`:""}</small></div>`;
   }).join("");

   const tracks=visible.map(a=>{
     const s0=a.실제시작일||a.시작일,e0=a.실제종료일||a.종료일||s0;
     const sIdx=clampIndex(dayIndex(s0,start)),eIdx=clampIndex(dayIndex(e0,start));
     const left=sIdx*cellPct,width=Math.max(cellPct,(eIdx-sIdx+1)*cellPct);
     const cl=(a.활동분류||"").includes("SNS")?"sns":(a.활동분류||"").includes("서점")?"store":"extra";
     return `<div class="p271-activity-track"><div class="p271-actbar ${cl}" style="left:${left}%;width:${Math.min(100-left,width)}%">${esc(a.활동명||"")}</div></div>`;
   }).join("");

   const emptyRow='<div class="p271-activity-label"><b>조회기간 활동 없음</b></div>';
   const emptyTrack='<div class="p271-activity-track"></div>';
   root.innerHTML=`<div class="p271-sales-grid p288-sales-grid">
     <div class="p271-sales-left">
       <div class="p271-chart-label">일별 판매·출고</div>
       <div class="p288-axis-spacer"></div>
       ${labels||emptyRow}
     </div>
     <div class="p271-timeline-area p288-timeline-area">
       <div class="p288-calendar-bg">${calendarBg.join("")}${weekLines.join("")}</div>
       <div class="p271-chart"><svg viewBox="0 0 1000 220" preserveAspectRatio="none"><g stroke="#e9edf2">${grids}</g><g fill="#a2adbb" opacity=".82">${bars}</g>${scmLine}</svg>${pubPct!==null?`<div class="p271-publine" style="left:${pubPct}%"></div><div class="p271-pubbadge" style="left:${pubPct}%">${perfDateText(pub)} 출간</div>`:""}</div>
       <div class="p271-axis">${mondayTicks.join("")}</div>
       ${tracks||emptyTrack}
     </div>
   </div>`;

   const t=document.getElementById("p271PeriodText");
   if(t)t.textContent=`${perfDateText(rows[0].date)}~${perfDateText(rows.at(-1).date)}`;
 };
})();
</script>
'''

    css = r'''
<style>
/* v288-performance-timeline-weekly-axis */
.p288-sales-grid{align-items:start}
.p288-axis-spacer{height:36px;border-top:1px solid var(--line);background:#fbfcfd}
.p288-timeline-area{position:relative;background:#fff;overflow:hidden}
.p288-timeline-area .p271-chart{height:220px;background:transparent;position:relative;z-index:2}
.p288-timeline-area .p271-chart svg{position:relative;z-index:2}
.p288-timeline-area .p271-axis{height:36px;background:transparent;position:relative;z-index:3;overflow:visible}
.p288-timeline-area .p271-activity-track{height:48px;background:transparent;position:relative;z-index:2}
.p288-sales-grid .p271-activity-label{height:48px}
.p288-calendar-bg{position:absolute;inset:0;z-index:1;pointer-events:none}
.p288-weekend{position:absolute;top:0;bottom:0}
.p288-sat{background:rgba(79,137,190,.075)}
.p288-sun{background:rgba(210,91,91,.075)}
.p288-weekline{position:absolute;top:0;bottom:0;width:1px;background:rgba(91,111,132,.16)}
.p288-monday{bottom:9px;font-size:11px;font-weight:800;color:#536579;z-index:4}
.p288-timeline-area .p271-actbar{z-index:4}
.p288-timeline-area .p271-publine{z-index:6}
.p288-timeline-area .p271-pubbadge{z-index:7;top:7px}
</style>
'''

    if "</body>" not in text or "</head>" not in text:
        raise RuntimeError("성과 화면 HTML 기준점을 찾지 못했습니다.")
    text=text.replace("</head>",css+"\n</head>",1)
    text=text.replace("</body>",script+"\n</body>",1)
    UI.write_text(text,encoding="utf-8")


if __name__ == "__main__":
    apply_patch()
