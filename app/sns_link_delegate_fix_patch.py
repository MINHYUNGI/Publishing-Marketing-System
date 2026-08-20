from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
UI=ROOT/"ui"/"index.html"
MARKER="v321-sns-link-delegation-fix"

def apply_patch():
    text=UI.read_text(encoding="utf-8")
    if MARKER in text:
        return

    css=r'''
<style>
/* v321-sns-link-delegation-fix */
.content-link-open{display:flex!important;align-items:center!important;justify-content:center!important}
.content-link-open .sns-open-btn{width:30px!important;height:30px!important;border:1px solid #cfd9e4!important;border-radius:7px!important;background:#fff!important;color:#2864bd!important;display:flex!important;align-items:center!important;justify-content:center!important;cursor:pointer!important;font-size:15px!important;line-height:1!important;padding:0!important}
.content-link-open .sns-open-btn:hover{background:#f2f7fd!important;border-color:#8fb2dc!important}
.content-link-platform{overflow:hidden!important;text-indent:-9999px!important;position:relative!important}
.content-link-platform::after{position:absolute!important;inset:0!important;display:flex!important;align-items:center!important;justify-content:center!important;text-indent:0!important;font-size:11px!important;font-weight:900!important;line-height:1!important}
.content-link-platform[data-platform="YouTube"]::after{content:"Y"}
.content-link-platform[data-platform="X"]::after{content:"X"}
.content-link-platform[data-platform="Instagram"]::after{content:"I"}
.content-link-platform[data-platform="Naver Blog"]::after{content:"B"}
.content-link-platform[data-platform="Naver Cafe"]::after{content:"C"}
.content-link-platform[data-platform="TikTok"]::after{content:"T"}
.content-link-platform[data-platform="Threads"]::after{content:"T"}
.content-link-platform[data-platform="Facebook"]::after{content:"F"}
.content-link-platform:not([data-platform])::after{content:"W"}
</style>
'''

    script=r'''
<script>
// v321-sns-link-delegation-fix
(function(){
  function upgradeLinkButtons(root){
    (root||document).querySelectorAll('.content-link-open a').forEach(a=>{
      const url=a.getAttribute('href')||'';
      const b=document.createElement('button');
      b.type='button';
      b.className='sns-open-btn';
      b.dataset.url=url;
      b.title='원문 열기';
      b.setAttribute('aria-label','원문 열기');
      b.textContent='↗';
      a.replaceWith(b);
    });
  }

  document.addEventListener('click',async function(e){
    const btn=e.target.closest('.sns-open-btn');
    if(!btn)return;
    e.preventDefault();
    e.stopPropagation();
    const url=(btn.dataset.url||'').trim();
    if(!url)return;
    try{
      if(window.pywebview && window.pywebview.api && window.pywebview.api.open_external_url){
        const res=await window.pywebview.api.open_external_url(url);
        if(res && res.ok===false && window.toast)toast(res.message||'링크를 열지 못했습니다.');
      }else{
        window.location.href=url;
      }
    }catch(err){
      if(window.toast)toast('링크 열기 오류: '+err);
    }
  },true);

  const observer=new MutationObserver(muts=>{
    for(const m of muts){
      for(const n of m.addedNodes){
        if(n.nodeType===1)upgradeLinkButtons(n);
      }
    }
  });
  observer.observe(document.documentElement,{childList:true,subtree:true});
  document.addEventListener('DOMContentLoaded',()=>upgradeLinkButtons(document));
  setTimeout(()=>upgradeLinkButtons(document),300);
})();
</script>
'''

    text=text.replace('</head>',css+'\n</head>',1)
    text=text.replace('</body>',script+f'\n<script>/* {MARKER} */</script>\n</body>',1)
    UI.write_text(text,encoding='utf-8')

if __name__=='__main__':
    apply_patch()
