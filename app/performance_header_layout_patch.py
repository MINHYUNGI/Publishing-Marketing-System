from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UI = ROOT / "ui" / "index.html"
MARKER = "v311-performance-header-kpi-width"


def apply_patch() -> None:
    text = UI.read_text(encoding="utf-8")
    if MARKER in text:
        return

    css = r'''
<style>
/* v311-performance-header-kpi-width */
.p271-book-card{
  grid-template-columns:92px minmax(520px,700px) minmax(610px,1fr)!important;
  align-items:center!important;
}
.p271-book-info{min-width:0;max-width:700px;width:100%}
.p271-book-info h2{width:max-content;max-width:100%;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.p271-meta{max-width:100%}
.p271-summary{max-width:700px;overflow-wrap:anywhere}
.p271-kpis{min-width:610px;grid-template-columns:repeat(4,minmax(135px,1fr))!important}
.p271-kpi{min-width:0;padding-left:13px!important;padding-right:13px!important}
.p271-kpi strong{white-space:nowrap!important;word-break:keep-all!important;overflow:visible!important}
.p271-kpi span,.p271-kpi small{word-break:keep-all}
@media(max-width:1450px){
 .p271-book-card{grid-template-columns:82px minmax(430px,620px) minmax(570px,1fr)!important}
 .p271-book-info{max-width:620px}
 .p271-summary{max-width:620px}
 .p271-kpis{min-width:570px;grid-template-columns:repeat(4,minmax(125px,1fr))!important}
}
@media(max-width:1200px){
 .p271-book-card{grid-template-columns:80px minmax(0,1fr)!important}
 .p271-kpis{grid-column:1/-1;min-width:0!important;grid-template-columns:repeat(4,minmax(120px,1fr))!important}
 .p271-book-info,.p271-summary{max-width:none}
}
</style>
'''
    if "</head>" not in text:
        raise RuntimeError("HTML head 종료 태그를 찾지 못했습니다.")
    text = text.replace("</head>", css + f'\n<script>/* {MARKER} */</script>\n</head>', 1)
    UI.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    apply_patch()
