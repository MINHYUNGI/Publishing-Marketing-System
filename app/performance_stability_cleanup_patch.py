from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UI = ROOT / "ui" / "index.html"
MARKER = "v312-performance-stability-cleanup"


def apply_patch() -> None:
    text = UI.read_text(encoding="utf-8")
    if MARKER in text:
        return

    # SNS 콘텐츠 영역이 자기 자신을 다시 그린 뒤 MutationObserver가 그 변경을 다시 감지해
    # 무한 재렌더링하는 루프를 제거합니다. 성과 페이지 본 렌더 함수에서 1회 호출이면 충분합니다.
    old_obs = r'''   const obs=new MutationObserver(()=>{
   if(document.querySelector("#performanceContent") && currentPerformanceData)setTimeout(renderSNSContentLinks,0);
 });
 const root=document.getElementById("performanceContent");if(root)obs.observe(root,{childList:true,subtree:true});
 setTimeout(renderSNSContentLinks,250);'''
    new_obs = r'''   // 성과 페이지 렌더 완료 후 1회만 갱신합니다. 자기 DOM 변경을 감시하지 않습니다.
 setTimeout(renderSNSContentLinks,250);'''
    if old_obs in text:
        text = text.replace(old_obs, new_obs, 1)

    # ERP 일별 UI 패치의 네 번째 'ERP 데이터 기간' KPI 카드를 제거합니다.
    old_kpi = r'''   if(kpis[3]){
     const first=erpRows[0]?.매출일자,last=erpRows[erpRows.length-1]?.매출일자;
     kpis[3].innerHTML=`<span>ERP 데이터 기간</span><strong>${erpRows.length?erpRows.length.toLocaleString("ko-KR")+"일":"—"}</strong><small>${erpRows.length?`${first} ~ ${last}`:"업로드 대기"}</small>`;
   }'''
    new_kpi = r'''   if(kpis[3])kpis[3].remove();'''
    if old_kpi in text:
        text = text.replace(old_kpi, new_kpi, 1)

    css = r'''
<style>
/* v312-performance-stability-cleanup */
.p271-kpis{
  grid-template-columns:repeat(3,minmax(155px,1fr))!important;
  min-width:500px!important;
}
.p271-book-card{
  grid-template-columns:92px minmax(480px,680px) minmax(500px,1fr)!important;
}
@media(max-width:1450px){
 .p271-book-card{grid-template-columns:82px minmax(420px,600px) minmax(470px,1fr)!important}
 .p271-kpis{min-width:470px!important;grid-template-columns:repeat(3,minmax(145px,1fr))!important}
}
@media(max-width:1200px){
 .p271-book-card{grid-template-columns:80px minmax(0,1fr)!important}
 .p271-kpis{grid-column:1/-1;min-width:0!important;grid-template-columns:repeat(3,minmax(135px,1fr))!important}
}
</style>
'''

    if "</head>" not in text:
        raise RuntimeError("HTML head 종료 태그를 찾지 못했습니다.")
    text = text.replace("</head>", css + f'\n<script>/* {MARKER} */</script>\n</head>', 1)
    UI.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    apply_patch()
