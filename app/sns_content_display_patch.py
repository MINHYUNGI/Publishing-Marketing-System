from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
UI=ROOT/"ui"/"index.html"
MARKER="v327-sns-content-title-hyperlink"

def apply_patch():
    text=UI.read_text(encoding="utf-8")
    if MARKER in text:
        return

    css=r'''
<style>
/* v327-sns-content-title-hyperlink */
.content-link-item{grid-template-columns:34px minmax(150px,.8fr) minmax(260px,1.4fr) repeat(3,minmax(76px,90px))!important}
.content-link-channel{min-width:0}.content-link-channel small,.content-link-content small{display:block;font-size:11px;color:#8a95a3;margin-bottom:2px}.content-link-channel b,.content-link-content b{display:block;font-size:13px;color:#344054;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.content-link-content a{color:#2864bd;text-decoration:underline;text-underline-offset:2px;font-weight:800;cursor:pointer}.content-link-content a:hover{color:#1c4d96}
.content-link-open{display:none!important}
.content-link-platform{width:24px!important;height:24px!important;min-width:24px!important;border-radius:7px!important;display:flex!important;align-items:center!important;justify-content:center!important;padding:0!important;background:#eef3f8!important;color:#41566d!important;font-size:0!important;font-weight:900!important;line-height:1!important;position:relative!important;overflow:hidden!important}
.content-link-platform::before{content:'W';font-size:11px!important}
.content-link-platform[data-platform="YouTube"]{background:#fff1f1!important;color:#b42318!important}.content-link-platform[data-platform="YouTube"]::before{content:'Y'}
.content-link-platform[data-platform="X"]{background:#f1f2f4!important;color:#111827!important}.content-link-platform[data-platform="X"]::before{content:'X'}
.content-link-platform[data-platform="Instagram"]{background:#f8eef7!important;color:#8b3a7b!important}.content-link-platform[data-platform="Instagram"]::before{content:'I'}
.content-link-platform[data-platform="Naver Blog"],.content-link-platform[data-platform="네이버 블로그"]{background:#edf8f1!important;color:#178a4b!important}.content-link-platform[data-platform="Naver Blog"]::before,.content-link-platform[data-platform="네이버 블로그"]::before{content:'B'}
.content-link-platform[data-platform="Naver Cafe"],.content-link-platform[data-platform="네이버 카페"]{background:#edf8f1!important;color:#178a4b!important}.content-link-platform[data-platform="Naver Cafe"]::before,.content-link-platform[data-platform="네이버 카페"]::before{content:'C'}
@media(max-width:1350px){.content-link-item{grid-template-columns:32px minmax(130px,.75fr) minmax(220px,1.3fr) repeat(2,minmax(68px,80px))!important}}
</style>
'''

    # 이전 렌더 형태(버튼 방식)를 일반 하이퍼링크로 단순화합니다.
    old='''<div class="content-link-platform" data-platform="${esc(r.플랫폼||"웹")}" title="${esc(r.플랫폼||"웹")}">${esc(r.플랫폼||"웹")}</div><div class="content-link-channel"><small>채널명</small><b>${esc(r.채널명||"—")}</b></div><div class="content-link-content"><small>콘텐츠 이름</small><b>${esc(r.콘텐츠명||"콘텐츠")}</b></div><div class="content-link-open"><button type="button" data-url="${esc(r.URL||'')}" onclick="return window.openContentLinkDirect(this)" title="원문 열기" aria-label="원문 열기">↗</button></div>'''
    new='''<div class="content-link-platform" data-platform="${esc(r.플랫폼||"웹")}" title="${esc(r.플랫폼||"웹")}">${esc(r.플랫폼||"웹")}</div><div class="content-link-channel"><small>채널명</small><b>${esc(r.채널명||"—")}</b></div><div class="content-link-content"><small>콘텐츠 이름</small><b>${r.URL?`<a href="${esc(r.URL)}" title="원문 열기">${esc(r.콘텐츠명||"콘텐츠")}</a>`:esc(r.콘텐츠명||"콘텐츠")}</b></div>'''
    if old not in text:
        # 최초 형태에서도 직접 바꿀 수 있도록 보조 기준점을 둡니다.
        old2='''<div class="content-link-platform">${esc(r.플랫폼||"웹")}</div><div class="content-link-name"><b>${esc(r.콘텐츠명||"콘텐츠")}</b><span>${esc(r.채널명||"")}</span></div><div class="content-link-url"><a href="${esc(r.URL)}" target="_blank" rel="noopener noreferrer" title="${esc(r.URL)}">${esc(r.URL)}</a></div>'''
        new2='''<div class="content-link-platform" data-platform="${esc(r.플랫폼||"웹")}" title="${esc(r.플랫폼||"웹")}">${esc(r.플랫폼||"웹")}</div><div class="content-link-channel"><small>채널명</small><b>${esc(r.채널명||"—")}</b></div><div class="content-link-content"><small>콘텐츠 이름</small><b>${r.URL?`<a href="${esc(r.URL)}" title="원문 열기">${esc(r.콘텐츠명||"콘텐츠")}</a>`:esc(r.콘텐츠명||"콘텐츠")}</b></div>'''
        if old2 not in text:
            raise RuntimeError("SNS 콘텐츠 렌더링 기준점을 찾지 못했습니다.")
        text=text.replace(old2,new2,1)
    else:
        text=text.replace(old,new,1)

    # 이전 별도 링크 열기 버튼이 이미 HTML에 주입되어 있다면 숨깁니다.
    css += r'''<style>.p271-native-link-btn{display:none!important}</style>'''
    text=text.replace('</head>',css+f'\n<script>/* {MARKER} */</script>\n</head>',1)
    UI.write_text(text,encoding="utf-8")

if __name__=="__main__":
    apply_patch()
