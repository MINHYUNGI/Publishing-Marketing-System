from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
UI=ROOT/"ui"/"index.html"
MARKER="v321-sns-link-capture-fix"

def apply_patch():
    text=UI.read_text(encoding="utf-8")
    if MARKER in text:return
    css=r'''
<style>
/* v321-sns-link-capture-fix */
.content-link-open{position:relative!important;z-index:20!important;pointer-events:auto!important}
.content-link-open a,.content-link-open button{pointer-events:auto!important;cursor:pointer!important}
</style>
'''
    script=r'''
<script>
// v321-sns-link-capture-fix
(function(){
 function show(msg){
   try{ if(typeof window.toast==='function'){ window.toast(msg); return; } }catch(e){}
   const el=document.getElementById('toast');
   if(el){el.textContent=msg;el.classList.add('show');setTimeout(()=>el.classList.remove('show'),1800);}
 }
 async function openUrl(url){
   if(!url){show('링크 주소가 없습니다.');return;}
   show('링크 여는 중...');
   try{
     if(window.pywebview && window.pywebview.api && typeof window.pywebview.api.open_external_url==='function'){
       const r=await window.pywebview.api.open_external_url(url);
       if(r && r.ok===false) show('링크 열기 실패: '+(r.message||'알 수 없는 오류'));
       else show('브라우저에서 링크를 열었습니다.');
       return;
     }
     show('앱 연결 준비 중입니다. 다시 눌러주세요.');
   }catch(e){
     show('링크 열기 오류: '+String(e));
   }
 }
 // 캡처 단계에서 가장 먼저 잡아 다른 핸들러의 stopPropagation 영향을 받지 않습니다.
 document.addEventListener('click',function(e){
   const target=e.target && e.target.closest ? e.target.closest('.content-link-open a, .content-link-open button') : null;
   if(!target)return;
   e.preventDefault();
   e.stopPropagation();
   e.stopImmediatePropagation();
   const url=target.getAttribute('data-url')||target.getAttribute('href')||target.dataset?.href||'';
   openUrl(url);
 },true);
 window.openSNSExternalLink=openUrl;
})();
</script>
'''
    text=text.replace('</head>',css+'\n</head>',1)
    text=text.replace('</body>',script+f'\n<script>/* {MARKER} */</script>\n</body>',1)
    UI.write_text(text,encoding='utf-8')

if __name__=='__main__':apply_patch()
