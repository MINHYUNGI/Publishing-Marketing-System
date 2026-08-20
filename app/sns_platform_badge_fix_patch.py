from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
UI=ROOT/"ui"/"index.html"
MARKER="v320-sns-platform-badge-css-fix"
def apply_patch():
    text=UI.read_text(encoding="utf-8")
    if MARKER in text:return
    css=r'''
<style>
/* v320-sns-platform-badge-css-fix */
.content-link-platform{font-size:0!important;overflow:hidden!important;position:relative!important}
.content-link-platform::before{content:'W';font-size:11px!important;font-weight:900!important;line-height:1!important}
.content-link-platform[data-platform="YouTube"]::before{content:'Y'}
.content-link-platform[data-platform="X"]::before{content:'X'}
.content-link-platform[data-platform="Instagram"]::before{content:'I'}
.content-link-platform[data-platform="Naver Blog"]::before,.content-link-platform[data-platform="네이버 블로그"]::before{content:'B'}
.content-link-platform[data-platform="Naver Cafe"]::before,.content-link-platform[data-platform="네이버 카페"]::before{content:'C'}
.content-link-platform[data-platform="TikTok"]::before{content:'T'}
.content-link-platform[data-platform="Threads"]::before{content:'T'}
.content-link-platform[data-platform="Facebook"]::before{content:'F'}
</style>
'''
    text=text.replace('</head>',css+f'\n<script>/* {MARKER} */</script>\n</head>',1)
    UI.write_text(text,encoding='utf-8')
if __name__=='__main__':apply_patch()
