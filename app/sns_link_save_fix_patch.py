from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UI = ROOT / "ui" / "index.html"
MARKER = "v310-sns-link-save-fix"


def apply_patch() -> None:
    text = UI.read_text(encoding="utf-8")
    if MARKER in text:
        return

    old = 'o.execution_note=q("note");o.links=[...tr.querySelectorAll("[data-link]")].map(x=>x.value.trim()).filter(Boolean);});'
    new = 'o.execution_note=q("note");const linkRow=tr.nextElementSibling&&tr.nextElementSibling.classList.contains("exec-link-detail-row")?tr.nextElementSibling:null;o.links=[...(linkRow||tr).querySelectorAll("[data-link]")].map(x=>x.value.trim()).filter(Boolean);});'
    if old not in text:
        raise RuntimeError("SNS 링크 저장 기준점을 찾지 못했습니다.")
    text = text.replace(old, new, 1)

    css = r'''
<style>
/* v310-sns-link-save-fix */
.exec-badge.pending{display:none!important}
</style>
'''
    if "</head>" not in text:
        raise RuntimeError("HTML head 기준점을 찾지 못했습니다.")
    text = text.replace("</head>", css + "\n</head>", 1)
    text = text.replace("</body>", f'<script>/* {MARKER} */</script>\n</body>', 1)
    UI.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    apply_patch()
