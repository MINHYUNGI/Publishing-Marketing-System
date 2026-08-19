from __future__ import annotations
from pathlib import Path
from typing import Any
from openai import OpenAI
from pydantic import BaseModel, Field

from .config import OPENAI_MODEL, PROMPT_DIR
from .document_reader import read_document_text, extract_sales_targets

class ActivityItem(BaseModel):
    activity_category: str
    detail_category: str | None = None
    channel_or_media: str | None = None
    activity_name: str
    start_date: str | None = None
    end_date: str | None = None
    schedule_note: str | None = None
    cost: int | None = Field(default=None, ge=0)
    url: str | None = None
    note: str | None = None
    plan_execution_type: str = "계획"
    evidence: str | None = None
    confidence: float = Field(ge=0, le=1)
    needs_review: bool = False
    review_reason: str | None = None


class SalesTargets(BaseModel):
    initial_units: int | None = Field(default=None, ge=0)
    initial_sales: int | None = Field(default=None, ge=0)
    month3_units: int | None = Field(default=None, ge=0)
    month3_sales: int | None = Field(default=None, ge=0)
    month6_units: int | None = Field(default=None, ge=0)
    month6_sales: int | None = Field(default=None, ge=0)
    month12_units: int | None = Field(default=None, ge=0)
    month12_sales: int | None = Field(default=None, ge=0)
    bep_units: int | None = Field(default=None, ge=0)
    bep_sales: int | None = Field(default=None, ge=0)
    bep_target_month: int | None = Field(default=None, ge=0)
    bep_target_note: str | None = None

class MarketingStrategy(BaseModel):
    target_readers: str | None = None
    core_keywords: list[str] = []
    marketing_message: str | None = None
    marketing_strategy: str | None = None
    usp: str | None = None
    confidence: float = Field(default=0, ge=0, le=1)
    evidence: str | None = None

class DocumentActivityAnalysis(BaseModel):
    document_title: str | None = None
    document_summary: str | None = None
    strategy: MarketingStrategy = MarketingStrategy()
    activities: list[ActivityItem] = []
    sales_targets: SalesTargets = SalesTargets()
    review_notes: list[str] = []

def _load_prompt() -> str:
    blocks = []
    for f in sorted(PROMPT_DIR.glob("*.txt")):
        blocks.append(f"\n### {f.name}\n{f.read_text(encoding='utf-8')}")
    return "\n".join(blocks)

def analyze_document(path: Path, selected_product: dict[str, Any], api_key: str) -> dict[str, Any]:
    text = read_document_text(path)
    direct_sales_targets = extract_sales_targets(path)
    prompt_knowledge = _load_prompt()

    product_code = selected_product["제품코드"]
    product_name = selected_product["제품명"]

    system_prompt = f"""당신은 미래엔 출판사업본부의 마케팅 계획서 분석 담당자입니다.

중요:
- 이 문서의 대상 제품은 사람이 제품인덱스에서 이미 확정했습니다.
- 제품을 추정하거나 변경하지 마십시오.
- 제품코드: {product_code}
- 제품명: {product_name}
- 당신의 역할은 이 제품의 '마케팅 전략정보'와 '실행 활동'을 문서에서 정확하게 구조화하는 것입니다.

[전략정보]
다음 항목을 문서에서 찾아 구조화하십시오.
1. 마케팅 타깃 독자
2. 핵심 키워드
3. 마케팅 문구 / 핵심 메시지
4. 마케팅 전략
5. USP / 도서 차별점

[영업목표]
- 초도 배본, 출간~3개월, 출간~6개월, 출간~12개월, BEP의 부수/매출액 숫자가 있으면 정확히 추출하십시오.
- 숫자가 없으면 null로 두십시오. 합계나 기간 값을 임의로 추정하지 마십시오.
- 단, Excel에서는 프로그램이 셀을 직접 읽은 값이 최종적으로 우선 적용됩니다.

전략정보는 문서에 실제로 있는 내용만 사용하십시오.
문서에 근거가 없으면 null 또는 빈 목록으로 두십시오.
여러 문장을 임의로 과장하거나 새 전략을 창작하지 마십시오.

[실행활동]
- 원문에 없는 날짜, 비용, 활동을 만들지 마십시오.
- 묶음 비용을 활동별로 임의 배분하지 마십시오.
- 활동분류는 반드시 '서점 마케팅', 'SNS·바이럴', '기타 추가 마케팅' 중 하나를 사용하십시오.
- 계획실행구분은 반드시 '계획', '실행', '추가' 중 하나를 사용하십시오.
- 모호한 항목은 needs_review=true로 표시하십시오.
- 한 문단/셀에 서로 다른 활동이 여러 개 있으면 가능한 범위에서 개별 활동으로 분리하십시오.

[업무지식과 출력 규칙]
{prompt_knowledge}
"""

    user_prompt = f"""[확정 제품]
제품코드: {product_code}
제품명: {product_name}

[원본 파일명]
{path.name}

[문서에서 추출한 텍스트]
{text}

위 문서에서 마케팅 전략정보와 마케팅 실행활동을 모두 추출하십시오."""

    client = OpenAI(api_key=api_key)
    response = client.responses.parse(
        model=OPENAI_MODEL,
        input=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        text_format=DocumentActivityAnalysis,
    )
    result = response.output_parsed
    if result is None:
        raise RuntimeError("AI가 구조화된 분석 결과를 반환하지 않았습니다.")

    analysis = result.model_dump()
    if direct_sales_targets:
        merged = dict(analysis.get("sales_targets") or {})
        merged.update(direct_sales_targets)
        analysis["sales_targets"] = merged
    analysis.update({
        "matched": True,
        "product_code": product_code,
        "product_name": product_name,
        "product_confidence": 1.0,
        "product_reason": "사용자가 제품인덱스에서 직접 선택함",
        "product_evidence": "사용자 직접 연결",
    })

    return {
        "file_path": str(path),
        "file_name": path.name,
        "document_text_preview": text[:1000],
        "analysis": analysis,
    }
