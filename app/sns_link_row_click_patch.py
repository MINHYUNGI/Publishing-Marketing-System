from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
UI=ROOT/'ui'/'index.html'
MARKER='v326-sns-row-native-open'
def apply_patch():
    text=UI.read_text(encoding='utf-8')
    if MARKER in text:return
    css=r'''<style>/* v326-sns-row-native-open */
.content-link-item{cursor:pointer!important;position:relative!important}.content-link-item:hover{background:#f7faff!important;box-shadow:inset 0 0 0 1px #c7d8ed!important}.content-link-item::after{content:'원문 보기';position:absolute;right:10px;bottom:5px;font-size:9px;color:#7b8da3;opacity:0;transition:opacity .12s}.content-link-item:hover::after{opacity:1}
</style>'''
    script=r'''<script>// v326-sns-row-native-open
(function(){
 function wire(){
  document.querySelectorAll('.content-link-item').forEach(row=>{
   if(row.dataset.rowOpenBound==='1')return;
   const a=row.querySelector('.content-link-open a');
   const b=row.querySelector('.sns-open-btn');
   const url=(a?.getAttribute('href')||b?.dataset?.url||'').trim();
   if(!url)return;
   row.dataset.rowOpenBound='1';row.dataset.sourceUrl=url;
   row.title='클릭하여 원문 열기';
   row.onclick=function(){
    const u=this.dataset.sourceUrl||'';
    if(!u)return;
    // pywebview JS bridge가 동작하면 기본 브라우저, 아니면 현재 창에서 URL을 엽니다.
    if(window.pywebview?.api?.open_external_url){window.pywebview.api.open_external_url(u);}
    else{window.location.assign(u);}
   };
  });
 }
 const obs=new MutationObserver(()=>wire());obs.observe(document.documentElement,{childList:true,subtree:true});
 document.addEventListener('DOMContentLoaded',()=>setTimeout(wire,200));setTimeout(wire,500);
})();</script>'''
    text=text.replace('</head>',css+'\n</head>',1).replace('</body>',script+f'\n<script>/* {MARKER} */</script>\n</body>',1)
    UI.write_text(text,encoding='utf-8')
if __name__=='__main__':apply_patch()
