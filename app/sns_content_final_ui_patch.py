from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UI = ROOT / "ui" / "index.html"
MARKER = "v332-sns-content-final-ui"


def apply_patch() -> None:
    text = UI.read_text(encoding="utf-8")
    if MARKER in text:
        return

    css = r'''
<style>
/* v332-sns-content-final-ui */
.content-link-item.sns-final-row{
  display:grid!important;
  grid-template-columns:34px minmax(160px,.85fr) minmax(280px,1.45fr) repeat(3,minmax(78px,92px))!important;
  gap:12px!important;
  align-items:center!important;
}
.content-link-item.sns-final-row .content-link-url{display:none!important}
.content-link-item.sns-final-row .content-link-name{display:contents!important}
.content-link-item.sns-final-row .sns-final-channel,
.content-link-item.sns-final-row .sns-final-content{min-width:0!important}
.content-link-item.sns-final-row .sns-final-channel small,
.content-link-item.sns-final-row .sns-final-content small{display:block!important;font-size:11px!important;color:#8a95a3!important;margin-bottom:2px!important}
.content-link-item.sns-final-row .sns-final-channel b,
.content-link-item.sns-final-row .sns-final-content b{display:block!important;font-size:13px!important;color:#344054!important;white-space:nowrap!important;overflow:hidden!important;text-overflow:ellipsis!important}
.content-link-item.sns-final-row .sns-final-content b{color:#175cd3!important;text-decoration:underline!important;text-underline-offset:2px!important;cursor:pointer!important}
.content-link-item.sns-final-row .sns-final-content b:hover{color:#103f91!important}
.content-link-item.sns-final-row .content-link-platform{width:24px!important;height:24px!important;min-width:24px!important;border-radius:7px!important;font-size:0!important;display:flex!important;align-items:center!important;justify-content:center!important;overflow:hidden!important}
.content-link-item.sns-final-row .content-link-platform::before{content:'W';font-size:11px!important;font-weight:900!important}
.content-link-item.sns-final-row .content-link-platform[data-platform="YouTube"]::before{content:'Y'}
.content-link-item.sns-final-row .content-link-platform[data-platform="X"]::before{content:'X'}
.content-link-item.sns-final-row .content-link-platform[data-platform="Instagram"]::before{content:'I'}
@media(max-width:1350px){.content-link-item.sns-final-row{grid-template-columns:32px minmax(130px,.75fr) minmax(220px,1.25fr) repeat(2,minmax(68px,80px))!important}}
</style>
'''

    script = r'''
<script>
// v332-sns-content-final-ui
(function(){
  function platformOf(row){
    const p=row.querySelector('.content-link-platform');
    if(!p)return '';
    const txt=(p.dataset.platform||p.textContent||'').trim();
    if(txt)p.dataset.platform=txt;
    return txt;
  }
  function normalizeRow(row){
    if(!row || row.dataset.snsFinal==='1')return;
    const urlAnchor=row.querySelector('.content-link-url a[href^="http"], a[href^="https://"]');
    const url=(urlAnchor && (urlAnchor.getAttribute('href')||urlAnchor.href)||'').trim();
    if(!url)return;

    platformOf(row);
    const oldName=row.querySelector('.content-link-name');
    let titleEl=row.querySelector('.content-link-content b');
    let channelEl=row.querySelector('.content-link-channel b');

    if(oldName){
      titleEl=oldName.querySelector('b');
      channelEl=oldName.querySelector('span');
      const channel=document.createElement('div');
      channel.className='sns-final-channel';
      channel.innerHTML='<small>채널명</small><b></b>';
      channel.querySelector('b').textContent=(channelEl?.textContent||'—').trim()||'—';
      const content=document.createElement('div');
      content.className='sns-final-content';
      content.innerHTML='<small>콘텐츠 이름</small><b></b>';
      content.querySelector('b').textContent=(titleEl?.textContent||'콘텐츠').trim()||'콘텐츠';
      oldName.replaceWith(channel,content);
      titleEl=content.querySelector('b');
    }else{
      const channelWrap=row.querySelector('.content-link-channel');
      const contentWrap=row.querySelector('.content-link-content');
      if(channelWrap)channelWrap.classList.add('sns-final-channel');
      if(contentWrap)contentWrap.classList.add('sns-final-content');
      titleEl=contentWrap?.querySelector('b')||titleEl;
    }

    if(!titleEl)return;
    titleEl.dataset.sourceUrl=url;
    titleEl.title='원문 열기';
    titleEl.setAttribute('role','link');
    titleEl.setAttribute('tabindex','0');
    const open=async function(ev){
      ev?.preventDefault?.(); ev?.stopPropagation?.();
      const targetUrl=(this.dataset.sourceUrl||'').trim();
      if(!targetUrl)return;
      try{
        if(!(window.pywebview&&window.pywebview.api&&window.pywebview.api.open_external_url)){
          if(window.toast)toast('브라우저 연결을 준비 중입니다. 잠시 후 다시 눌러주세요.');
          return;
        }
        const res=await window.pywebview.api.open_external_url(targetUrl);
        if(!res?.ok && window.toast)toast(res?.message||'링크를 열 수 없습니다.');
      }catch(e){ if(window.toast)toast('링크 열기 오류: '+e); }
    };
    titleEl.addEventListener('click',open);
    titleEl.addEventListener('keydown',function(e){if(e.key==='Enter'||e.key===' '){open.call(this,e);}});
    row.classList.add('sns-final-row');
    row.dataset.snsFinal='1';
  }
  function normalize(){document.querySelectorAll('.content-link-item').forEach(normalizeRow);}
  window.addEventListener('pywebviewready',()=>setTimeout(normalize,50));
  document.addEventListener('DOMContentLoaded',()=>setTimeout(normalize,150));
  const observer=new MutationObserver(()=>normalize());
  observer.observe(document.documentElement,{childList:true,subtree:true});
  setTimeout(normalize,600);
})();
</script>
'''

    text = text.replace("</head>", css + "\n</head>", 1)
    text = text.replace("</body>", script + f"\n<script>/* {MARKER} */</script>\n</body>", 1)
    UI.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    apply_patch()
