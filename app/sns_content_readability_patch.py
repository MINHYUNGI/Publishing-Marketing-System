from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
UI=ROOT/"ui"/"index.html"
MARKER="v315-sns-content-readability"

def apply_patch():
    text=UI.read_text(encoding="utf-8")
    if MARKER in text:return
    css=r'''
<style>
/* v315-sns-content-readability */
.content-link-list{padding:12px 16px 16px!important;gap:10px!important}
.content-link-item{grid-template-columns:max-content minmax(150px,.8fr) minmax(240px,1.25fr) 38px repeat(4,minmax(72px,86px))!important;gap:12px!important;padding:13px 14px!important}
.content-link-platform{font-size:11px!important;padding:0!important;background:transparent!important;border-radius:0!important;color:#4f6479!important;font-weight:800!important;min-width:auto!important;max-width:none!important}
.content-link-channel small,.content-link-content small,.content-link-metric small{font-size:10px!important;line-height:1.2!important}
.content-link-channel b,.content-link-content b{font-size:12px!important;line-height:1.35!important}
.content-link-metric b{font-size:13px!important;line-height:1.25!important;margin-top:3px!important}
.content-link-open a{width:28px!important;height:28px!important;font-size:14px!important}
@media(max-width:1350px){
 .content-link-item{grid-template-columns:max-content minmax(130px,.7fr) minmax(200px,1.1fr) 36px repeat(2,minmax(68px,78px))!important}
}
</style>
'''
    script=r'''
<script>
// v315-sns-content-readability
(function(){
 const alias={
  'YouTube':'YouTube','Instagram':'Instagram','X':'X','네이버 블로그':'Naver Blog','네이버 카페':'Naver Cafe','TikTok':'TikTok','Threads':'Threads','Facebook':'Facebook'
 };
 function normalizePlatformLabels(){document.querySelectorAll('.content-link-platform').forEach(el=>{const t=(el.textContent||'').trim();el.textContent=alias[t]||t||'Web';});}
 const old=window.renderSNSContentLinks;
 if(typeof old==='function')window.renderSNSContentLinks=function(){old();normalizePlatformLabels();};
 document.addEventListener('DOMContentLoaded',()=>setTimeout(normalizePlatformLabels,250));
 setTimeout(normalizePlatformLabels,350);
})();
</script>
'''
    text=text.replace('</head>',css+'\n</head>',1)
    text=text.replace('</body>',script+f'\n<script>/* {MARKER} */</script>\n</body>',1)
    UI.write_text(text,encoding='utf-8')

if __name__=='__main__':apply_patch()
