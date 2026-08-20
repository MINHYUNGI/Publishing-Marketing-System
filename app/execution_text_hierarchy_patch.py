from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UI = ROOT / "ui" / "index.html"
MARKER = "v304-execution-text-hierarchy"


def apply_patch() -> None:
    text = UI.read_text(encoding="utf-8")
    if MARKER in text:
        return

    script = r'''
<script>
// v304-execution-text-hierarchy
(function(){
 function scale(){
   if(typeof globalFontScaleValue!=="undefined" && Number.isFinite(Number(globalFontScaleValue))) return Number(globalFontScaleValue)||1;
   return Math.max(.8,Math.min(2,Number(localStorage.getItem("fontScale")||100)/100));
 }
 function applyExecutionTextHierarchy(){
   const s=scale();
   document.querySelectorAll(".exec-table td strong").forEach(el=>{
     el.dataset.baseFontPx="11";
     el.dataset.performanceBaseFontPx="11";
     el.style.setProperty("font-size",`${(11*s).toFixed(2)}px`,"important");
     el.style.setProperty("font-weight","800","important");
   });
   document.querySelectorAll(".exec-table td .p271-placeholder").forEach(el=>{
     el.dataset.baseFontPx="10";
     el.dataset.performanceBaseFontPx="10";
     el.style.setProperty("font-size",`${(10*s).toFixed(2)}px`,"important");
     el.style.setProperty("font-weight","600","important");
   });
 }
 window.applyExecutionTextHierarchy=applyExecutionTextHierarchy;
 const prevSet=window.setFontScale;
 if(typeof prevSet==="function"){
   window.setFontScale=function(v,save=true){
     prevSet(v,save);
     requestAnimationFrame(applyExecutionTextHierarchy);
     setTimeout(applyExecutionTextHierarchy,60);
   };
 }
 const obs=new MutationObserver(()=>requestAnimationFrame(applyExecutionTextHierarchy));
 obs.observe(document.body,{childList:true,subtree:true});
 document.addEventListener("DOMContentLoaded",()=>setTimeout(applyExecutionTextHierarchy,120));
 setTimeout(applyExecutionTextHierarchy,180);
})();
</script>
'''
    if "</body>" not in text:
        raise RuntimeError("HTML body 종료 태그를 찾지 못했습니다.")
    text = text.replace("</body>", script + "\n</body>", 1)
    UI.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    apply_patch()
