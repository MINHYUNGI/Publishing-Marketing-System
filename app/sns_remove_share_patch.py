from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
UI=ROOT/"ui"/"index.html"
MARKER="v317-sns-remove-share"
def apply_patch():
 text=UI.read_text(encoding="utf-8")
 if MARKER in text:return
 # 공유 metric은 YouTube 공개 API에서 제공되지 않으므로 표시하지 않습니다.
 old='''<div class="content-link-metric optional-metric"><small>댓글</small><b>${metric(r.댓글수)}</b></div><div class="content-link-metric optional-metric"><small>공유</small><b>${metric(r.공유수)}</b></div>'''
 new='''<div class="content-link-metric optional-metric"><small>댓글</small><b>${metric(r.댓글수)}</b></div>'''
 if old in text:text=text.replace(old,new,1)
 css=r'''<style>/* v317-sns-remove-share */
.content-link-item{grid-template-columns:max-content minmax(150px,.8fr) minmax(240px,1.25fr) 38px repeat(3,minmax(76px,90px))!important}
@media(max-width:1350px){.content-link-item{grid-template-columns:max-content minmax(130px,.7fr) minmax(200px,1.1fr) 36px repeat(2,minmax(68px,80px))!important}}
</style>'''
 text=text.replace('</head>',css+f'\n<script>/* {MARKER} */</script>\n</head>',1)
 UI.write_text(text,encoding='utf-8')
if __name__=='__main__':apply_patch()
