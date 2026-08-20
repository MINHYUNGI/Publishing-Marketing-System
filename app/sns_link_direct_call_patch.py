from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UI = ROOT / "ui" / "index.html"
MARKER = "v322-sns-link-direct-call"


def apply_patch():
    text = UI.read_text(encoding="utf-8")
    if MARKER in text:
        return

    script = r'''
<script>
// v322-sns-link-direct-call
(function(){
  window.openSNSLinkDirect = async function(el){
    const url = String((el && el.dataset && el.dataset.url) || '').trim();
    try{
      if(window.toast) toast('링크 여는 중...');
      if(!url){ if(window.toast) toast('링크 주소가 없습니다.'); return false; }
      if(!(window.pywebview && window.pywebview.api && typeof window.pywebview.api.open_external_url === 'function')){
        if(window.toast) toast('앱 연결이 아직 준비되지 않았습니다.');
        return false;
      }
      const res = await window.pywebview.api.open_external_url(url);
      if(res && res.ok){ if(window.toast) toast('브라우저에서 링크를 열었습니다.'); }
      else if(window.toast) toast((res && res.message) || '링크를 열지 못했습니다.');
    }catch(err){
      if(window.toast) toast('링크 열기 오류: ' + err);
    }
    return false;
  };

  function upgrade(root){
    (root || document).querySelectorAll('.content-link-open a, .content-link-open .sns-open-btn').forEach(el=>{
      if(el.tagName === 'BUTTON' && el.getAttribute('onclick')) return;
      const url = el.dataset.url || el.getAttribute('href') || '';
      const b = document.createElement('button');
      b.type = 'button';
      b.className = 'sns-open-btn';
      b.dataset.url = url;
      b.setAttribute('onclick','return openSNSLinkDirect(this)');
      b.title = '원문 열기';
      b.setAttribute('aria-label','원문 열기');
      b.textContent = '↗';
      el.replaceWith(b);
    });
  }

  document.addEventListener('pywebviewready',()=>upgrade(document));
  document.addEventListener('DOMContentLoaded',()=>upgrade(document));
  new MutationObserver(muts=>{
    for(const m of muts){
      for(const n of m.addedNodes){ if(n.nodeType===1) upgrade(n); }
    }
  }).observe(document.documentElement,{childList:true,subtree:true});
  setTimeout(()=>upgrade(document),250);
  setTimeout(()=>upgrade(document),1000);
})();
</script>
'''

    text = text.replace("</body>", script + f'\n<script>/* {MARKER} */</script>\n</body>', 1)
    UI.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    apply_patch()
