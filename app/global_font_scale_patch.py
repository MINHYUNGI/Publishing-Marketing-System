from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UI = ROOT / "ui" / "index.html"
MARKER = "v310-global-font-scale-control-safe"


def apply_patch() -> None:
    text = UI.read_text(encoding="utf-8")
    if MARKER in text:
        return

    old = 'function setFontScale(v,save=true){document.documentElement.style.setProperty("--font-scale",Number(v)/100);if(save)localStorage.setItem("fontScale",v);}'
    new = r'''// v310-global-font-scale-control-safe
let globalFontScaleValue=1;
let globalFontObserver=null;
const GLOBAL_FONT_SKIP='script,style,svg,path,rect,line,polyline,g,defs,button,[role="button"],input[type="button"],input[type="submit"],input[type="reset"]';
function shouldSkipFontScale(el){
 if(!el||el.nodeType!==1)return true;
 if(el.matches(GLOBAL_FONT_SKIP))return true;
 if(el.closest('button,[role="button"]'))return true;
 return false;
}
function applyFontScaleToElement(el){
 if(!el||el.nodeType!==1)return;
 if(!shouldSkipFontScale(el)){
   if(!el.dataset.baseFontPx){
     const fs=parseFloat(getComputedStyle(el).fontSize);
     if(Number.isFinite(fs)&&fs>0)el.dataset.baseFontPx=String(fs);
   }
   const base=parseFloat(el.dataset.baseFontPx||"");
   if(Number.isFinite(base)&&base>0)el.style.fontSize=`${(base*globalFontScaleValue).toFixed(2)}px`;
 }
 el.querySelectorAll?.("*").forEach(child=>{
   if(shouldSkipFontScale(child))return;
   if(!child.dataset.baseFontPx){
     const fs=parseFloat(getComputedStyle(child).fontSize);
     if(Number.isFinite(fs)&&fs>0)child.dataset.baseFontPx=String(fs);
   }
   const b=parseFloat(child.dataset.baseFontPx||"");
   if(Number.isFinite(b)&&b>0)child.style.fontSize=`${(b*globalFontScaleValue).toFixed(2)}px`;
 });
}
function applyGlobalFontScale(){
 document.documentElement.style.setProperty("--font-scale",1);
 document.querySelectorAll("body *").forEach(el=>{
   if(shouldSkipFontScale(el))return;
   if(!el.dataset.baseFontPx){
     const fs=parseFloat(getComputedStyle(el).fontSize);
     if(Number.isFinite(fs)&&fs>0)el.dataset.baseFontPx=String(fs);
   }
   const base=parseFloat(el.dataset.baseFontPx||"");
   if(Number.isFinite(base)&&base>0)el.style.fontSize=`${(base*globalFontScaleValue).toFixed(2)}px`;
 });
}
function setFontScale(v,save=true){
 globalFontScaleValue=Math.max(.8,Math.min(2,Number(v||100)/100));
 document.documentElement.style.setProperty("--font-scale",1);
 applyGlobalFontScale();
 if(!globalFontObserver){
   globalFontObserver=new MutationObserver(mutations=>{
     mutations.forEach(m=>m.addedNodes.forEach(node=>{if(node.nodeType===1)applyFontScaleToElement(node)}));
   });
   globalFontObserver.observe(document.body,{childList:true,subtree:true});
 }
 if(save)localStorage.setItem("fontScale",v);
}'''
    if old not in text:
        # 구버전 패치가 이미 포함된 HTML에는 재주입하지 않고 다음 reset 시 정상 적용됩니다.
        if "v292-global-font-scale" in text or "v310-global-font-scale-control-safe" in text:
            return
        raise RuntimeError("기존 글자 크기 함수 기준점을 찾지 못했습니다.")
    text = text.replace(old, new, 1)
    UI.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    apply_patch()
