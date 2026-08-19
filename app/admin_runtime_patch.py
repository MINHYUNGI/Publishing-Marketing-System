from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UI = ROOT / "ui" / "index.html"
MARKER = "v286-admin-erp-daily"


def apply_patch() -> None:
    text = UI.read_text(encoding="utf-8")
    if MARKER in text:
        return

    script = r'''
<script>
// v286-admin-erp-daily
(function(){
 async function loadAdminProducts(){
   const sel=document.getElementById("erpAdminProductSelect");
   const state=document.getElementById("erpAdminProductState");
   if(!sel)return;
   if(state)state.textContent="도서 목록을 불러오는 중...";
   try{
     const r=await pywebview.api.get_marketing_plan_list();
     if(!r.ok){if(state)state.textContent="도서 목록 조회 실패";return;}
     const plans=r.plans||[];
     sel.innerHTML='<option value="">도서를 선택해 주세요</option>'+plans.map(x=>`<option value="${String(x.제품코드||"").replace(/"/g,'&quot;')}">${String(x.제품명||x.제품코드||"")} · ${String(x.제품코드||"")}</option>`).join('');
     if(state)state.textContent=`${plans.length}개 도서`;
   }catch(e){if(state)state.textContent="도서 목록 조회 실패";}
 }

 function ensureAdminView(){
   if(document.getElementById("navDataAdmin")) return;
   const nav=document.querySelector(".nav");
   const workspace=document.querySelector(".workspace");
   if(!nav || !workspace) return;

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

   const page=document.createElement("div");
   page.id="dataAdminPage";
   page.className="page-view";
   page.innerHTML=`
    <div class="title"><div><h1>데이터 관리</h1><div class="sub">성과 대시보드에 사용하는 원천 데이터를 관리합니다.</div></div><span class="badge">ADMIN</span></div>
    <section class="panel admin-data-panel">
      <div class="head"><div><strong>ERP 일별 판매 데이터</strong><small>ERP에서 조회한 도서별 일별 매출 엑셀을 선택한 도서에 연결합니다.</small></div></div>
      <div class="admin-data-body">
        <div class="admin-data-info"><b>업로드 기준</b><span>먼저 도서를 선택한 뒤 해당 도서의 ERP 일별 엑셀을 업로드합니다. 엑셀의 제품코드와 선택한 도서의 제품코드가 다르면 업로드를 차단합니다. 같은 제품코드·매출일자는 갱신합니다.</span></div>
        <div class="admin-product-row"><div><label>대상 도서</label><select id="erpAdminProductSelect" class="select"><option value="">도서를 선택해 주세요</option></select></div><span id="erpAdminProductState">도서 목록 대기</span></div>
        <button class="btn primary admin-upload-btn" id="erpAdminUploadBtn">ERP 일별 데이터 업로드</button>
        <div id="erpUploadResult" class="admin-upload-result">아직 업로드한 파일이 없습니다.</div>
      </div>
    </section>`;
   workspace.appendChild(page);
   document.getElementById("erpAdminUploadBtn").onclick=uploadErpDailyData;
 }

 window.showDataAdminPage=function(){
   ["uploadPage","detailPage","performancePage","dataAdminPage"].forEach(id=>{
     const e=document.getElementById(id); if(e)e.classList.toggle("active",id==="dataAdminPage");
   });
   ["navUpload","navDetail","navPerformance","navDataAdmin"].forEach(id=>{
     const e=document.getElementById(id); if(e)e.classList.toggle("active",id==="navDataAdmin");
   });
   const title=document.getElementById("pageHeaderTitle"),sub=document.getElementById("pageHeaderSub");
   if(title)title.textContent="데이터 관리";
   if(sub)sub.textContent="ERP·SCM 등 성과 원천 데이터를 업로드하고 관리합니다.";
   loadAdminProducts();
 };

 window.uploadErpDailyData=async function(){
   const result=document.getElementById("erpUploadResult"),btn=document.getElementById("erpAdminUploadBtn"),sel=document.getElementById("erpAdminProductSelect");
   const productCode=sel?.value||"";
   if(!productCode){if(result)result.textContent="업로드 실패: 먼저 대상 도서를 선택해 주세요.";return;}
   if(btn){btn.disabled=true;btn.textContent="업로드 중...";}
   try{
     const r=await pywebview.api.import_erp_daily_excel(productCode);
     if(r.cancelled){if(result)result.textContent="업로드를 취소했습니다.";return;}
     if(!r.ok){if(result)result.textContent=`업로드 실패: ${r.message||"알 수 없는 오류"}`;return;}
     const range=(r.min_date&&r.max_date)?` · ${r.min_date} ~ ${r.max_date}`:"";
     if(result)result.innerHTML=`<b>${r.product_name||productCode}</b><br>${Number(r.total||0).toLocaleString("ko-KR")}일 반영 완료${range} · ${r.file_name||"ERP 파일"}`;
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
/* v286-admin-erp-daily */
.admin-data-panel{max-width:1100px}.admin-data-body{padding:22px}.admin-data-info{padding:15px 17px;border:1px solid #d8e3f2;border-radius:10px;background:#f7faff;margin-bottom:16px}.admin-data-info b{display:block;font-size:14px;color:#344054;margin-bottom:6px}.admin-data-info span{font-size:13px;color:#667085;line-height:1.55}.admin-product-row{display:grid;grid-template-columns:minmax(320px,620px) auto;gap:12px;align-items:end;margin-bottom:14px}.admin-product-row label{display:block;font-size:12px;font-weight:800;color:#475467;margin-bottom:6px}.admin-product-row>span{font-size:12px;color:#667085;padding-bottom:10px}.admin-upload-btn{width:auto!important;min-width:220px;flex:none!important}.admin-upload-result{margin-top:14px;padding:14px 16px;border:1px solid #e1e6ec;border-radius:9px;background:#fbfcfe;color:#5d6877;font-size:13px;line-height:1.55}
</style>
'''
    text = text.replace("</head>", css + "\n</head>", 1)
    UI.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    apply_patch()
