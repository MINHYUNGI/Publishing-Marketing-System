from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UI = ROOT / "ui" / "index.html"
MARKER = "v298-execution-layout-drag"


def apply_patch() -> None:
    text = UI.read_text(encoding="utf-8")
    if MARKER in text:
        return

    css = r'''
<style>
/* v298-execution-layout-drag */
.exec-table{
  width:100% !important;
  table-layout:fixed !important;
  min-width:0 !important;
}
.exec-table th:nth-child(1), .exec-table td:nth-child(1){width:48% !important;}
.exec-table th:nth-child(2), .exec-table td:nth-child(2){width:12% !important;}
.exec-table th:nth-child(3), .exec-table td:nth-child(3){width:12% !important;}
.exec-table th:nth-child(4), .exec-table td:nth-child(4){width:10% !important;}
.exec-table th:nth-child(5), .exec-table td:nth-child(5){width:10% !important;}
.exec-table th:nth-child(6), .exec-table td:nth-child(6){width:8% !important;}
.exec-table th,.exec-table td{box-sizing:border-box;}
.exec-table td:first-child{overflow:hidden;}
.exec-table td:first-child strong,
.exec-table td:first-child .p271-placeholder{display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
.exec-modal-head{cursor:move;user-select:none;touch-action:none;}
.exec-modal-head button,.exec-modal-head input,.exec-modal-head a{cursor:pointer;}
.exec-modal{will-change:transform;}
</style>
'''

    script = r'''
<script>
// v298-execution-layout-drag
(function(){
  let dragState=null;

  function beginDrag(e){
    const head=e.target.closest?.('.exec-modal-head');
    if(!head)return;
    if(e.target.closest('button,input,select,textarea,a'))return;
    const modal=head.closest('.exec-modal');
    if(!modal)return;
    e.preventDefault();
    const currentX=Number(modal.dataset.dragX||0);
    const currentY=Number(modal.dataset.dragY||0);
    dragState={modal,startX:e.clientX,startY:e.clientY,baseX:currentX,baseY:currentY};
    head.setPointerCapture?.(e.pointerId);
  }

  function moveDrag(e){
    if(!dragState)return;
    const {modal,startX,startY,baseX,baseY}=dragState;
    let nextX=baseX+(e.clientX-startX);
    let nextY=baseY+(e.clientY-startY);

    const oldTransform=modal.style.transform;
    modal.style.transform=`translate(${nextX}px, ${nextY}px)`;
    let rect=modal.getBoundingClientRect();
    const margin=12;

    if(rect.left<margin) nextX+=margin-rect.left;
    if(rect.right>window.innerWidth-margin) nextX-=rect.right-(window.innerWidth-margin);
    if(rect.top<margin) nextY+=margin-rect.top;
    if(rect.bottom>window.innerHeight-margin) nextY-=rect.bottom-(window.innerHeight-margin);

    modal.dataset.dragX=String(nextX);
    modal.dataset.dragY=String(nextY);
    modal.style.transform=`translate(${nextX}px, ${nextY}px)`;
  }

  function endDrag(){dragState=null;}

  document.addEventListener('pointerdown',beginDrag,true);
  document.addEventListener('pointermove',moveDrag,true);
  document.addEventListener('pointerup',endDrag,true);
  document.addEventListener('pointercancel',endDrag,true);

  // 팝업이 처음 열릴 때는 중앙 위치에서 시작합니다.
  const observer=new MutationObserver(()=>{
    const backdrop=document.getElementById('execModalBackdrop');
    const modal=backdrop?.querySelector('.exec-modal');
    if(!backdrop||!modal)return;
    if(backdrop.classList.contains('show') && backdrop.dataset.dragOpened!=='1'){
      backdrop.dataset.dragOpened='1';
      modal.dataset.dragX='0';modal.dataset.dragY='0';modal.style.transform='translate(0px, 0px)';
    }
    if(!backdrop.classList.contains('show'))backdrop.dataset.dragOpened='0';
  });
  observer.observe(document.body,{subtree:true,attributes:true,attributeFilter:['class'],childList:true});
})();
</script>
'''

    if "</head>" not in text or "</body>" not in text:
        raise RuntimeError("HTML 기준점을 찾지 못했습니다.")
    text = text.replace("</head>", css + "\n</head>", 1)
    text = text.replace("</body>", script + "\n</body>", 1)
    UI.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    apply_patch()
