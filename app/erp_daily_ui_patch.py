from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UI = ROOT / "ui" / "index.html"
MARKER = "v285-erp-daily-per-book"


def apply_patch() -> None:
    text = UI.read_text(encoding="utf-8")
    if MARKER in text:
        return

    script = r'''
<script>
// v285-erp-daily-per-book
(function(){
 const originalRenderPerformancePage = renderPerformancePage;
 renderPerformancePage = function(r){
   originalRenderPerformancePage(r);
   const erpRows = r.ERP일별판매실적 || [];
   const erpQty = erpRows.reduce((s,x)=>s+Number(x.매출부수||0),0);
   const erpAmount = erpRows.reduce((s,x)=>s+Number(x.매출금액||0),0);
   const sales = r.영업목표||{}, bp=r.사업계획목표||{};
   const goal12 = perfGoal12(sales,bp);
   const goalRate = goal12 ? erpQty/goal12*100 : null;

   const card=document.querySelector("#performanceContent .p271-book-card");
   if(card && !document.getElementById("erpDailyUploadBar")){
     const bar=document.createElement("div");
     bar.id="erpDailyUploadBar";bar.className="erp-daily-upload-bar";
     const first=erpRows[0]?.매출일자||null,last=erpRows[erpRows.length-1]?.매출일자||null;
     bar.innerHTML=`<div><b>ERP 일별 판매 데이터</b><span>${erpRows.length?`${erpRows.length.toLocaleString("ko-KR")}일 · ${first||"—"} ~ ${last||"—"}`:"아직 이 도서의 ERP 일별 데이터가 없습니다."}</span></div><button id="erpDailyUploadBtn">ERP 일별 데이터 업로드</button>`;
     card.insertAdjacentElement("afterend",bar);
     document.getElementById("erpDailyUploadBtn").onclick=uploadCurrentBookErpDaily;
   }

   const kpis=[...document.querySelectorAll("#performanceContent .p271-kpi")];
   if(kpis[0])kpis[0].innerHTML=`<span>ERP 누적 매출부수</span><strong>${erpRows.length?erpQty.toLocaleString("ko-KR")+"부":"—"}</strong><small>${erpRows.length?`일별 순매출 ${erpRows.length.toLocaleString("ko-KR")}일 집계`:"ERP 일별 데이터 없음"}</small>`;
   if(kpis[1])kpis[1].innerHTML=`<span>ERP 누적 매출액</span><strong>${erpRows.length?perfMoneyWon(erpAmount):"—"}</strong><small>${erpRows.length?`순매출 기준 ${erpQty.toLocaleString("ko-KR")}부`:"ERP 일별 데이터 없음"}</small>`;
   if(kpis[2])kpis[2].innerHTML=`<span>12개월 목표 대비</span><strong>${erpRows.length&&goalRate!==null?goalRate.toFixed(1)+"%":"—"}</strong><small>${goal12?goal12.toLocaleString("ko-KR")+"부 목표 기준":"영업목표 없음"}</small>`;
   if(kpis[3]){
     const first=erpRows[0]?.매출일자,last=erpRows[erpRows.length-1]?.매출일자;
     kpis[3].innerHTML=`<span>ERP 데이터 기간</span><strong>${erpRows.length?erpRows.length.toLocaleString("ko-KR")+"일":"—"}</strong><small>${erpRows.length?`${first} ~ ${last}`:"업로드 대기"}</small>`;
   }

   const heads=[...document.querySelectorAll("#performanceContent .p271-panel-head h3")];
   const salesHead=heads.find(h=>(h.textContent||"").startsWith("2."));
   if(salesHead){const p=salesHead.parentElement.querySelector("p");if(p)p.textContent="ERP 일별 순매출과 실제 마케팅 집행기간을 같은 날짜축에서 비교합니다.";}
   const legend=document.querySelector("#performanceContent .p271-legend");
   if(legend)legend.innerHTML='<span class="erp">ERP 일별 매출부수</span>';
   const note=document.querySelector("#performanceContent .p271-note");
   if(note)note.innerHTML='<b>기준:</b> ERP에서 도서별로 내려받은 일별 파일의 「매출부수·매출금액」을 사용합니다. SCM 실판매는 아직 연결하지 않습니다.';

   const summaryBoxes=[...document.querySelectorAll("#performanceContent .p271-summary-box")];
   if(summaryBoxes[0])summaryBoxes[0].innerHTML=`<span>ERP 판매 경과</span><strong>${erpRows.length?erpQty.toLocaleString("ko-KR")+"부":"데이터 업로드 대기"}</strong><p>${erpRows.length?`누적 ERP 순매출 ${perfMoneyWon(erpAmount)} · ${erpRows.length.toLocaleString("ko-KR")}일 데이터 기준입니다.`:"이 도서의 ERP 일별 판매 파일을 업로드하면 자동 반영됩니다."}</p>`;
 };

 window.uploadCurrentBookErpDaily=async function(){
   if(!currentPerformanceCode){toast("먼저 도서를 선택해 주세요.");return;}
   const btn=document.getElementById("erpDailyUploadBtn");
   try{
     if(btn){btn.disabled=true;btn.textContent="업로드 중...";}
     const r=await pywebview.api.import_erp_daily_excel(currentPerformanceCode);
     if(r.cancelled)return;
     if(!r.ok){toast(r.message||"ERP 일별 데이터 업로드 실패");return;}
     toast(`ERP 일별 데이터 ${Number(r.total||0).toLocaleString("ko-KR")}건을 반영했습니다.`);
     await loadPerformanceDetail(currentPerformanceCode);
   }catch(e){toast("ERP 일별 데이터 업로드 오류: "+e);}
   finally{if(btn){btn.disabled=false;btn.textContent="ERP 일별 데이터 업로드";}}
 };
})();
</script>
'''
    css = r'''
<style>
/* v285-erp-daily-per-book */
.erp-daily-upload-bar{display:flex;align-items:center;justify-content:space-between;gap:18px;margin:12px 0 14px;padding:14px 16px;background:#f7faff;border:1px solid #cfe0f3;border-radius:11px}
.erp-daily-upload-bar div{min-width:0}.erp-daily-upload-bar b{display:block;font-size:14px;color:#234d78}.erp-daily-upload-bar span{display:block;margin-top:4px;font-size:12px;color:#68788b}
.erp-daily-upload-bar button{height:38px;padding:0 16px;border:0;border-radius:8px;background:#2864bd;color:#fff;font-size:12px;font-weight:800;cursor:pointer;white-space:nowrap}.erp-daily-upload-bar button:disabled{opacity:.55;cursor:not-allowed}
</style>
'''
    if "</body>" not in text or "</head>" not in text:
        raise RuntimeError("ERP 일별 UI 패치 기준점을 찾지 못했습니다.")
    text=text.replace("</head>",css+"\n</head>",1)
    text=text.replace("</body>",script+"\n</body>",1)
    UI.write_text(text,encoding="utf-8")


if __name__ == "__main__":
    apply_patch()
