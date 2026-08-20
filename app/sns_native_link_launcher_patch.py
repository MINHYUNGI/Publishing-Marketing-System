from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
UI=ROOT/"ui"/"index.html"
MARKER="v325-sns-native-link-launcher-robust"

def apply_patch():
    text=UI.read_text(encoding="utf-8")
    if MARKER in text:
        return

    css=r'''
<style>
/* v325-sns-native-link-launcher-robust */
.p271-content-head-actions{display:flex!important;align-items:center!important;gap:8px!important}
.p271-native-link-btn{height:32px!important;padding:0 12px!important;border:1px solid #9fb2c8!important;border-radius:7px!important;background:#fff!important;color:#24415f!important;font-size:11px!important;font-weight:800!important;cursor:pointer!important;white-space:nowrap!important}
.p271-native-link-btn:hover{background:#f2f6fa!important;border-color:#6f8fad!important}
.content-link-open{display:none!important}
/* 플랫폼 표시는 원문 텍스트를 숨기고 한 글자만 안정적으로 표시 */
.content-link-platform{width:24px!important;min-width:24px!important;height:24px!important;padding:0!important;overflow:hidden!important;font-size:0!important;position:relative!important;border-radius:6px!important;display:flex!important;align-items:center!important;justify-content:center!important}
.content-link-platform::after{font-size:11px!important;font-weight:900!important;line-height:1!important;color:#344054!important}
.content-link-platform[data-platform="YouTube"]::after{content:"Y"!important;color:#b42318!important}
.content-link-platform[data-platform="X"]::after{content:"X"!important;color:#111827!important}
.content-link-platform[data-platform="Instagram"]::after{content:"I"!important;color:#8b3a7b!important}
.content-link-platform[data-platform="Naver Blog"]::after,.content-link-platform[data-platform="네이버 블로그"]::after{content:"B"!important;color:#178a4b!important}
.content-link-platform[data-platform="Naver Cafe"]::after,.content-link-platform[data-platform="네이버 카페"]::after{content:"C"!important;color:#178a4b!important}
</style>
'''

    script=r'''
<script>
// v325-sns-native-link-launcher-robust
(function(){
  function findSNSPanel(){
    const heads=[...document.querySelectorAll('.p271-panel-head')];
    return heads.find(h=>h.querySelector('h3')?.textContent?.includes('5. SNS·바이럴 콘텐츠 반응'))||null;
  }
  function installNativeLauncher(){
    const head=findSNSPanel();
    if(!head)return;
    let actions=head.querySelector('.p271-content-head-actions');
    const tag=head.querySelector('.p271-panel-tag');
    if(!actions){
      actions=document.createElement('div');
      actions.className='p271-content-head-actions';
      if(tag){ head.insertBefore(actions,tag); actions.appendChild(tag); }
      else head.appendChild(actions);
    }
    if(!actions.querySelector('.p271-native-link-btn')){
      const btn=document.createElement('button');
      btn.type='button';
      btn.className='p271-native-link-btn';
      btn.textContent='콘텐츠 링크 열기';
      btn.onclick=async function(){
        try{
          const code=String(window.currentPerformanceCode||currentPerformanceCode||'').trim();
          if(!code){ if(window.toast)toast('도서 제품코드를 확인할 수 없습니다.'); return; }
          if(!window.pywebview?.api?.open_content_links_native){ if(window.toast)toast('링크 열기 기능 연결을 확인할 수 없습니다.'); return; }
          await window.pywebview.api.open_content_links_native(code);
        }catch(e){ if(window.toast)toast('콘텐츠 링크 창 오류: '+e); }
      };
      actions.insertBefore(btn,actions.firstChild);
    }
  }
  const obs=new MutationObserver(()=>installNativeLauncher());
  document.addEventListener('DOMContentLoaded',()=>{installNativeLauncher();obs.observe(document.body,{childList:true,subtree:true});});
  setTimeout(()=>{installNativeLauncher();if(document.body)obs.observe(document.body,{childList:true,subtree:true});},500);
})();
</script>
'''
    text=text.replace('</head>',css+'\n</head>',1)
    text=text.replace('</body>',script+f'\n<script>/* {MARKER} */</script>\n</body>',1)
    UI.write_text(text,encoding='utf-8')

if __name__=='__main__':
    apply_patch()
