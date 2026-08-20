from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UI = ROOT / "ui" / "index.html"
MARKER = "v293-performance-font-scale"


def apply_patch() -> None:
    text = UI.read_text(encoding="utf-8")
    if MARKER in text:
        return

    script = r'''
<script>
// v293-performance-font-scale
(function(){
 function perfScaleValue(){
   if(typeof globalFontScaleValue!=="undefined" && Number.isFinite(Number(globalFontScaleValue))) return Number(globalFontScaleValue);
   return Math.max(.8,Math.min(2,Number(localStorage.getItem("fontScale")||100)/100));
 }
 function applyPerformanceFontScale(){
   const page=document.getElementById("performancePage");
   if(!page)return;
   const scale=perfScaleValue();
   page.querySelectorAll("*").forEach(el=>{
     if(el.matches("script,style,svg,path,rect,line,polyline,g,defs"))return;
     let base=parseFloat(el.dataset.baseFontPx||el.dataset.performanceBaseFontPx||"");
     if(!Number.isFinite(base)||base<=0){
       const fs=parseFloat(getComputedStyle(el).fontSize);
       if(!Number.isFinite(fs)||fs<=0)return;
       // 공통 폰트 패치가 먼저 적용된 신규 노드라면 baseFontPx를 우선 사용하고,
       // 그렇지 않은 경우 현재 배율을 제거해 100% 기준값을 복원합니다.
       base=el.dataset.baseFontPx?parseFloat(el.dataset.baseFontPx):(fs/scale);
       if(!Number.isFinite(base)||base<=0)return;
       el.dataset.performanceBaseFontPx=String(base);
     }
     el.style.setProperty("font-size",`${(base*scale).toFixed(2)}px`,"important");
   });
 }
 window.applyPerformanceFontScale=applyPerformanceFontScale;

 // 공통 글자 크기 변경 뒤 성과 페이지에는 우선순위를 높여 한 번 더 적용합니다.
 const originalSet=window.setFontScale;
 if(typeof originalSet==="function"){
   window.setFontScale=function(v,save=true){
     originalSet(v,save);
     requestAnimationFrame(()=>applyPerformanceFontScale());
     setTimeout(applyPerformanceFontScale,40);
   };
 }

 // 성과 화면은 데이터를 선택할 때 innerHTML로 다시 생성되므로 생성 직후에도 재적용합니다.
 const perf=document.getElementById("performancePage");
 if(perf){
   const observer=new MutationObserver(()=>requestAnimationFrame(()=>applyPerformanceFontScale()));
   observer.observe(perf,{childList:true,subtree:true});
 }

 document.addEventListener("DOMContentLoaded",()=>setTimeout(applyPerformanceFontScale,80));
})();
</script>
'''
    if "</body>" not in text:
        raise RuntimeError("HTML body 종료 태그를 찾지 못했습니다.")
    text = text.replace("</body>", script + "\n</body>", 1)
    UI.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    apply_patch()
