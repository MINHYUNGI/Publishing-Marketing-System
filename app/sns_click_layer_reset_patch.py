from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
UI=ROOT/'ui'/'index.html'
MARKER='v329-sns-click-layer-reset'
def apply_patch():
 text=UI.read_text(encoding='utf-8')
 if MARKER in text:return
 css=r'''<style>/* v329-sns-click-layer-reset */
/* 5번 영역의 장식/레이아웃 레이어는 클릭을 받지 않고 실제 콘텐츠만 받도록 정리 */
.p271-digital-cards{isolation:isolate!important;position:relative!important;z-index:1!important;pointer-events:auto!important}
.p271-digital-cards>*{pointer-events:auto!important}
.content-link-item{position:relative!important;z-index:2!important;pointer-events:auto!important}
.content-link-item>*{position:relative!important;z-index:3!important;pointer-events:auto!important}
.content-link-content,.content-link-content b{z-index:20!important;pointer-events:auto!important}
.content-link-content a{z-index:10000!important;pointer-events:auto!important;cursor:pointer!important}
.content-link-item::before,.content-link-item::after,.p271-digital-cards::before,.p271-digital-cards::after,.p271-panel::before,.p271-panel::after{pointer-events:none!important}
</style>'''
 script=r'''<script>// v329-sns-click-layer-reset
(function(){
 function reset(){
  document.querySelectorAll('.content-link-content a').forEach(a=>{
   a.style.pointerEvents='auto';a.style.position='relative';a.style.zIndex='10000';
  });
 }
 document.addEventListener('DOMContentLoaded',()=>setTimeout(reset,200));
 const o=new MutationObserver(()=>reset());o.observe(document.documentElement,{childList:true,subtree:true});
 // pointerdown 진단: 링크에 마우스가 실제 닿으면 창 제목에 POINTER가 표시됩니다.
 document.addEventListener('pointerdown',e=>{const a=e.target.closest?.('.content-link-content a');if(a)document.title='POINTER · '+(a.href||'');},true);
})();</script>'''
 text=text.replace('</head>',css+'\n</head>',1).replace('</body>',script+f'\n<script>/* {MARKER} */</script>\n</body>',1)
 UI.write_text(text,encoding='utf-8')
if __name__=='__main__':apply_patch()
