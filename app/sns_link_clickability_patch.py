from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
UI=ROOT/'ui'/'index.html'
MARKER='v328-sns-link-clickability'
def apply_patch():
    text=UI.read_text(encoding='utf-8')
    if MARKER in text:return
    css=r'''<style>/* v328-sns-link-clickability */
.p271-digital-cards,.content-link-item,.content-link-channel,.content-link-content,.content-link-content b{position:relative!important;pointer-events:auto!important}
.content-link-item::before,.content-link-item::after,.p271-digital-cards::before,.p271-digital-cards::after{pointer-events:none!important}
.content-link-content{z-index:50!important;overflow:visible!important}
.content-link-content b{z-index:51!important;overflow:visible!important}
.content-link-content a{position:relative!important;z-index:9999!important;pointer-events:auto!important;cursor:pointer!important;display:inline-block!important;max-width:100%!important;white-space:nowrap!important;overflow:hidden!important;text-overflow:ellipsis!important;color:#175cd3!important;text-decoration:underline!important;text-underline-offset:2px!important;-webkit-user-select:text!important;user-select:text!important}
</style>'''
    # 캡처 단계에서 클릭이 실제 A 요소에 도달하는지만 화면에 표시합니다. 링크 기본 동작은 막지 않습니다.
    script=r'''<script>// v328-sns-link-clickability
(function(){document.addEventListener('click',function(e){const a=e.target.closest?.('.content-link-content a');if(!a)return;document.title='LINK CLICK · '+(a.href||'');},true);})();</script>'''
    text=text.replace('</head>',css+'\n</head>',1).replace('</body>',script+f'\n<script>/* {MARKER} */</script>\n</body>',1)
    UI.write_text(text,encoding='utf-8')
if __name__=='__main__':apply_patch()
