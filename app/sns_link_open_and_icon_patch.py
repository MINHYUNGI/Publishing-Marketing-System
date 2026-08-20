from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
UI=ROOT/"ui"/"index.html"
MARKER="v319-sns-link-open-platform-icons"

def apply_patch():
    text=UI.read_text(encoding="utf-8")
    if MARKER in text:return
    css=r'''
<style>
/* v319-sns-link-open-platform-icons */
.content-link-item{grid-template-columns:34px minmax(150px,.8fr) minmax(240px,1.25fr) 38px repeat(3,minmax(76px,90px))!important}
.content-link-platform{width:24px!important;height:24px!important;min-width:24px!important;border-radius:7px!important;display:flex!important;align-items:center!important;justify-content:center!important;padding:0!important;background:#eef3f8!important;color:#41566d!important;font-size:11px!important;font-weight:900!important;line-height:1!important}
.content-link-platform[data-platform="YouTube"]{background:#fff1f1!important;color:#b42318!important}
.content-link-platform[data-platform="X"]{background:#f1f2f4!important;color:#111827!important}
.content-link-platform[data-platform="Instagram"]{background:#f8eef7!important;color:#8b3a7b!important}
.content-link-platform[data-platform="Naver Blog"],.content-link-platform[data-platform="Naver Cafe"]{background:#edf8f1!important;color:#178a4b!important}
@media(max-width:1350px){.content-link-item{grid-template-columns:32px minmax(130px,.7fr) minmax(200px,1.1fr) 36px repeat(2,minmax(68px,80px))!important}}
</style>
'''
    script=r'''
<script>
// v319-sns-link-open-platform-icons
(function(){
 const map={YouTube:'Y',X:'X',Instagram:'I','Naver Blog':'B','Naver Cafe':'C',TikTok:'T',Threads:'T',Facebook:'F'};
 function decoratePlatforms(){
   document.querySelectorAll('.content-link-platform').forEach(el=>{
     const full=(el.getAttribute('data-platform')||el.textContent||'').trim();
     const normalized=({'네이버 블로그':'Naver Blog','네이버 카페':'Naver Cafe'})[full]||full;
     el.setAttribute('data-platform',normalized||'Web');
     el.setAttribute('title',normalized||'Web');
     el.textContent=map[normalized]||((normalized||'W').charAt(0).toUpperCase());
   });
 }
 async function openExternal(url){
   try{
     if(window.pywebview?.api?.open_external_url){
       const r=await window.pywebview.api.open_external_url(url);
       if(r && r.ok===false && window.toast)toast(r.message||'링크를 열지 못했습니다.');
       return false;
     }
     window.open(url,'_blank');
   }catch(e){if(window.toast)toast('링크 열기 오류: '+e)}
   return false;
 }
 window.openSNSExternalLink=openExternal;
 function wireLinks(){
   document.querySelectorAll('.content-link-open a').forEach(a=>{
     if(a.dataset.externalBound==='1')return;
     a.dataset.externalBound='1';
     const url=a.getAttribute('href')||'';
     a.removeAttribute('target');
     a.addEventListener('click',e=>{e.preventDefault();e.stopPropagation();openExternal(url)});
   });
   decoratePlatforms();
 }
 const old=window.renderSNSContentLinks;
 if(typeof old==='function')window.renderSNSContentLinks=function(){old();setTimeout(wireLinks,0)};
 document.addEventListener('DOMContentLoaded',()=>setTimeout(wireLinks,300));
 setTimeout(wireLinks,450);
})();
</script>
'''
    # 플랫폼 원문을 data-platform에 보존하여 한 글자 배지로 치환할 수 있게 합니다.
    old='<div class="content-link-platform">${esc(r.플랫폼||"웹")}</div>'
    new='<div class="content-link-platform" data-platform="${esc(r.플랫폼||"웹")}">${esc(r.플랫폼||"웹")}</div>'
    if old in text:text=text.replace(old,new,1)
    text=text.replace('</head>',css+'\n</head>',1)
    text=text.replace('</body>',script+f'\n<script>/* {MARKER} */</script>\n</body>',1)
    UI.write_text(text,encoding='utf-8')

if __name__=='__main__':apply_patch()
