from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UI = ROOT / "ui" / "index.html"
MARKER = "v289-performance-first-marketing-period-60-default"


def apply_patch() -> None:
    text = UI.read_text(encoding="utf-8")
    if MARKER in text:
        return

    # 기본 조회기간은 첫 마케팅일 기준 60일입니다.
    text = text.replace("let performancePeriod=30;", "let performancePeriod=60;", 1)

    old = 'function performanceVisibleSeries(){return (currentPerformanceData?.__series||[]).slice(-performancePeriod)}'
    if old in text:
        new = r'''// v289-performance-first-marketing-period-60-default
function performanceFirstMarketingDate(){
 const acts=currentPerformanceData?.마케팅활동||[];
 const dates=acts.map(a=>perfDate(a.시작일)).filter(Boolean).sort((a,b)=>a-b);
 return dates.length?dates[0]:null;
}
function performanceVisibleSeries(){
 const source=currentPerformanceData?.__series||[];
 const anchor=performanceFirstMarketingDate();
 if(!anchor)return source.slice(-performancePeriod);
 const byDate=new Map(source.map(x=>[String(x.date).slice(0,10),x]));
 const rows=[];
 for(let i=0;i<performancePeriod;i++){
   const d=new Date(anchor);d.setDate(anchor.getDate()+i);
   const key=d.toISOString().slice(0,10);
   rows.push(byDate.get(key)||{date:key,scm:0,erp:0,scmSales:0,erpSales:0});
 }
 return rows;
}'''
        text = text.replace(old, new, 1)

    old_note = '<div class="p271-toolbar"><div class="p271-period"><span>조회기간</span>'
    new_note = '<div class="p271-toolbar"><div class="p271-period"><span>첫 마케팅일 기준</span>'
    text = text.replace(old_note, new_note, 1)

    # 이전 패치가 이미 적용된 로컬 HTML에서도 기본값만 확실하게 60일로 보정합니다.
    text = text.replace("let performancePeriod=30;", "let performancePeriod=60;")

    UI.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    apply_patch()
