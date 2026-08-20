from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UI = ROOT / "ui" / "index.html"
MARKER = "v308-execution-compact-one-line"


def apply_patch() -> None:
    text = UI.read_text(encoding="utf-8")
    if MARKER in text:
        return

    css = r'''
<style>
/* v308-execution-compact-one-line */
.exec-table{table-layout:fixed!important}
.exec-table th,.exec-table td{padding-top:7px!important;padding-bottom:7px!important}
.exec-table th:first-child,.exec-table td:first-child{width:42%}
.exec-activity-inline{display:grid;grid-template-columns:minmax(0,2.2fr) minmax(110px,1fr);align-items:center;gap:12px;min-width:0}
.exec-activity-name{display:flex;align-items:center;min-width:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.exec-activity-name strong{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.exec-activity-channel{min-width:0;color:#7a8797;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;border-left:1px solid #e4e9ef;padding-left:12px}
</style>
'''

    script = r'''
<script>
// v308-execution-compact-one-line
(function(){
 function compactExecutionRows(){
   document.querySelectorAll('.exec-table tbody td:first-child').forEach(td=>{
     if(td.querySelector('.exec-activity-inline'))return;
     const strong=td.querySelector('strong');
     const channel=td.querySelector('.p271-placeholder');
     if(!strong||!channel)return;
     const badges=[...td.querySelectorAll('.exec-badge')];
     const wrap=document.createElement('div');wrap.className='exec-activity-inline';
     const name=document.createElement('div');name.className='exec-activity-name';
     name.appendChild(strong);
     badges.forEach(b=>name.appendChild(b));
     const ch=document.createElement('div');ch.className='exec-activity-channel';ch.textContent=channel.textContent||'';
     wrap.appendChild(name);wrap.appendChild(ch);
     td.replaceChildren(wrap);
   });
 }
 window.compactExecutionRows=compactExecutionRows;
 const obs=new MutationObserver(()=>requestAnimationFrame(compactExecutionRows));
 obs.observe(document.body,{childList:true,subtree:true});
 document.addEventListener('DOMContentLoaded',()=>setTimeout(compactExecutionRows,100));
 setTimeout(compactExecutionRows,160);
})();
</script>
'''
    if "</head>" not in text or "</body>" not in text:
        raise RuntimeError("HTML 기준점을 찾지 못했습니다.")
    text=text.replace("</head>",css+"\n</head>",1)
    text=text.replace("</body>",script+"\n</body>",1)
    UI.write_text(text,encoding="utf-8")


if __name__ == "__main__":
    apply_patch()
