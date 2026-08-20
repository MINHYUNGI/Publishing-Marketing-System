from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
UI=ROOT/"ui"/"index.html"
MARKER="v314-sns-content-display"

def apply_patch():
    text=UI.read_text(encoding="utf-8")
    if MARKER in text:return
    css=r'''
<style>
/* v314-sns-content-display */
.content-link-item{grid-template-columns:105px minmax(180px,.9fr) minmax(260px,1.35fr) 44px repeat(4,90px)!important}
.content-link-channel{min-width:0}.content-link-channel small,.content-link-content small{display:block;font-size:8px;color:#8a95a3;margin-bottom:2px}.content-link-channel b,.content-link-content b{display:block;font-size:10px;color:#344054;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.content-link-open{display:flex;align-items:center;justify-content:center}.content-link-open a{width:30px;height:30px;border:1px solid #cfd9e4;border-radius:7px;display:flex;align-items:center;justify-content:center;color:#2864bd;text-decoration:none;font-size:15px;background:#fff}.content-link-open a:hover{background:#f2f7fd;border-color:#8fb2dc}
@media(max-width:1350px){.content-link-item{grid-template-columns:90px minmax(150px,.8fr) minmax(210px,1.2fr) 40px repeat(2,75px)!important}}
</style>
'''
    # 최종 렌더 시 URL 문자열 대신 채널명/콘텐츠명/링크 아이콘을 보여줍니다.
    old='''<div class="content-link-platform">${esc(r.플랫폼||"웹")}</div><div class="content-link-name"><b>${esc(r.콘텐츠명||"콘텐츠")}</b><span>${esc(r.채널명||"")}</span></div><div class="content-link-url"><a href="${esc(r.URL)}" target="_blank" rel="noopener noreferrer" title="${esc(r.URL)}">${esc(r.URL)}</a></div>'''
    new='''<div class="content-link-platform">${esc(r.플랫폼||"웹")}</div><div class="content-link-channel"><small>채널명</small><b>${esc(r.채널명||"—")}</b></div><div class="content-link-content"><small>콘텐츠 이름</small><b>${esc(r.콘텐츠명||"콘텐츠")}</b></div><div class="content-link-open"><a href="${esc(r.URL)}" target="_blank" rel="noopener noreferrer" title="콘텐츠 열기" aria-label="콘텐츠 링크 열기">↗</a></div>'''
    if old not in text:raise RuntimeError("SNS 콘텐츠 표시 기준점을 찾지 못했습니다.")
    text=text.replace(old,new,1)
    text=text.replace('</head>',css+f'\n<script>/* {MARKER} */</script>\n</head>',1)
    UI.write_text(text,encoding="utf-8")

if __name__=="__main__":apply_patch()
