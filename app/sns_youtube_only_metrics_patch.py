from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
UI=ROOT/"ui"/"index.html"
MARKER="v318-sns-youtube-only-metrics"

def apply_patch():
    text=UI.read_text(encoding="utf-8")
    if MARKER in text:return
    css=r'''
<style>
/* v318-sns-youtube-only-metrics */
.content-link-item.non-youtube{grid-template-columns:max-content minmax(150px,.85fr) minmax(260px,1.45fr) 38px!important}
.content-link-item.non-youtube .content-link-metric{display:none!important}
@media(max-width:1350px){.content-link-item.non-youtube{grid-template-columns:max-content minmax(130px,.8fr) minmax(220px,1.3fr) 36px!important}}
</style>
'''
    script=r'''
<script>
// v318-sns-youtube-only-metrics
(function(){
 function markRows(){
   document.querySelectorAll('.content-link-item').forEach(row=>{
     const platform=(row.querySelector('.content-link-platform')?.textContent||'').trim().toLowerCase();
     row.classList.toggle('non-youtube',platform!=='youtube');
   });
 }
 const old=window.renderSNSContentLinks;
 if(typeof old==='function')window.renderSNSContentLinks=function(){old();markRows();};
 document.addEventListener('DOMContentLoaded',()=>setTimeout(markRows,300));
 setTimeout(markRows,450);
})();
</script>
'''
    text=text.replace('</head>',css+'\n</head>',1)
    text=text.replace('</body>',script+f'\n<script>/* {MARKER} */</script>\n</body>',1)
    UI.write_text(text,encoding='utf-8')

if __name__=='__main__':apply_patch()
