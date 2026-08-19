from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UI = ROOT / "ui" / "index.html"
MARKER = "v283-admin-data-management"


def apply_patch() -> None:
    text = UI.read_text(encoding="utf-8")
    if MARKER in text:
        return

    # 좌측 메뉴의 MANAGEMENT 그룹에 관리자 데이터 관리 메뉴 추가
    nav_anchor = '<div class="nav-group">MANAGEMENT</div>'
    if nav_anchor not in text:
        raise RuntimeError("MANAGEMENT 메뉴 기준점을 찾지 못했습니다.")
    nav = nav_anchor + '\n<button id="navDataAdmin" onclick="showDataAdminView()">데이터 관리</button>'
    text = text.replace(nav_anchor, nav, 1)

    # main 영역 끝에 관리자 화면 추가
    view_anchor = '<div id="performanceView"'
    pos = text.find(view_anchor)
    if pos < 0:
        raise RuntimeError("성과 화면 기준점을 찾지 못했습니다.")
    # performanceView가 시작되기 직전에 별도 view를 삽입
    admin_html = r'''<div id="dataAdminView" style="display:none">
  <div class="title"><div><h1>데이터 관리</h1><div class="sub">성과 대시보드에 사용하는 원천 데이터를 관리합니다.</div></div><span class="badge">ADMIN</span></div>
  <section class="panel admin-data-panel">
   <div class="head"><div><strong>ERP 월별 판매 데이터</strong><small>아이세움·북폴리오 두 시트를 모두 읽어 제품코드 × 년월 기준으로 Supabase에 반영합니다.</small></div></div>
   <div class="admin-data-body">
    <div class="admin-data-info"><b>업로드 기준</b><span>동일 제품코드·년월은 갱신하고, 신규 월은 추가합니다. 제품코드가 없는 합계/소계 행은 제외합니다.</span></div>
    <button class="btn primary admin-upload-btn" onclick="uploadErpMonthlyData()">ERP 월별 데이터 업로드</button>
    <div id="erpUploadResult" class="admin-upload-result">아직 업로드한 파일이 없습니다.</div>
   </div>
  </section>
 </div>
'''
    text = text[:pos] + admin_html + text[pos:]

    # 관리자 화면 JS
    js_anchor = 'function showView('
    js_pos = text.find(js_anchor)
    if js_pos < 0:
        raise RuntimeError("showView 함수를 찾지 못했습니다.")
    admin_js = r'''
function showDataAdminView(){
 document.querySelectorAll(".nav button").forEach(b=>b.classList.remove("active"));
 const n=document.getElementById("navDataAdmin");if(n)n.classList.add("active");
 ["uploadView","detailView","performanceView"].forEach(id=>{const e=document.getElementById(id);if(e)e.style.display="none"});
 const v=document.getElementById("dataAdminView");if(v)v.style.display="block";
}
async function uploadErpMonthlyData(){
 const result=document.getElementById("erpUploadResult");
 if(result)result.textContent="ERP 파일을 선택해 주세요.";
 const r=await pywebview.api.import_erp_monthly_sales();
 if(!r.ok){if(result)result.textContent=`업로드 실패: ${r.message||"알 수 없는 오류"}`;toast(r.message||"ERP 업로드 실패");return;}
 if(r.cancelled){if(result)result.textContent="업로드를 취소했습니다.";return;}
 const sheets=(r.sheets||[]).map(x=>`${x.sheet}: ${Number(x.rows||0).toLocaleString("ko-KR")}건`).join(" · ");
 if(result)result.innerHTML=`<b>${esc(r.file_name||"")}</b><br>${Number(r.rows||0).toLocaleString("ko-KR")}건 반영 완료${sheets?` · ${esc(sheets)}`:""}`;
 toast(`ERP ${Number(r.rows||0).toLocaleString("ko-KR")}건 반영 완료`);
}

'''
    text = text[:js_pos] + admin_js + text[js_pos:]

    css = r'''
/* v283-admin-data-management */
.admin-data-panel{max-width:1100px}
.admin-data-body{padding:22px}
.admin-data-info{padding:15px 17px;border:1px solid #d8e3f2;border-radius:10px;background:#f7faff;margin-bottom:16px}
.admin-data-info b{display:block;font-size:14px;color:#344054;margin-bottom:6px}.admin-data-info span{font-size:13px;color:#667085;line-height:1.55}
.admin-upload-btn{width:auto;min-width:220px;flex:none}
.admin-upload-result{margin-top:14px;padding:14px 16px;border:1px solid #e1e6ec;border-radius:9px;background:#fbfcfe;color:#5d6877;font-size:13px;line-height:1.55}
'''
    text = text.replace("</style>", css + "\n</style>", 1)
    UI.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    apply_patch()
