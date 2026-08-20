from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UI = ROOT / "ui" / "index.html"
MARKER = "v296-exec-edit-button-fixed-font"


def apply_patch() -> None:
    text = UI.read_text(encoding="utf-8")
    if MARKER in text:
        return
    css = r'''
<style>
/* v296-exec-edit-button-fixed-font */
.exec-edit-btn{
  font-size:11px !important;
}
</style>
'''
    if "</head>" not in text:
        raise RuntimeError("HTML head 기준점을 찾지 못했습니다.")
    text = text.replace("</head>", css + "\n</head>", 1)
    UI.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    apply_patch()
