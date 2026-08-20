from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
UI=ROOT/"ui"/"index.html"
MARKER="v322-sns-content-display-direct-link"

def apply_patch():
    text=UI.read_text(encoding="utf-8")
    if MARKER in text:
        return

    css=r'''
<style>
/* v322-sns-content-display-direct-link */
.content-link-item{grid-template-columns:34px minmax(150px,.8fr) minmax(240px,1.25fr) 40px repeat(3,minmax(76px,90px))!important}
.content-link-channel{min-width:0}.content-link-channel small,.content-link-content small{display:block;font-size:11px;color:#8a95a3;margin-bottom:2px}.content-link-channel b,.content-link-content b{display:block;font-size:13px;color:#344054;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.content-link-open{display:flex;align-items:center;justify-content:center}.content-link-open button{width:30px;height:30px;border:1px solid #cfd9e4;border-radius:7px;display:flex;align-items:center;justify-content:center;color:#2864bd;font-size:15px;background:#fff;cursor:pointer;padding:0;line-height:1}.content-link-open button:hover{background:#f2f7fd;border-color:#8fb2dc}
.content-link-platform{width:24px!important;height:24px!important;min-width:24px!important;border-radius:7px!important;display:flex!important;align-items:center!important;justify-content:center!important;padding:0!important;background:#eef3f8!important;color:#41566d!important;font-size:0!important;font-weight:900!important;line-height:1!important;position:relative!important;overflow:hidden!important}
.content-link-platform::before{content:'W';font-size:11px!important}
.content-link-platform[data-platform="YouTube"]{background:#fff1f1!important;color:#b42318!important}.content-link-platform[data-platform="YouTube"]::before{content:'Y'}
.content-link-platform[data-platform="X"]{background:#f1f2f4!important;color:#111827!important}.content-link-platform[data-platform="X"]::before{content:'X'}
.content-link-platform[data-platform="Instagram"]{background:#f8eef7!important;color:#8b3a7b!important}.content-link-platform[data-platform="Instagram"]::before{content:'I'}
.content-link-platform[data-platform="Naver Blog"],.content-link-platform[data-platform="네이버 블로그"]{background:#edf8f1!important;color:#178a4b!important}.content-link-platform[data-platform="Naver Blog"]::before,.content-link-platform[data-platform="네이버 블로그"]::before{content:'B'}
.content-link-platform[data-platform="Naver Cafe"],.content-link-platform[data-platform="네이버 카페"]{background:#edf8f1!important;color:#178a4b!important}.content-link-platform[data-platform="Naver Cafe"]::before,.content-link-platform[data-platform="네이버 카페"]::before{content:'C'}
.content-link-platform[data-platform="TikTok"]::before{content:'T'}
.content-link-platform[data-platform="Threads"]::before{content:'T'}
.content-link-platform[data-platform="Facebook"]::before{content:'F'}
@media(max-width:1350px){.content-link-item{grid-template-columns:32px minmax(130px,.7fr) minmax(200px,1.1fr) 38px repeat(2,minmax(68px,80px))!important}}
</style>
'''

    script=r'''
<script>
// v322-sns-content-display-direct-link
window.openContentLinkDirect = async function(btn){
  try{
    const url=(btn && btn.dataset ? btn.dataset.url : '') || '';
    if(!url){ if(window.toast) toast('링크 주소가 없습니다.'); return false; }
    if(window.toast) toast('링크 여는 중...');
    if(!(window.pywebview && window.pywebview.api && window.pywebview.api.open_external_url)){
      if(window.toast) toast('앱 연결 준비 중입니다. 잠시 후 다시 눌러주세요.');
      return false;
    }
    const res=await window.pywebview.api.open_external_url(url);
    if(res && res.ok){ if(window.toast) toast('브라우저에서 링크를 열었습니다.'); }
    else if(window.toast){ toast('링크 열기 실패: '+((res&&res.message)||'알 수 없는 오류')); }
  }catch(e){ if(window.toast) toast('링크 열기 오류: '+e); }
  return false;
};
</script>
'''

    old='''<div class="content-link-platform">${esc(r.플랫폼||"웹")}</div><div class="content-link-name"><b>${esc(r.콘텐츠명||"콘텐츠")}</b><span>${esc(r.채널명||"")}</span></div><div class="content-link-url"><a href="${esc(r.URL)}" target="_blank" rel="noopener noreferrer" title="${esc(r.URL)}">${esc(r.URL)}</a></div>'''
    new='''<div class="content-link-platform" data-platform="${esc(r.플랫폼||"웹")}" title="${esc(r.플랫폼||"웹")}">${esc(r.플랫폼||"웹")}</div><div class="content-link-channel"><small>채널명</small><b>${esc(r.채널명||"—")}</b></div><div class="content-link-content"><small>콘텐츠 이름</small><b>${esc(r.콘텐츠명||"콘텐츠")}</b></div><div class="content-link-open"><button type="button" data-url="${esc(r.URL||'')}" onclick="return window.openContentLinkDirect(this)" title="원문 열기" aria-label="원문 열기">↗</button></div>'''
    if old not in text:
        raise RuntimeError("SNS 콘텐츠 원본 렌더링 기준점을 찾지 못했습니다.")
    text=text.replace(old,new,1)
    text=text.replace('</head>',css+'\n</head>',1)
    text=text.replace('</body>',script+f'\n<script>/* {MARKER} */</script>\n</body>',1)
    UI.write_text(text,encoding="utf-8")

if __name__=="__main__":
    apply_patch()
