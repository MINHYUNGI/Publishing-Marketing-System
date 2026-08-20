from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UI = ROOT / "ui" / "index.html"
MARKER = "v311-execution-live-font-scale"


def apply_patch() -> None:
    text = UI.read_text(encoding="utf-8")
    if MARKER in text:
        return
    script = r'''
<script>
// v311-execution-live-font-scale
(function(){
 const rules=[
   [".exec-group-title b",13,800],
   [".exec-group-title span",10,400],
   [".exec-table th",10,700],
   [".exec-table td",11,400],
   [".exec-activity-name strong",11,800],
   [".exec-activity-channel",10,500],
   [".exec-table td .p271-placeholder",10,500],
   [".exec-badge",9,900]
 ];
 function scale(){
   if(typeof globalFontScaleValue!=="undefined"&&Number.isFinite(Number(globalFontScaleValue)))return Number(globalFontScaleValue)||1;
   return Math.max(.8,Math.min(2,Number(localStorage.getItem("fontScale")||100)/100));
 }
 function applyExecutionLiveScale(){
   const s=scale();
   rules.forEach(([sel,base,weight])=>document.querySelectorAll(sel).forEach(el=>{
     if(el.matches("button,[role=button]"))return;
     el.dataset.baseFontPx=String(base);
     el.dataset.performanceBaseFontPx=String(base);
     el.style.setProperty("font-size",`${(base*s).toFixed(2)}px`,"important");
     if(weight)el.style.setProperty("font-weight",String(weight),"important");
   }));
 }
 window.applyExecutionLiveScale=applyExecutionLiveScale;
 const previous=window.setFontScale;
 if(typeof previous==="function")window.setFontScale=function(v,save=true){previous(v,save);requestAnimationFrame(applyExecutionLiveScale);setTimeout(applyExecutionLiveScale,50)};
 const obs=new MutationObserver(()=>requestAnimationFrame(applyExecutionLiveScale));
 obs.observe(document.body,{childList:true,subtree:true});
 document.addEventListener("DOMContentLoaded",()=>setTimeout(applyExecutionLiveScale,120));
 setTimeout(applyExecutionLiveScale,200);
})();
</script>
'''
    if "</body>" not in text:
        raise RuntimeError("HTML body 종료 태그를 찾지 못했습니다.")
    text = text.replace("</body>", script + f'\n<script>/* {MARKER} */</script>\n</body>', 1)
    UI.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    apply_patch()
