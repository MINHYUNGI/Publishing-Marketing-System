from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UI = ROOT / "ui" / "index.html"
MARKER = "v287-restart-latest-sidebar"


def apply_patch() -> None:
    text = UI.read_text(encoding="utf-8")
    if MARKER in text:
        return

    script = r'''
<script>
// v287-restart-latest-sidebar
(function(){
 function addRestartButton(){
   if(document.getElementById("restartLatestBtn"))return;
   const sidebar=document.querySelector(".sidebar");
   if(!sidebar)return;
   const wrap=document.createElement("div");
   wrap.className="restart-latest-wrap";
   wrap.innerHTML='<button id="restartLatestBtn" class="restart-latest-btn" title="GitHub 최신 버전으로 다시 시작"><span>↻</span><b>최신 버전으로 다시 시작</b></button>';
   const user=sidebar.querySelector(".user");
   if(user)sidebar.insertBefore(wrap,user);else sidebar.appendChild(wrap);
   document.getElementById("restartLatestBtn").onclick=async function(){
     if(!confirm("프로그램을 종료하고 GitHub 최신 버전으로 다시 시작하시겠습니까?"))return;
     const btn=this;btn.disabled=true;btn.querySelector("b").textContent="업데이트 후 다시 시작 중...";
     try{
       const r=await pywebview.api.restart_latest_version();
       if(!r?.ok){btn.disabled=false;btn.querySelector("b").textContent="최신 버전으로 다시 시작";toast(r?.message||"재시작에 실패했습니다.");}
     }catch(e){btn.disabled=false;btn.querySelector("b").textContent="최신 버전으로 다시 시작";toast("재시작 실패: "+e);}
   };
 }
 if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",addRestartButton);else addRestartButton();
})();
</script>
'''
    css = r'''
<style>
/* v287-restart-latest-sidebar */
.restart-latest-wrap{padding:8px 10px 10px;margin-top:auto}
.restart-latest-btn{width:100%;min-height:42px;border:1px solid rgba(255,255,255,.16);border-radius:9px;background:rgba(255,255,255,.06);color:#dce6f4;display:flex;align-items:center;gap:9px;padding:0 12px;cursor:pointer;text-align:left}
.restart-latest-btn:hover{background:rgba(255,255,255,.12)}
.restart-latest-btn span{font-size:18px}.restart-latest-btn b{font-size:12px;font-weight:800}
.restart-latest-btn:disabled{opacity:.65;cursor:wait}
.app.sidebar-collapsed .restart-latest-wrap{padding:8px}
.app.sidebar-collapsed .restart-latest-btn{justify-content:center;padding:0;font-size:0}.app.sidebar-collapsed .restart-latest-btn b{display:none}
</style>
'''
    if "</body>" not in text or "</head>" not in text:
        raise RuntimeError("재시작 버튼을 삽입할 HTML 기준점을 찾지 못했습니다.")
    text = text.replace("</body>", script + "\n</body>", 1)
    text = text.replace("</head>", css + "\n</head>", 1)
    UI.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    apply_patch()
