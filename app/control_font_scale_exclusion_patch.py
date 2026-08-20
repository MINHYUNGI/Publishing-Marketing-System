from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UI = ROOT / "ui" / "index.html"
MARKER = "v299-control-font-scale-exclusion"


def apply_patch() -> None:
    text = UI.read_text(encoding="utf-8")
    if MARKER in text:
        return

    script = r'''
<script>
// v299-control-font-scale-exclusion
(function(){
 const CONTROL_SELECTOR = 'button,[role="button"],input[type="button"],input[type="submit"],input[type="reset"]';
 function currentScale(){
   if(typeof globalFontScaleValue!=="undefined" && Number.isFinite(Number(globalFontScaleValue))) return Number(globalFontScaleValue)||1;
   return Math.max(.8,Math.min(2,Number(localStorage.getItem("fontScale")||100)/100));
 }
 function normalizeControlFont(el){
   if(!el || el.nodeType!==1 || !el.matches(CONTROL_SELECTOR)) return;
   let base=parseFloat(el.dataset.controlBaseFontPx||el.dataset.baseFontPx||el.dataset.performanceBaseFontPx||"");
   if(!Number.isFinite(base)||base<=0){
     const fs=parseFloat(getComputedStyle(el).fontSize);
     if(!Number.isFinite(fs)||fs<=0)return;
     const scale=currentScale();
     base=fs/(scale||1);
   }
   if(!Number.isFinite(base)||base<=0)return;
   el.dataset.controlBaseFontPx=String(base);
   el.style.setProperty("font-size",`${base.toFixed(2)}px`,"important");
 }
 function normalizeAllControlFonts(root=document){
   if(root.nodeType===1 && root.matches?.(CONTROL_SELECTOR)) normalizeControlFont(root);
   root.querySelectorAll?.(CONTROL_SELECTOR).forEach(normalizeControlFont);
 }
 window.normalizeAllControlFonts=normalizeAllControlFonts;

 function scheduleNormalize(root=document){
   normalizeAllControlFonts(root);
   requestAnimationFrame(()=>{
     normalizeAllControlFonts(root);
     requestAnimationFrame(()=>normalizeAllControlFonts(root));
   });
   setTimeout(()=>normalizeAllControlFonts(root),60);
 }

 const previousSet=window.setFontScale;
 if(typeof previousSet==="function"){
   window.setFontScale=function(v,save=true){
     previousSet(v,save);
     scheduleNormalize(document);
   };
 }

 const observer=new MutationObserver(mutations=>{
   mutations.forEach(m=>m.addedNodes.forEach(node=>{
     if(node.nodeType===1)scheduleNormalize(node);
   }));
 });
 observer.observe(document.body,{childList:true,subtree:true});

 document.addEventListener("DOMContentLoaded",()=>setTimeout(()=>scheduleNormalize(document),100));
 setTimeout(()=>scheduleNormalize(document),150);
})();
</script>
'''
    if "</body>" not in text:
        raise RuntimeError("HTML body 종료 태그를 찾지 못했습니다.")
    text = text.replace("</body>", script + "\n</body>", 1)
    UI.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    apply_patch()
