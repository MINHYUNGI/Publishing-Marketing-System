from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UI = ROOT / "ui" / "index.html"
MARKER = "v287-admin-erp-auto-detect"


def apply_patch() -> None:
    text = UI.read_text(encoding="utf-8")
    if MARKER in text:
        return

    script = r'''
<script>
// v287-admin-erp-auto-detect
(function(){
 function ensureAdminView(){
   if(document.getElementById("navDataAdmin")) return;
   const nav=document.querySelector(".nav"),workspace=document.querySelector(".workspace");
   if(!nav||!workspace)return;

   const mgmt=document.createElement("div");mgmt.className="nav-group";mgmt.textContent="MANAGEMENT";nav.appendChild(mgmt);
   const btn=document.createElement("button");btn.id="navDataAdmin";btn.title="데이터 관리";btn.innerHTML='<span class="nav-icon">⚙</span><span class="nav-label">데이터 관리</span>';btn.onclick=showDataAdminPage;nav.appendChild(btn);

   const page=document.createElement("div");page.id="dataAdminPage";page.className="page-view";
   page.innerHTML=`
    <div class="title"><div><h1>데이터 관리</h1><div class="sub">성과 대시보드에 사용하는 원천 데이터를 관리합니다.</div></div><span class="badge">ADMIN</span></div>
    <section class="panel admin-data-panel">
      <div class="head"><div><strong>ERP 일별 판매 데이터</strong><small>ERP에서 도서별 일별 매출 엑셀을 내려받아 그대로 업로드합니다. 시스템이 제품코드를 자동으로 찾아 해당 도서에 연결합니다.</small></div></div>
      <div class="admin-data-body">
        <div class="admin-data-info"><b>자동 연결 및 중복 처리</b><span>엑셀 안의 제품코드를 자동 인식합니다. 한 파일에는 한 도서만 있어야 합니다. 이미 등록된 날짜는 값이 같으면 건너뛰고, 값이 바뀐 날짜는 수정하며, 새로운 날짜만 추가합니다.</span></div>
        <button class="btn primary admin-upload-btn" id="erpAdminUploadBtn">ERP 일별 데이터 업로드</button>
        <div id="erpUploadResult" class="admin-upload-result">아직 업로드한 파일이 없습니다.</div>
      </div>
    </section>`;
   workspace.appendChild(page);
   document.getElementById("erpAdminUploadBtn").onclick=uploadErpDailyData;
 }

 window.showDataAdminPage=function(){
   ["uploadPage","detailPage","performancePage","dataAdminPage"].forEach(id=>{const e=document.getElementById(id);if(e)e.classList.toggle("active",id==="dataAdminPage");});
   ["navUpload","navDetail","navPerformance","navDataAdmin"].forEach(id=>{const e=document.getElementById(id);if(e)e.classList.toggle("active",id==="navDataAdmin");});
   const title=document.getElementById("pageHeaderTitle"),sub=document.getElementById("pageHeaderSub");
   if(title)title.textContent="데이터 관리";
   if(sub)sub.textContent="ERP·SCM 등 성과 원천 데이터를 업로드하고 관리합니다.";
 };

 window.uploadErpDailyData=async function(){
   const result=document.getElementById("erpUploadResult"),btn=document.getElementById("erpAdminUploadBtn");
   if(btn){btn.disabled=true;btn.textContent="업로드 중...";}
   try{
     const r=await pywebview.api.import_erp_daily_excel();
     if(r.cancelled){if(result)result.textContent="업로드를 취소했습니다.";return;}
     if(!r.ok){if(result)result.textContent=`업로드 실패: ${r.message||"알 수 없는 오류"}`;return;}
     const range=(r.date_from&&r.date_to)?`${r.date_from} ~ ${r.date_to}`:"기간 미확인";
     if(result)result.innerHTML=`<b>${r.product_name||r.product_code} · ${r.product_code}</b><br>${range}<br>신규 ${Number(r.inserted||0).toLocaleString("ko-KR")}일 · 수정 ${Number(r.updated||0).toLocaleString("ko-KR")}일 · 동일값 건너뜀 ${Number(r.unchanged||0).toLocaleString("ko-KR")}일`;
   }catch(e){if(result)result.textContent="업로드 오류: "+(e?.message||e);}
   finally{if(btn){btn.disabled=false;btn.textContent="ERP 일별 데이터 업로드";}}
 };

 const originalShowAppPage=window.showAppPage;
 if(typeof originalShowAppPage==="function"){
   window.showAppPage=function(page){
     const admin=document.getElementById("dataAdminPage");if(admin)admin.classList.remove("active");
     const adminNav=document.getElementById("navDataAdmin");if(adminNav)adminNav.classList.remove("active");
     return originalShowAppPage(page);
   };
 }
 if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",ensureAdminView);else ensureAdminView();
})();
</script>
'''
    if "</body>" not in text:
        raise RuntimeError("HTML body 종료 태그를 찾지 못했습니다.")
    text = text.replace("</body>", script + "\n</body>", 1)

    css = r'''
<style>
/* v287-admin-erp-auto-detect */
.admin-data-panel{max-width:1100px}.admin-data-body{padding:22px}.admin-data-info{padding:15px 17px;border:1px solid #d8e3f2;border-radius:10px;background:#f7faff;margin-bottom:16px}.admin-data-info b{display:block;font-size:14px;color:#344054;margin-bottom:6px}.admin-data-info span{font-size:13px;color:#667085;line-height:1.55}.admin-upload-btn{width:auto!important;min-width:220px;flex:none!important}.admin-upload-result{margin-top:14px;padding:14px 16px;border:1px solid #e1e6ec;border-radius:9px;background:#fbfcfe;color:#5d6877;font-size:13px;line-height:1.6}
</style>
'''
    text = text.replace("</head>", css + "\n</head>", 1)
    UI.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    apply_patch()
