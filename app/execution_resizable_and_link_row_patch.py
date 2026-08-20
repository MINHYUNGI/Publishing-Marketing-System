from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UI = ROOT / "ui" / "index.html"
MARKER = "v309-execution-resizer-link-row"


def apply_patch() -> None:
    text = UI.read_text(encoding="utf-8")
    if MARKER in text:
        return

    css = r'''
<style>
/* v309-execution-resizer-link-row */
.exec-activity-inline{grid-template-columns:minmax(90px,var(--exec-name-width,66%)) minmax(90px,1fr)!important;position:relative}
.exec-activity-resizer{position:absolute;top:-7px;bottom:-7px;left:var(--exec-name-width,66%);width:9px;transform:translateX(-4px);cursor:col-resize;z-index:3}
.exec-activity-resizer::after{content:"";position:absolute;left:4px;top:7px;bottom:7px;width:1px;background:#dfe5ec}
.exec-activity-resizer:hover::after,.exec-activity-resizer.dragging::after{width:2px;background:#7c9fc5}
.exec-activity-channel{border-left:0!important;padding-left:12px!important}
.exec-link-detail-row td{padding:0 7px 10px 49px!important;border-bottom:1px solid #edf0f3;background:#fbfcfd}
.exec-link-detail{display:grid;grid-template-columns:92px minmax(0,1fr);gap:10px;align-items:start;padding-top:7px}
.exec-link-detail-label{font-size:10px;font-weight:800;color:#667485;padding-top:8px}
.exec-link-detail .exec-link-stack{min-width:0;width:100%}
.exec-link-detail .exec-link-row{grid-template-columns:minmax(0,1fr) 28px}
.exec-link-detail .exec-link-row input{width:100%}
</style>
'''

    script = r'''
<script>
// v309-execution-resizer-link-row
(function(){
 const KEY='executionActivityNameWidthPct';
 let pct=Math.max(28,Math.min(82,Number(localStorage.getItem(KEY)||66)));
 function applyPct(){
   document.querySelectorAll('.exec-activity-inline').forEach(w=>w.style.setProperty('--exec-name-width',pct+'%'));
 }
 function installResizers(){
   document.querySelectorAll('.exec-activity-inline').forEach(w=>{
     w.style.setProperty('--exec-name-width',pct+'%');
     if(w.querySelector('.exec-activity-resizer'))return;
     const r=document.createElement('span');r.className='exec-activity-resizer';r.title='드래그해서 활동명/채널 영역 너비 조절';
     r.addEventListener('mousedown',ev=>{
       ev.preventDefault();ev.stopPropagation();r.classList.add('dragging');
       const rect=w.getBoundingClientRect();
       const move=e=>{pct=Math.max(28,Math.min(82,(e.clientX-rect.left)/rect.width*100));applyPct()};
       const up=()=>{r.classList.remove('dragging');localStorage.setItem(KEY,String(pct));document.removeEventListener('mousemove',move);document.removeEventListener('mouseup',up)};
       document.addEventListener('mousemove',move);document.addEventListener('mouseup',up);
     });
     w.appendChild(r);
   });
 }
 window.installExecutionActivityResizers=installResizers;
 const obs=new MutationObserver(()=>requestAnimationFrame(installResizers));
 obs.observe(document.body,{childList:true,subtree:true});
 document.addEventListener('DOMContentLoaded',()=>setTimeout(installResizers,120));
 setTimeout(installResizers,180);
})();
</script>
'''

    # SNS 편집 표의 링크 전용 열을 제거합니다.
    old = '<th style="min-width:180px">실행 내용/비고</th>${String(execEditCategory||"").includes("SNS")?\'<th style="min-width:300px">콘텐츠 링크</th>\':\'\'}<th></th></tr>'
    new = '<th style="min-width:180px">실행 내용/비고</th><th></th></tr>'
    if old not in text:
        raise RuntimeError("SNS 링크 헤더 기준점을 찾지 못했습니다.")
    text=text.replace(old,new,1)

    old = '<td><input data-f="note" value="${esc(o.execution_note)}" ${cancel?\'disabled\':\'\'}></td>${String(execEditCategory||"").includes("SNS")?`<td>${renderExecLinks(o,i,cancel)}</td>`:""}<td><button class="exec-minus'
    new = '<td><input data-f="note" value="${esc(o.execution_note)}" ${cancel?\'disabled\':\'\'}></td><td><button class="exec-minus'
    if old not in text:
        raise RuntimeError("SNS 링크 셀 기준점을 찾지 못했습니다.")
    text=text.replace(old,new,1)

    # 각 SNS 활동의 메인 행 바로 아래에 링크 전용 한 줄을 추가합니다.
    old = '${new_order}</tr>`}).join("")}</tbody></table>`;'
    # 후속 패치로 이미 문자열이 변형될 수 있어 더 안정적인 최종 행 조각을 찾습니다.
    if old not in text:
        old = '</button></td></tr>`}).join("")}</tbody></table>`;'
        new = '</button></td></tr>${String(execEditCategory||"").includes("SNS")?`<tr class="exec-link-detail-row"><td colspan="8"><div class="exec-link-detail"><div class="exec-link-detail-label">콘텐츠 링크</div>${renderExecLinks(o,i,cancel)}</div></td></tr>`:""}`}).join("")}</tbody></table>`;'
    else:
        new = '${new_order}</tr>${String(execEditCategory||"").includes("SNS")?`<tr class="exec-link-detail-row"><td colspan="8"><div class="exec-link-detail"><div class="exec-link-detail-label">콘텐츠 링크</div>${renderExecLinks(o,i,cancel)}</div></td></tr>`:""}`}).join("")}</tbody></table>`;'
    if old not in text:
        raise RuntimeError("SNS 활동 행 종료 기준점을 찾지 못했습니다.")
    text=text.replace(old,new,1)

    if "</head>" not in text or "</body>" not in text:
        raise RuntimeError("HTML 기준점을 찾지 못했습니다.")
    text=text.replace("</head>",css+"\n</head>",1)
    text=text.replace("</body>",script+f'\n<script>/* {MARKER} */</script>\n</body>',1)
    UI.write_text(text,encoding="utf-8")


if __name__ == "__main__":
    apply_patch()
