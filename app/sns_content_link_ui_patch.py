from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UI = ROOT / "ui" / "index.html"
MARKER = "v306-sns-content-links"


def apply_patch() -> None:
    text = UI.read_text(encoding="utf-8")
    if MARKER in text:
        return

    css = r'''
<style>
/* v306-sns-content-links */
.exec-link-stack{display:flex;flex-direction:column;gap:5px;min-width:270px}
.exec-link-row{display:grid;grid-template-columns:minmax(0,1fr) 28px;gap:5px;align-items:center}
.exec-link-row input{min-width:0}
.exec-link-add,.exec-link-remove{font-size:10px!important;line-height:1!important;height:28px;border-radius:6px;background:#fff;cursor:pointer;font-weight:800}
.exec-link-add{border:1px solid #9bb8d8;color:#356b9e;padding:0 8px;width:max-content}
.exec-link-remove{border:1px solid #ddb0b0;color:#a74747;width:28px;padding:0}
.content-link-list{padding:10px 18px 18px;display:flex;flex-direction:column;gap:8px}
.content-link-item{display:grid;grid-template-columns:105px minmax(220px,1.3fr) minmax(300px,2fr) repeat(4,90px);gap:10px;align-items:center;padding:11px 12px;border:1px solid #e1e7ee;border-radius:9px;background:#fff}
.content-link-platform{font-size:10px;font-weight:900;color:#49657f;background:#eef4f8;border-radius:999px;padding:4px 8px;width:max-content;max-width:100%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.content-link-name b{display:block;font-size:11px}.content-link-name span{display:block;margin-top:3px;font-size:9px;color:#7b8795}
.content-link-url{min-width:0}.content-link-url a{display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:#2864bd;text-decoration:none;font-size:10px}.content-link-url a:hover{text-decoration:underline}
.content-link-metric{text-align:right}.content-link-metric small{display:block;font-size:8px;color:#8a95a3}.content-link-metric b{display:block;margin-top:2px;font-size:10px;color:#344054}
@media(max-width:1350px){.content-link-item{grid-template-columns:90px minmax(180px,1fr) minmax(260px,1.6fr) repeat(2,75px)}.content-link-item .optional-metric{display:none}}
</style>
'''
    if "</head>" not in text:
        raise RuntimeError("HTML head 종료 태그를 찾지 못했습니다.")
    text = text.replace("</head>", css + "\n</head>", 1)

    # 편집 데이터에 기존 콘텐츠 링크를 포함합니다.
    old = ',sort_order:Number(a.실행정렬순서??a.정렬순서??999999),is_new:false};'
    new = ',links:(a.콘텐츠링크||[]).map(x=>x.URL||"").filter(Boolean),sort_order:Number(a.실행정렬순서??a.정렬순서??999999),is_new:false};'
    if old not in text:
        raise RuntimeError("실행 편집 데이터 기준점을 찾지 못했습니다.")
    text = text.replace(old, new, 1)

    old = 'execution_type:"활동추가",sort_order:(execEditItems.length+1)*10,is_new:true}'
    new = 'execution_type:"활동추가",links:[],sort_order:(execEditItems.length+1)*10,is_new:true}'
    if old not in text:
        raise RuntimeError("신규 실행활동 기준점을 찾지 못했습니다.")
    text = text.replace(old, new, 1)

    # 입력값을 읽을 때 링크 배열도 함께 수집합니다.
    old = 'o.execution_note=q("note");});'
    new = 'o.execution_note=q("note");o.links=[...tr.querySelectorAll("[data-link]")].map(x=>x.value.trim()).filter(Boolean);});'
    if old not in text:
        raise RuntimeError("실행 입력 수집 기준점을 찾지 못했습니다.")
    text = text.replace(old, new, 1)

    helper_anchor = 'function renderExecModalTable(){'
    helper = r'''function renderExecLinks(o,i,cancel){
   if(!String(execEditCategory||"").includes("SNS"))return "";
   const links=Array.isArray(o.links)?o.links:[];
   const rows=(links.length?links:[""]).map((url,j)=>`<div class="exec-link-row"><input data-link="${j}" placeholder="https://..." value="${esc(url||"")}" ${cancel?'disabled':''}><button class="exec-link-remove" onclick="removeExecutionLink(${i},${j})" ${cancel?'disabled':''}>−</button></div>`).join("");
   return `<div class="exec-link-stack">${rows}<button class="exec-link-add" onclick="addExecutionLink(${i})" ${cancel?'disabled':''}>+ 링크</button></div>`;
 }
 window.addExecutionLink=function(i){pullExecInputs();const o=execEditItems[i];if(!o)return;o.links=Array.isArray(o.links)?o.links:[];o.links.push("");renderExecModalTable()};
 window.removeExecutionLink=function(i,j){pullExecInputs();const o=execEditItems[i];if(!o)return;o.links=Array.isArray(o.links)?o.links:[];o.links.splice(j,1);renderExecModalTable()};
 '''
    if helper_anchor not in text:
        raise RuntimeError("실행 편집 렌더 기준점을 찾지 못했습니다.")
    text = text.replace(helper_anchor, helper + helper_anchor, 1)

    # SNS 팝업에서만 콘텐츠 링크 열을 노출합니다.
    old = '<th style="min-width:180px">실행 내용/비고</th><th></th></tr>'
    new = '<th style="min-width:180px">실행 내용/비고</th>${String(execEditCategory||"").includes("SNS")?\'<th style="min-width:300px">콘텐츠 링크</th>\':\'\'}<th></th></tr>'
    if old not in text:
        raise RuntimeError("실행 편집 헤더 기준점을 찾지 못했습니다.")
    text = text.replace(old, new, 1)

    old = '<td><input data-f="note" value="${esc(o.execution_note)}" ${cancel?\'disabled\':\'\'}></td><td><button class="exec-minus'
    new = '<td><input data-f="note" value="${esc(o.execution_note)}" ${cancel?\'disabled\':\'\'}></td>${String(execEditCategory||"").includes("SNS")?`<td>${renderExecLinks(o,i,cancel)}</td>`:""}<td><button class="exec-minus'
    if old not in text:
        raise RuntimeError("실행 편집 링크 셀 기준점을 찾지 못했습니다.")
    text = text.replace(old, new, 1)

    script = r'''
<script>
// v306-sns-content-links
(function(){
 function metric(v){const n=Number(v||0);return n?n.toLocaleString("ko-KR"):"—"}
 function contentRows(){
   return (currentPerformanceData?.콘텐츠성과||[]).filter(x=>x.URL).sort((a,b)=>Number(a.링크순서||999999)-Number(b.링크순서||999999));
 }
 function renderSNSContentLinks(){
   const panel=[...document.querySelectorAll("#performanceContent .p271-panel")].find(p=>p.querySelector("h3")?.textContent.trim().startsWith("5."));
   if(!panel)return;
   const rows=contentRows();
   panel.innerHTML=`<div class="p271-panel-head"><div><h3>5. SNS·바이럴 콘텐츠 반응</h3><p>실제 실행 활동에 등록한 콘텐츠 링크와 링크별 반응 지표를 표시합니다.</p></div><span class="p271-panel-tag">${rows.length}건</span></div>
   ${rows.length?`<div class="content-link-list">${rows.map(r=>`<div class="content-link-item"><div class="content-link-platform">${esc(r.플랫폼||"웹")}</div><div class="content-link-name"><b>${esc(r.콘텐츠명||"콘텐츠")}</b><span>${esc(r.채널명||"")}</span></div><div class="content-link-url"><a href="${esc(r.URL)}" target="_blank" rel="noopener noreferrer" title="${esc(r.URL)}">${esc(r.URL)}</a></div><div class="content-link-metric"><small>조회</small><b>${metric(r.조회수)}</b></div><div class="content-link-metric"><small>좋아요</small><b>${metric(r.좋아요수)}</b></div><div class="content-link-metric optional-metric"><small>댓글</small><b>${metric(r.댓글수)}</b></div><div class="content-link-metric optional-metric"><small>공유</small><b>${metric(r.공유수)}</b></div></div>`).join("")}</div>`:'<div class="perf-empty">등록된 SNS·바이럴 콘텐츠 링크가 없습니다.</div>'}`;
   if(window.applyGlobalFontScale)setTimeout(()=>window.applyGlobalFontScale(),0);
 }
 window.renderSNSContentLinks=renderSNSContentLinks;
 const oldRender=window.renderPerformancePage;
 if(typeof oldRender==="function")window.renderPerformancePage=function(r){oldRender(r);setTimeout(renderSNSContentLinks,0)};
 const obs=new MutationObserver(()=>{
   if(document.querySelector("#performanceContent") && currentPerformanceData)setTimeout(renderSNSContentLinks,0);
 });
 const root=document.getElementById("performanceContent");if(root)obs.observe(root,{childList:true,subtree:true});
 setTimeout(renderSNSContentLinks,250);
})();
</script>
'''
    if "</body>" not in text:
        raise RuntimeError("HTML body 종료 태그를 찾지 못했습니다.")
    text = text.replace("</body>", script + f'\n<script>/* {MARKER} */</script>\n</body>', 1)
    UI.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    apply_patch()
