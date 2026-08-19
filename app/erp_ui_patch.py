from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UI = ROOT / "ui" / "index.html"
MARKER = "p283-erp-upload"


def apply_patch() -> None:
    text = UI.read_text(encoding="utf-8")
    if MARKER in text:
        return

    old_toolbar = '<div class="performance-toolbar"><b>도서 선택</b><select id="performanceProductSelect" onchange="loadPerformanceDetail(this.value)"></select><span id="performanceLoadState">목록 불러오는 중...</span></div>'
    new_toolbar = '<div class="performance-toolbar"><b>도서 선택</b><select id="performanceProductSelect" onchange="loadPerformanceDetail(this.value)"></select><span id="performanceLoadState">목록 불러오는 중...</span><button class="p283-erp-btn" onclick="importErpMonthlyExcel()">ERP 월별 데이터 업로드</button></div>'
    if old_toolbar not in text:
        raise RuntimeError("성과 화면 도서 선택 영역을 찾지 못했습니다.")
    text = text.replace(old_toolbar, new_toolbar, 1)

    old_note = '<div class="performance-note"><div><b>현재 단계</b> · Supabase의 기획·활동 데이터는 실제 연결됩니다. SCM·ERP 일별 판매 원천은 아직 본 시스템에 연결되지 않아 판매 그래프와 누적 실적은 <b>화면 검증용 예시 데이터</b>로 표시합니다.</div><span class="tag">SCM/ERP 연동 예정</span></div>'
    new_note = '<div class="performance-note"><div><b>ERP 월별 실적</b> · 아이세움·북폴리오 2개 시트의 월별 ERP 데이터를 업로드할 수 있습니다. 동일 제품코드·년월은 중복 생성하지 않고 최신 값으로 갱신합니다.</div><span class="tag">ERP 실데이터</span></div>'
    if old_note in text:
        text = text.replace(old_note, new_note, 1)

    js_anchor = 'async function loadPerformancePlanList(){'
    js = r'''async function importErpMonthlyExcel(){
 const btn=document.querySelector(".p283-erp-btn");
 if(btn){btn.disabled=true;btn.textContent="ERP 업로드 중...";}
 try{
   const r=await pywebview.api.import_erp_monthly_excel();
   if(r.cancelled)return;
   if(!r.ok){toast(r.message||"ERP 업로드에 실패했습니다.");return;}
   const sheets=Object.entries(r.sheet_counts||{}).map(([k,v])=>`${k} ${Number(v).toLocaleString("ko-KR")}건`).join(" · ");
   toast(`ERP 업로드 완료 · ${Number(r.total||0).toLocaleString("ko-KR")}건`);
   performanceLoadState.textContent=`ERP ${Number(r.total||0).toLocaleString("ko-KR")}건 업로드 완료 · ${sheets}`;
   if(currentPerformanceCode)await loadPerformanceDetail(currentPerformanceCode);
 }catch(e){toast("ERP 업로드 오류: "+(e?.message||e));}
 finally{if(btn){btn.disabled=false;btn.textContent="ERP 월별 데이터 업로드";}}
}

'''
    if js_anchor not in text:
        raise RuntimeError("성과 화면 JavaScript 기준점을 찾지 못했습니다.")
    text = text.replace(js_anchor, js + js_anchor, 1)

    css = r'''
/* p283-erp-upload */
.p283-erp-btn{margin-left:auto;height:38px;padding:0 14px;border:1px solid #87a9ca;border-radius:8px;background:#f2f7fb;color:#174d78;font-size:13px;font-weight:900;cursor:pointer}
.p283-erp-btn:hover{background:#e7f0f8}.p283-erp-btn:disabled{opacity:.55;cursor:wait}
'''
    text = text.replace("</style>", css + "\n</style>", 1)
    UI.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    apply_patch()
