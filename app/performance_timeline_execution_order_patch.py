from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UI = ROOT / "ui" / "index.html"
MARKER = "v304-performance-timeline-execution-order"


def apply_patch() -> None:
    text = UI.read_text(encoding="utf-8")
    if MARKER in text:
        return

    old = '''function sortWithinGroup(arr){
   return [...arr].sort((a,b)=>{
     const ad=String(a?.실제시작일||a?.시작일||"9999-12-31");
     const bd=String(b?.실제시작일||b?.시작일||"9999-12-31");
     return ad.localeCompare(bd)||String(a?.활동명||"").localeCompare(String(b?.활동명||""),"ko");
   });
 }'''
    new = '''function sortWithinGroup(arr){
   return [...arr].sort((a,b)=>{
     const ao=Number(a?.실행정렬순서??a?.정렬순서??999999);
     const bo=Number(b?.실행정렬순서??b?.정렬순서??999999);
     if(ao!==bo)return ao-bo;
     const ad=String(a?.실제시작일||a?.시작일||"9999-12-31");
     const bd=String(b?.실제시작일||b?.시작일||"9999-12-31");
     return ad.localeCompare(bd)||String(a?.활동명||"").localeCompare(String(b?.활동명||""),"ko");
   });
 }'''
    if old not in text:
        raise RuntimeError("타임라인 그룹 정렬 함수 기준점을 찾지 못했습니다.")
    text = text.replace(old, new, 1)

    if "</body>" not in text:
        raise RuntimeError("HTML body 종료 태그를 찾지 못했습니다.")
    text = text.replace("</body>", f'<script>/* {MARKER} */</script>\n</body>', 1)
    UI.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    apply_patch()
