from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UI = ROOT / "ui" / "index.html"
MARKER = "v297-fixed-button-fonts"


def apply_patch() -> None:
    text = UI.read_text(encoding="utf-8")
    if MARKER in text:
        return

    script = r'''
<script>
// v297-fixed-button-fonts
(function(){
  const fixedSelector = 'button,input[type="button"],input[type="submit"],input[type="reset"],[role="button"]';

  function fixOne(el){
    if(!el || el.nodeType!==1 || !el.matches?.(fixedSelector)) return;
    let base = parseFloat(el.dataset.baseFontPx || '');
    if(!Number.isFinite(base) || base<=0){
      const current = parseFloat(getComputedStyle(el).fontSize);
      const scale = Number(window.globalFontScaleValue || 1) || 1;
      base = Number.isFinite(current) && current>0 ? current / scale : 12;
      el.dataset.baseFontPx = String(base);
    }
    el.style.setProperty('font-size', `${base.toFixed(2)}px`, 'important');
    el.dataset.fixedButtonFont = '1';
  }

  function fixAll(root=document){
    if(root?.matches?.(fixedSelector)) fixOne(root);
    root?.querySelectorAll?.(fixedSelector).forEach(fixOne);
  }

  function wrapGlobalFontFunction(name){
    const original = window[name];
    if(typeof original !== 'function' || original._fixedButtonWrapped) return;
    const wrapped = function(...args){
      const result = original.apply(this,args);
      fixAll(document);
      requestAnimationFrame(()=>fixAll(document));
      setTimeout(()=>fixAll(document),0);
      return result;
    };
    wrapped._fixedButtonWrapped = true;
    window[name] = wrapped;
  }

  function install(){
    wrapGlobalFontFunction('applyGlobalFontScale');
    wrapGlobalFontFunction('setFontScale');
    wrapGlobalFontFunction('applyPerformanceFontScale');
    fixAll(document);
  }

  const observer = new MutationObserver(mutations=>{
    mutations.forEach(m=>m.addedNodes.forEach(node=>{
      if(node.nodeType===1) fixAll(node);
    }));
  });

  if(document.readyState==='loading'){
    document.addEventListener('DOMContentLoaded',()=>{
      install();
      observer.observe(document.body,{childList:true,subtree:true});
    },{once:true});
  }else{
    install();
    observer.observe(document.body,{childList:true,subtree:true});
  }

  // 초기화가 늦게 끝나는 경우를 위해 한 번 더 후킹합니다.
  setTimeout(install,800);
})();
</script>
'''

    if "</body>" not in text:
        raise RuntimeError("HTML body 기준점을 찾지 못했습니다.")
    text = text.replace("</body>", script + "\n</body>", 1)
    UI.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    apply_patch()
