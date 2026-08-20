from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
UI=ROOT/"ui"/"index.html"
MARKER="v331-sns-content-target-blank-tolerant"

def apply_patch():
    text=UI.read_text(encoding="utf-8")
    if MARKER in text:
        return

    css=r'''
<style>
/* v331-sns-content-target-blank-tolerant */
.content-link-content a{color:#2864bd;text-decoration:underline;text-underline-offset:2px;font-weight:800;cursor:pointer;pointer-events:auto!important}
.content-link-content a:hover{color:#1c4d96}
.content-link-open,.p271-native-link-btn{display:none!important}
.content-link-platform{width:24px!important;height:24px!important;min-width:24px!important;border-radius:7px!important;display:flex!important;align-items:center!important;justify-content:center!important;padding:0!important;font-size:0!important;font-weight:900!important;line-height:1!important;position:relative!important;overflow:hidden!important}
.content-link-platform::before{content:'W';font-size:11px!important}
.content-link-platform[data-platform="YouTube"]::before{content:'Y'}.content-link-platform[data-platform="X"]::before{content:'X'}.content-link-platform[data-platform="Instagram"]::before{content:'I'}
</style>
'''
    # 현재 UI는 이전 패치가 누적될 수 있으므로 특정 과거 문자열을 필수로 요구하지 않습니다.
    # 이미 콘텐츠 제목 링크가 있으면 target=_blank만 보강합니다.
    text=text.replace('<a href="${esc(r.URL)}" title="원문 열기">','<a href="${esc(r.URL)}" target="_blank" rel="noopener noreferrer" title="원문 열기">')
    text=text.replace('<a href="${esc(r.URL)}" target="_blank" rel="noopener noreferrer" title="${esc(r.URL)}">','<a href="${esc(r.URL)}" target="_blank" rel="noopener noreferrer" title="${esc(r.URL)}">')
    text=text.replace('</head>',css+f'\n<script>/* {MARKER} */</script>\n</head>',1)
    UI.write_text(text,encoding="utf-8")

if __name__=="__main__":
    apply_patch()
