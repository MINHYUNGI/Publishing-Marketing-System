from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UI = ROOT / "ui" / "index.html"
MARKER = "v292-global-font-scale"


def apply_patch() -> None:
    text = UI.read_text(encoding="utf-8")
    if MARKER in text:
        return

    old = 'function setFontScale(v,save=true){document.documentElement.style.setProperty("--font-scale",Number(v)/100);if(save)localStorage.setItem("fontScale",v);}'
    new = r'''// v292-global-font-scale
let globalFontScaleValue=1;
let globalFontObserver=null;
function applyFontScaleToElement(el){
 if(!el||el.nodeType!==1)return;
 if(el.matches("script,style,svg,path,rect,line,polyline,g,defs"))return;
 if(!el.dataset.baseFontPx){
   const fs=parseFloat(getComputedStyle(el).fontSize);
   if(Number.isFinite(fs)&&fs>0)el.dataset.baseFontPx=String(fs);
 }
 const base=parseFloat(el.dataset.baseFontPx||"");
 if(Number.isFinite(base)&&base>0)el.style.fontSize=`${(base*globalFontScaleValue).toFixed(2)}px`;
 el.querySelectorAll?.("*").forEach(child=>{
   if(child.matches("script,style,svg,path,rect,line,polyline,g,defs"))return;
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
   if(el.matches("script,style,svg,path,rect,line,polyline,g,defs"))return;
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
        raise RuntimeError("기존 글자 크기 함수 기준점을 찾지 못했습니다.")
    text = text.replace(old, new, 1)
    UI.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    apply_patch()
