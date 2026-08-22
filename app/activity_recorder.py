from __future__ import annotations

from datetime import date
from typing import Any
from uuid import uuid4

from openai import OpenAI
from pydantic import BaseModel, Field

from .config import OPENAI_MODEL


class SalesActivityDetail(BaseModel):
    activity_type: str
    activity_date: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    original_date_expression: str | None = None
    count: int | None = Field(default=None, ge=0)
    content: str | None = None


class SalesActivityAnalysis(BaseModel):
    channel: str | None = None
    assignee_name: str | None = None
    client_name: str | None = None
    activity_type: str | None = None
    activity_summary: str | None = None
    product_code: str | None = None
    product_name: str | None = None
    isbn: str | None = None
    multiple_products: bool = False
    activity_start_date: str | None = None
    activity_end_date: str | None = None
    result_date: str | None = None
    original_date_expression: str | None = None
    meeting_count: int | None = Field(default=None, ge=0)
    proposal_sent: bool | None = None
    sample_provided: bool | None = None
    activity_details: str | None = None
    detail_activities: list[SalesActivityDetail] = Field(default_factory=list)
    delivered_units: int | None = Field(default=None, ge=0)
    sales_amount: int | None = Field(default=None, ge=0)
    operating_profit: int | None = None
    operating_profit_rate: float | None = None
    other_result: str | None = None
    note: str | None = None
    review_notes: list[str] = Field(default_factory=list)


SYSTEM_PROMPT = """당신은 미래엔 출판사업본부의 마케팅·영업 활동 기록 구조화 담당자입니다.
사용자 원문에 실제로 있는 사실만 구조화하십시오. 없는 거래처, 제품, 날짜, 수량, 금액, 성과를 추측하지 마십시오.
모르는 값은 null로 반환하십시오. 매출액과 영업이익은 원 단위 정수로 변환합니다.
예: 15백만원=15000000, 3백만원=3000000. 비율 20%는 20으로 반환합니다.
명백한 산술(매출 15000000원과 이익률 20% => 이익 3000000원)만 계산할 수 있습니다.
연도 없는 월/일은 제공된 시스템 기준일의 연도를 사용하되, 문맥상 애매하면 review_notes에 남깁니다.
'7월부터 8월 초'처럼 정확한 일이 없는 표현은 임의 날짜를 만들지 말고 original_date_expression에 보존합니다.
한 원문에 미팅, 제안서, 협상, 채택, 납품 등 여러 과정이 있으면 detail_activities로 분리합니다.
제품코드나 ISBN을 새로 만들지 마십시오. 제품 공식 정보 검증은 별도 ERP 단계에서 수행됩니다.
"""


def analyze_sales_activity(
    original_text: str,
    api_key: str,
    *,
    selected_channel: str | None = None,
    selected_assignee_name: str | None = None,
    selected_product: dict[str, Any] | None = None,
    reference_date: date | None = None,
) -> dict[str, Any]:
    text = str(original_text or "").strip()
    if not text:
        raise ValueError("마케팅·영업 활동 원문을 입력해 주세요.")
    reference = reference_date or date.today()
    product_context = "선택 안 함"
    if selected_product:
        product_context = f"{selected_product.get('제품코드')} / {selected_product.get('제품명')}"
    user_prompt = f"""[시스템 기준일]
{reference.isoformat()}

[화면 사전 선택]
채널: {selected_channel or '선택 안 함'}
담당자: {selected_assignee_name or '선택 안 함'}
제품: {product_context}

[사용자 원문]
{text}

화면 사전 선택값도 참고하되 원문과 충돌하면 원문을 임의로 덮어쓰지 말고 review_notes에 충돌을 적으십시오.
원문을 지정된 구조로 정확하게 변환하십시오."""
    response = OpenAI(api_key=api_key).responses.parse(
        model=OPENAI_MODEL,
        input=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        text_format=SalesActivityAnalysis,
    )
    parsed = response.output_parsed
    if parsed is None:
        raise RuntimeError("AI가 구조화된 분석 결과를 반환하지 않았습니다.")
    return {
        "request_id": str(uuid4()),
        "model": OPENAI_MODEL,
        "reference_date": reference.isoformat(),
        "original_text": text,
        "analysis": parsed.model_dump(),
    }


def split_channels(users: list[dict[str, Any]]) -> dict[str, list[dict[str, str]]]:
    mapping: dict[str, list[dict[str, str]]] = {}
    for user in users:
        if not user.get("사용여부", True):
            continue
        for raw in str(user.get("담당채널") or "").replace("，", ",").split(","):
            channel = raw.strip()
            if not channel:
                continue
            item = {"사용자ID": str(user.get("사용자ID") or ""), "이름": str(user.get("이름") or "")}
            if item not in mapping.setdefault(channel, []):
                mapping[channel].append(item)
    return dict(sorted(mapping.items(), key=lambda item: item[0]))


def enrich_analysis(
    result: dict[str, Any],
    *,
    users: list[dict[str, Any]],
    selected_channel: str | None,
    selected_assignee_id: str | None,
    selected_product: dict[str, Any] | None,
    erp_product: dict[str, Any] | None,
) -> dict[str, Any]:
    raw = dict(result["analysis"])
    draft = dict(raw)
    warnings = list(raw.get("review_notes") or [])
    if selected_channel:
        if raw.get("channel") and raw["channel"] != selected_channel:
            warnings.append(f"선택 채널({selected_channel})과 원문 채널({raw['channel']})이 다릅니다.")
        draft["channel"] = selected_channel
    selected_user = next((u for u in users if str(u.get("사용자ID")) == str(selected_assignee_id)), None)
    if selected_user:
        draft["assignee_id"] = str(selected_user["사용자ID"])
        draft["assignee_name"] = selected_user.get("이름")

    extracted_code = str(raw.get("product_code") or "").strip()
    selected_code = str((selected_product or {}).get("제품코드") or "").strip()
    if selected_code and extracted_code and selected_code != extracted_code:
        warnings.append("선택한 도서와 AI가 추출한 제품이 다릅니다.")
        draft["product_conflict"] = True
    official = erp_product or selected_product
    if extracted_code and not erp_product:
        warnings.append(f"ERP제품마스터에 존재하지 않는 제품코드입니다: {extracted_code}")
        draft["invalid_product_code"] = True
    elif official:
        official_code = str(official.get("제품코드") or "")
        ai_name = str(raw.get("product_name") or "").strip()
        official_name = str(official.get("제품명") or "")
        if ai_name and official_name and ai_name != official_name:
            warnings.append(f"입력 제품명({ai_name}) 대신 ERP 공식 제품명({official_name})을 사용합니다.")
        draft.update({
            "product_code": official_code,
            "product_name": official_name,
            "isbn": official.get("ISBN"),
            "product_brand": official.get("브랜드명"),
            "product_status": official.get("제품상태"),
        })
    result["draft"] = draft
    result["warnings"] = list(dict.fromkeys(warnings))
    return result
