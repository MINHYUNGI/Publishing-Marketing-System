from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
UI=ROOT/"ui"/"index.html"
MARKER="v324-sns-native-link-launcher"

def apply_patch():
    text=UI.read_text(encoding="utf-8")
    if MARKER in text:
        return

    old='''<section class="p271-panel"><div class="p271-panel-head"><div><h3>5. SNS·바이럴 콘텐츠 반응</h3><p>Supabase 「콘텐츠성과」의 콘텐츠별 반응 지표를 표시합니다.</p></div><span class="p271-panel-tag">${contents.length}건</span></div><div class="p271-digital-cards">${contentHtml}</div></section>'''
    new='''<section class="p271-panel"><div class="p271-panel-head"><div><h3>5. SNS·바이럴 콘텐츠 반응</h3><p>Supabase 「콘텐츠성과」의 콘텐츠별 반응 지표를 표시합니다.</p></div><div class="p271-content-head-actions"><button type="button" class="p271-native-link-btn" onclick="pywebview.api.open_content_links_native(currentPerformanceCode)">콘텐츠 링크 열기</button><span class="p271-panel-tag">${contents.length}건</span></div></div><div class="p271-digital-cards">${contentHtml}</div></section>'''
    if old not in text:
        raise RuntimeError("SNS 콘텐츠 섹션 헤더 기준점을 찾지 못했습니다.")
    text=text.replace(old,new,1)

    css=r'''
<style>
/* v324-sns-native-link-launcher */
.p271-content-head-actions{display:flex;align-items:center;gap:8px}
.p271-native-link-btn{height:30px;padding:0 11px;border:1px solid #b8c7d9;border-radius:7px;background:#fff;color:#344054;font-size:11px!important;font-weight:800!important;cursor:pointer;white-space:nowrap}
.p271-native-link-btn:hover{background:#f6f8fb;border-color:#8ea7c2}
/* 기존 행 단위 링크 버튼은 혼선을 막기 위해 숨깁니다. */
.content-link-open{display:none!important}
</style>
'''
    text=text.replace('</head>',css+f'\n<script>/* {MARKER} */</script>\n</head>',1)
    UI.write_text(text,encoding='utf-8')

if __name__=='__main__':
    apply_patch()
