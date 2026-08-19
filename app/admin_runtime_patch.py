from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UI = ROOT / "ui" / "index.html"
MARKER = "v285-admin-data-management"


def apply_patch() -> None:
    text = UI.read_text(encoding="utf-8")
    if MARKER in text:
        return

    script = r'''
<script>
// v285-admin-data-management
(function(){
 function ensureAdminView(){
   if(document.getElementById("navDataAdmin")) return;

   const nav=document.querySelector(".nav");
   const workspace=document.querySelector(".workspace");
   if(!nav || !workspace) return;

   // 관리자 메뉴 그룹과 버튼
   const mgmt=document.createElement("div");
   mgmt.className="nav-group";
   mgmt.textContent="MANAGEMENT";
   nav.appendChild(mgmt);

   const btn=document.createElement("button");
   btn.id="navDataAdmin";
   btn.title="데이터 관리";
   btn.innerHTML='<span class="nav-icon">⚙</span><span class="nav-label">데이터 관리</span>';
   btn.onclick=showDataAdminPage;
   nav.appendChild(btn);

   // 기존 upload/detail/performance와 동일한 page-view 구조 사용
   const page=document.createElement("div");
   page.id="dataAdminPage";
   page.className="page-view";
   page.innerHTML=`
    <div class="title"><div><h1>데이터 관리</h1><div class="sub">성과 대시보드에 사용하는 원천 데이터를 관리합니다.</div></div><span class="badge">ADMIN</span></div>
    <section class="panel admin-data-panel">
      <div class="head"><div><strong>ERP 월별 판매 데이터</strong><small>아이세움·북폴리오 두 시트를 모두 읽어 제품코드 × 년월 기준으로 Supabase에 반영합니다.</small></div></div>
      <div class="admin-data-body">
        <div class="admin-data-info"><b>업로드 기준</b><span>동일 제품코드·년월은 갱신하고 신규 월은 추가합니다. 제품코드가 없는 합계·소계 행은 제외합니다.</span></div>
        <button class="btn primary admin-upload-btn" id="erpAdminUploadBtn">ERP 월별 데이터 업로드</button>
        <div id="erpUploadResult" class="admin-upload-result">아직 업로드한 파일이 없습니다.</div>
      </div>
    </section>`;
   workspace.appendChild(page);
   document.getElementById("erpAdminUploadBtn").onclick=uploadErpMonthlyData;
 }

 window.showDataAdminPage=function(){
   ["uploadPage","detailPage","performancePage","dataAdminPage"].forEach(id=>{
     const e=document.getElementById(id); if(e)e.classList.toggle("active",id==="dataAdminPage");
   });
   ["navUpload","navDetail","navPerformance","navDataAdmin"].forEach(id=>{
     const e=document.getElementById(id); if(e)e.classList.toggle("active",id==="navDataAdmin");
   });
   const title=document.getElementById("pageHeaderTitle");
   const sub=document.getElementById("pageHeaderSub");
   if(title)title.textContent="데이터 관리";
   if(sub)sub.textContent="ERP·SCM 등 성과 원천 데이터를 업로드하고 관리합니다.";
 };

 window.uploadErpMonthlyData=async function(){
   const result=document.getElementById("erpUploadResult");
   const btn=document.getElementById("erpAdminUploadBtn");
   if(btn){btn.disabled=true;btn.textContent="업로드 중...";}
   try{
     const r=await pywebview.api.import_erp_monthly_excel();
     if(r.cancelled){if(result)result.textContent="업로드를 취소했습니다.";return;}
     if(!r.ok){if(result)result.textContent=`업로드 실패: ${r.message||"알 수 없는 오류"}`;return;}
     const sheets=Object.entries(r.sheet_counts||{}).map(([k,v])=>`${k}: ${Number(v||0).toLocaleString("ko-KR")}건`).join(" · ");
     if(result)result.innerHTML=`<b>${r.file_name||"ERP 파일"}</b><br>${Number(r.total||0).toLocaleString("ko-KR")}건 반영 완료${sheets?` · ${sheets}`:""}`;
   }catch(e){
     if(result)result.textContent="업로드 오류: "+(e?.message||e);
   }finally{
     if(btn){btn.disabled=false;btn.textContent="ERP 월별 데이터 업로드";}
   }
 };

 // 기존 메뉴로 돌아갈 때 관리자 화면 active 해제
 const originalShowAppPage=window.showAppPage;
 if(typeof originalShowAppPage==="function"){
   window.showAppPage=function(page){
     const admin=document.getElementById("dataAdminPage"); if(admin)admin.classList.remove("active");
     const adminNav=document.getElementById("navDataAdmin"); if(adminNav)adminNav.classList.remove("active");
     return originalShowAppPage(page);
   };
 }

 if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",ensureAdminView); else ensureAdminView();
})();
</script>
'''
    if "</body>" not in text:
        raise RuntimeError("HTML body 종료 태그를 찾지 못했습니다.")
    text = text.replace("</body>", script + "\n</body>", 1)

    css = r'''
<style>
/* v285-admin-data-management */
.admin-data-panel{max-width:1100px}
.admin-data-body{padding:22px}
.admin-data-info{padding:15px 17px;border:1px solid #d8e3f2;border-radius:10px;background:#f7faff;margin-bottom:16px}
.admin-data-info b{display:block;font-size:14px;color:#344054;margin-bottom:6px}
.admin-data-info span{font-size:13px;color:#667085;line-height:1.55}
.admin-upload-btn{width:auto!important;min-width:220px;flex:none!important}
.admin-upload-result{margin-top:14px;padding:14px 16px;border:1px solid #e1e6ec;border-radius:9px;background:#fbfcfe;color:#5d6877;font-size:13px;line-height:1.55}
</style>
'''
    text = text.replace("</head>", css + "\n</head>", 1)
    UI.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    apply_patch()
