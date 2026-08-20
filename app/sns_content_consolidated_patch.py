from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent.parent
UI = ROOT / "ui" / "index.html"
MARKER = "v334-sns-content-consolidated"


def apply_patch() -> None:
    text = UI.read_text(encoding="utf-8")
    if MARKER in text:
        return

    css = r'''
<style>
/* v334-sns-content-consolidated */
.sns-content-list{padding:15px 20px 20px;display:flex;flex-direction:column;gap:10px}
.sns-content-row{display:grid;grid-template-columns:32px minmax(145px,.78fr) minmax(260px,1.45fr) auto;gap:12px;align-items:center;padding:12px 13px;border:1px solid #e1e7ee;border-radius:9px;background:#fff;min-width:0}
.sns-content-row.link-only{grid-template-columns:32px minmax(145px,.78fr) minmax(260px,1.45fr)}
.sns-platform-badge{width:26px;height:26px;border-radius:7px;display:flex;align-items:center;justify-content:center;font-size:calc(12px * var(--font-scale));font-weight:900;line-height:1;background:#eef3f8;color:#41566d}
.sns-platform-badge.sns-youtube{background:#fff0f0;color:#b42318}.sns-platform-badge.sns-x{background:#f1f2f4;color:#111827}.sns-platform-badge.sns-instagram{background:#f7edf6;color:#8b3a7b}.sns-platform-badge.sns-blog,.sns-platform-badge.sns-cafe{background:#edf8f1;color:#178a4b}
.sns-content-channel,.sns-content-main{min-width:0}.sns-content-channel small,.sns-content-main small,.sns-content-metric small{display:block;font-size:calc(11px * var(--font-scale));color:#8793a1;margin-bottom:3px;line-height:1.2}.sns-content-channel b{display:block;font-size:calc(14px * var(--font-scale));color:#344054;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.sns-content-channel span{display:block;margin-top:3px;font-size:calc(10px * var(--font-scale));color:#98a2b3}
.sns-content-main a,.sns-content-main b{display:block;max-width:100%;font-size:calc(14px * var(--font-scale));font-weight:800;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.sns-content-main a{color:#175cd3;text-decoration:underline;text-underline-offset:2px;cursor:pointer}.sns-content-main a:hover{color:#103f91}
.sns-content-metrics{display:grid;grid-template-columns:repeat(3,minmax(72px,88px));gap:8px}.sns-content-metric{text-align:right;padding-left:8px;border-left:1px solid #edf0f3}.sns-content-metric b{display:block;font-size:calc(15px * var(--font-scale));color:#344054;font-variant-numeric:tabular-nums}
@media(max-width:1350px){.sns-content-row{grid-template-columns:30px minmax(125px,.72fr) minmax(210px,1.25fr) auto;gap:9px}.sns-content-row.link-only{grid-template-columns:30px minmax(125px,.72fr) minmax(210px,1.25fr)}.sns-content-metrics{grid-template-columns:repeat(3,minmax(60px,72px));gap:5px}}
@media(max-width:1050px){.sns-content-row,.sns-content-row.link-only{grid-template-columns:30px minmax(120px,.8fr) minmax(200px,1.3fr)}.sns-content-metrics{grid-column:2/-1;display:flex;justify-content:flex-start}.sns-content-metric{text-align:left;min-width:82px}}
</style>
'''

    replacement = r'''
 const snsPlatformMeta=value=>{
   const raw=String(value||"웹").trim(),lower=raw.toLowerCase();
   if(lower.includes("youtube")||raw.includes("유튜브"))return {key:"youtube",letter:"Y",label:"YouTube",youtube:true};
   if(raw==="X"||lower.includes("twitter")||raw.includes("트위터"))return {key:"x",letter:"X",label:"X",youtube:false};
   if(lower.includes("instagram")||raw.includes("인스타"))return {key:"instagram",letter:"I",label:"Instagram",youtube:false};
   if(lower.includes("blog")||raw.includes("블로그"))return {key:"blog",letter:"B",label:"Naver Blog",youtube:false};
   if(lower.includes("cafe")||raw.includes("카페"))return {key:"cafe",letter:"C",label:"Naver Cafe",youtube:false};
   if(lower.includes("tiktok")||raw.includes("틱톡"))return {key:"tiktok",letter:"T",label:"TikTok",youtube:false};
   if(lower.includes("facebook")||raw.includes("페이스북"))return {key:"facebook",letter:"F",label:"Facebook",youtube:false};
   if(lower.includes("threads")||raw.includes("스레드"))return {key:"threads",letter:"T",label:"Threads",youtube:false};
   return {key:"web",letter:"W",label:raw||"웹",youtube:false};
 };
 const snsMetric=v=>v===null||v===undefined||v===""?"—":Number(v).toLocaleString("ko-KR");
 const contentRows=[...contents].filter(c=>String(c.URL||"").trim()).sort((a,b)=>Number(a.링크순서??999999)-Number(b.링크순서??999999));
 const contentHtml=contentRows.length?contentRows.map(c=>{
   const meta=snsPlatformMeta(c.플랫폼),title=c.콘텐츠명||"콘텐츠",channel=c.채널명||"—";
   const titleHtml=`<a href="${esc(c.URL)}" target="_blank" rel="noopener noreferrer" title="원문 열기">${esc(title)}</a>`;
   const metrics=meta.youtube?`<div class="sns-content-metrics"><div class="sns-content-metric"><small>조회</small><b>${snsMetric(c.조회수)}</b></div><div class="sns-content-metric"><small>좋아요</small><b>${snsMetric(c.좋아요수)}</b></div><div class="sns-content-metric"><small>댓글</small><b>${snsMetric(c.댓글수)}</b></div></div>`:"";
   return `<div class="sns-content-row ${meta.youtube?"youtube":"link-only"}"><div class="sns-platform-badge sns-${meta.key}" title="${esc(meta.label)}">${meta.letter}</div><div class="sns-content-channel"><small>채널명</small><b>${esc(channel)}</b>${c.게시일?`<span>${esc(c.게시일)}</span>`:""}</div><div class="sns-content-main"><small>콘텐츠 이름</small>${titleHtml}</div>${metrics}</div>`;
 }).join(""):`<div class="perf-empty">등록된 SNS·바이럴 콘텐츠 링크가 없습니다.</div>`;

 const ages='''

    pattern = re.compile(
        r'\n const contentHtml=contents\.length\?contents\.slice\(0,6\)\.map\(\(c,i\)=>`[\s\S]*?</div>`\)\.join\(""\):`<div class="perf-empty">등록된 SNS·바이럴 콘텐츠 성과가 없습니다\.</div>`;\n\n const ages=',
        re.MULTILINE,
    )
    text, count = pattern.subn(replacement, text, count=1)
    if count != 1:
        raise RuntimeError("SNS 콘텐츠 원본 렌더링 블록을 찾지 못했습니다.")

    old_section = '<span class="p271-panel-tag">${contents.length}건</span></div><div class="p271-digital-cards">${contentHtml}</div></section>'
    new_section = '<span class="p271-panel-tag">${contentRows.length}건</span></div><div class="sns-content-list">${contentHtml}</div></section>'
    if old_section not in text:
        raise RuntimeError("SNS 콘텐츠 섹션 컨테이너를 찾지 못했습니다.")
    text = text.replace(old_section, new_section, 1)

    text = text.replace("</head>", css + f'\n<script>/* {MARKER} */</script>\n</head>', 1)
    UI.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    apply_patch()
