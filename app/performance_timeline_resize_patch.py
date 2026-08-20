from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UI = ROOT / "ui" / "index.html"
MARKER = "v299-performance-timeline-resize"


def apply_patch() -> None:
    text = UI.read_text(encoding="utf-8")
    if MARKER in text:
        return

    css = r'''
<style>
/* v299-performance-timeline-resize */
#p271SalesGrid .p271-sales-grid{
  --p271-left-width:220px;
  grid-template-columns:var(--p271-left-width) minmax(0,1fr)!important;
  position:relative;
}
#p271SalesGrid .p271-sales-left{
  min-width:0;
  width:auto!important;
}
#p271SalesGrid .p271-timeline-area{
  min-width:0;
}
#p271SalesGrid .p299-timeline-resizer{
  position:absolute;
  top:0;
  bottom:0;
  left:calc(var(--p271-left-width) - 4px);
  width:8px;
  z-index:50;
  cursor:col-resize;
  background:transparent;
  user-select:none;
  touch-action:none;
}
#p271SalesGrid .p299-timeline-resizer::after{
  content:"";
  position:absolute;
  top:0;
  bottom:0;
  left:3px;
  width:2px;
  background:transparent;
  transition:background .12s ease, box-shadow .12s ease;
}
#p271SalesGrid .p299-timeline-resizer:hover::after,
#p271SalesGrid .p299-timeline-resizer.dragging::after{
  background:#6d91b5;
  box-shadow:0 0 0 1px rgba(109,145,181,.12);
}
body.p299-resizing-timeline,
body.p299-resizing-timeline *{
  cursor:col-resize!important;
  user-select:none!important;
}
</style>
'''

    script = r'''
<script>
// v299-performance-timeline-resize
(function(){
 const KEY="p271TimelineLeftWidth";
 const DEFAULT=220;
 const MIN=170;
 function savedWidth(){
   const n=Number(localStorage.getItem(KEY)||DEFAULT);
   return Number.isFinite(n)?n:DEFAULT;
 }
 function clampWidth(grid,px){
   const total=grid.getBoundingClientRect().width||900;
   const max=Math.max(MIN,Math.min(560,total*.48));
   return Math.round(Math.max(MIN,Math.min(max,px)));
 }
 function applyWidth(grid,px,save=false){
   if(!grid)return;
   const w=clampWidth(grid,px);
   grid.style.setProperty("--p271-left-width",w+"px");
   if(save)localStorage.setItem(KEY,String(w));
 }
 function installResizer(){
   const grid=document.querySelector("#p271SalesGrid .p271-sales-grid");
   if(!grid)return;
   applyWidth(grid,savedWidth(),false);
   if(grid.querySelector(".p299-timeline-resizer"))return;
   const handle=document.createElement("div");
   handle.className="p299-timeline-resizer";
   handle.title="드래그하여 마케팅 활동 영역 너비 조절";
   handle.setAttribute("aria-label","마케팅 활동 영역 너비 조절");
   grid.appendChild(handle);
   let dragging=false,startX=0,startWidth=0;
   const move=e=>{
     if(!dragging)return;
     const x=e.clientX??e.touches?.[0]?.clientX;
     if(!Number.isFinite(x))return;
     applyWidth(grid,startWidth+(x-startX),false);
   };
   const stop=()=>{
     if(!dragging)return;
     dragging=false;
     handle.classList.remove("dragging");
     document.body.classList.remove("p299-resizing-timeline");
     const current=parseFloat(getComputedStyle(grid).getPropertyValue("--p271-left-width"))||savedWidth();
     applyWidth(grid,current,true);
     window.removeEventListener("mousemove",move);
     window.removeEventListener("mouseup",stop);
     window.removeEventListener("touchmove",move);
     window.removeEventListener("touchend",stop);
   };
   const start=e=>{
     if(e.button!==undefined&&e.button!==0)return;
     e.preventDefault();
     dragging=true;
     const x=e.clientX??e.touches?.[0]?.clientX;
     startX=Number(x)||0;
     startWidth=grid.querySelector(".p271-sales-left")?.getBoundingClientRect().width||savedWidth();
     handle.classList.add("dragging");
     document.body.classList.add("p299-resizing-timeline");
     window.addEventListener("mousemove",move);
     window.addEventListener("mouseup",stop);
     window.addEventListener("touchmove",move,{passive:false});
     window.addEventListener("touchend",stop);
   };
   handle.addEventListener("mousedown",start);
   handle.addEventListener("touchstart",start,{passive:false});
 }
 window.installP271TimelineResizer=installResizer;
 const old=window.renderP271SalesGrid;
 if(typeof old==="function"){
   window.renderP271SalesGrid=function(){
     const r=old.apply(this,arguments);
     requestAnimationFrame(installResizer);
     return r;
   };
 }
 const root=document.getElementById("p271SalesGrid");
 if(root){
   const obs=new MutationObserver(()=>requestAnimationFrame(installResizer));
   obs.observe(root,{childList:true,subtree:true});
 }
 window.addEventListener("resize",()=>{
   const grid=document.querySelector("#p271SalesGrid .p271-sales-grid");
   if(grid)applyWidth(grid,savedWidth(),false);
 });
 document.addEventListener("DOMContentLoaded",()=>setTimeout(installResizer,100));
})();
</script>
'''

    if "</head>" not in text or "</body>" not in text:
        raise RuntimeError("HTML 기준점을 찾지 못했습니다.")
    text = text.replace("</head>", css + "\n</head>", 1)
    text = text.replace("</body>", script + "\n</body>", 1)
    UI.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    apply_patch()
