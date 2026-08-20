from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UI = ROOT / "ui" / "index.html"
MARKER = "v333-sns-execution-link-editor"


def _replace_once(text: str, old: str, new: str) -> str:
    return text.replace(old, new, 1) if old in text else text


def apply_patch() -> None:
    text = UI.read_text(encoding="utf-8")
    if MARKER in text:
        return

    css = r'''
<style>
/* v333-sns-execution-link-editor */
.exec-link-stack{display:flex;flex-direction:column;gap:5px;min-width:270px}
.exec-link-row{display:grid;grid-template-columns:minmax(0,1fr) 28px;gap:5px;align-items:center}
.exec-link-row input{min-width:0}
.exec-link-add,.exec-link-remove{font-size:10px!important;line-height:1!important;height:28px;border-radius:6px;background:#fff;cursor:pointer;font-weight:800}
.exec-link-add{border:1px solid #9bb8d8;color:#356b9e;padding:0 8px;width:max-content}
.exec-link-remove{border:1px solid #ddb0b0;color:#a74747;width:28px;padding:0}
</style>
'''
    text = text.replace("</head>", css + f'\n<script>/* {MARKER} */</script>\n</head>', 1)

    # 실제 실행 편집 데이터에 기존 콘텐츠 링크를 포함합니다.
    text = _replace_once(
        text,
        ',sort_order:Number(a.실행정렬순서??a.정렬순서??999999),is_new:false};',
        ',links:(a.콘텐츠링크||[]).map(x=>x.URL||"").filter(Boolean),sort_order:Number(a.실행정렬순서??a.정렬순서??999999),is_new:false};',
    )
    text = _replace_once(
        text,
        'execution_type:"활동추가",sort_order:(execEditItems.length+1)*10,is_new:true}',
        'execution_type:"활동추가",links:[],sort_order:(execEditItems.length+1)*10,is_new:true}',
    )
    text = _replace_once(
        text,
        'o.execution_note=q("note");});',
        'o.execution_note=q("note");o.links=[...tr.querySelectorAll("[data-link]")].map(x=>x.value.trim()).filter(Boolean);});',
    )

    if "function renderExecLinks(" not in text and "function renderExecModalTable(){" in text:
        helper = r'''function renderExecLinks(o,i,cancel){
   if(!String(execEditCategory||"").includes("SNS"))return "";
   const links=Array.isArray(o.links)?o.links:[];
   const rows=(links.length?links:[""]).map((url,j)=>`<div class="exec-link-row"><input data-link="${j}" placeholder="https://..." value="${esc(url||"")}" ${cancel?'disabled':''}><button class="exec-link-remove" onclick="removeExecutionLink(${i},${j})" ${cancel?'disabled':''}>−</button></div>`).join("");
   return `<div class="exec-link-stack">${rows}<button class="exec-link-add" onclick="addExecutionLink(${i})" ${cancel?'disabled':''}>+ 링크</button></div>`;
 }
 window.addExecutionLink=function(i){pullExecInputs();const o=execEditItems[i];if(!o)return;o.links=Array.isArray(o.links)?o.links:[];o.links.push("");renderExecModalTable()};
 window.removeExecutionLink=function(i,j){pullExecInputs();const o=execEditItems[i];if(!o)return;o.links=Array.isArray(o.links)?o.links:[];o.links.splice(j,1);renderExecModalTable()};
 '''
        text = text.replace("function renderExecModalTable(){", helper + "function renderExecModalTable(){", 1)

    text = _replace_once(
        text,
        '<th style="min-width:180px">실행 내용/비고</th><th></th></tr>',
        '<th style="min-width:180px">실행 내용/비고</th>${String(execEditCategory||"").includes("SNS")?\'<th style="min-width:300px">콘텐츠 링크</th>\':\'\'}<th></th></tr>',
    )
    text = _replace_once(
        text,
        '<td><input data-f="note" value="${esc(o.execution_note)}" ${cancel?\'disabled\':\'\'}></td><td><button class="exec-minus',
        '<td><input data-f="note" value="${esc(o.execution_note)}" ${cancel?\'disabled\':\'\'}></td>${String(execEditCategory||"").includes("SNS")?`<td>${renderExecLinks(o,i,cancel)}</td>`:""}<td><button class="exec-minus',
    )

    UI.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    apply_patch()
