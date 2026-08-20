from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UI = ROOT / "ui" / "index.html"
MARKER = "v295-execution-ui-activation"


def apply_patch() -> None:
    text = UI.read_text(encoding="utf-8")
    if MARKER in text:
        return

    script = r'''
<script>
// v295-execution-ui-activation
(function(){
 let scheduled=false;
 function activateExecutionPanel(){
   scheduled=false;
   const root=document.getElementById("performanceContent");
   if(!root||typeof window.renderExecutionPanel!=="function")return;
   const section3=[...root.querySelectorAll(".p271-panel")].find(p=>p.querySelector("h3")?.textContent.trim().startsWith("3."));
   if(!section3||section3.querySelector(".exec-groups"))return;
   window.renderExecutionPanel();
 }
 function scheduleActivation(){
   if(scheduled)return;
   scheduled=true;
   setTimeout(activateExecutionPanel,30);
 }
 const start=()=>{
   const root=document.getElementById("performanceContent");
   if(!root){setTimeout(start,100);return;}
   new MutationObserver(scheduleActivation).observe(root,{childList:true,subtree:true});
   scheduleActivation();
 };
 if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",start);else start();
})();
</script>
'''
    if "</body>" not in text:
        raise RuntimeError("HTML body 종료 태그를 찾지 못했습니다.")
    text = text.replace("</body>", script + "\n</body>", 1)
    UI.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    apply_patch()
