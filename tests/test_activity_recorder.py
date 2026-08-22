from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.activity_recorder import enrich_analysis, split_channels
from app.backend import Backend


USERS = [
    {"사용자ID": "u1", "이름": "정슬기", "담당채널": "납품, 공동구매", "사용여부": True},
    {"사용자ID": "u2", "이름": "우광일", "담당채널": "쿠팡", "사용여부": True},
]


def test_split_channels_supports_multiple_channels_per_user():
    mapping = split_channels(USERS)
    assert mapping["납품"] == [{"사용자ID": "u1", "이름": "정슬기"}]
    assert mapping["공동구매"] == [{"사용자ID": "u1", "이름": "정슬기"}]
    assert mapping["쿠팡"] == [{"사용자ID": "u2", "이름": "우광일"}]


def test_erp_official_product_overrides_ai_product_name_and_warns_on_conflict():
    result = {
        "analysis": {"product_code": "P2", "product_name": "사용자 책", "review_notes": []},
    }
    enriched = enrich_analysis(
        result,
        users=USERS,
        selected_channel="납품",
        selected_assignee_id="u1",
        selected_product={"제품코드": "P1", "제품명": "선택 책"},
        erp_product={"제품코드": "P2", "제품명": "ERP 공식명", "ISBN": "9781", "브랜드명": "브랜드", "제품상태": "판매중"},
    )
    assert enriched["draft"]["product_name"] == "ERP 공식명"
    assert enriched["draft"]["product_conflict"] is True
    assert any("선택한 도서" in warning for warning in enriched["warnings"])


@patch("app.backend.get_openai_api_key", return_value="test-key")
@patch("app.backend.analyze_sales_activity")
def test_analysis_creates_draft_without_any_database_write(analyze, _key):
    analyze.return_value = {
        "request_id": "req",
        "model": "model",
        "reference_date": "2026-08-22",
        "original_text": "활동 원문",
        "analysis": {"channel": "납품", "product_code": None, "review_notes": []},
    }
    backend = Backend()
    backend.users = USERS
    backend.db = MagicMock()
    backend.db.fetch_erp_product_master.return_value = None

    result = backend.analyze_ai_marketing_sales_activity({
        "channel": "납품", "assignee_id": "u1", "original_text": "활동 원문",
    })

    assert result["ok"] is True
    backend.db.save_ai_marketing_sales_activity.assert_not_called()


def test_confirm_save_validates_and_uses_atomic_repository_call():
    backend = Backend()
    backend.users = USERS
    backend.db = MagicMock()
    backend.db.fetch_erp_product_master.return_value = {
        "제품코드": "P1", "제품명": "ERP 책", "ISBN": "9781",
    }
    backend.db.save_ai_marketing_sales_activity.return_value = {
        "기록ID": "record-1", "중복": False, "세부활동수": 1,
    }
    result = backend.save_ai_marketing_sales_activity({
        "request_id": "11111111-1111-1111-1111-111111111111",
        "registrar_id": "u1",
        "original_text": "웅진씽크빅 납품 활동",
        "ai_analysis_json": {"original": True},
        "draft": {
            "channel": "납품", "assignee_id": "u1", "client_name": "웅진씽크빅",
            "product_code": "P1", "activity_details": "제안 및 납품", "sales_amount": 15_000_000,
            "detail_activities": [{"activity_type": "미팅", "count": 3, "content": "담당자 미팅"}],
        },
    })
    assert result["ok"] is True
    record, details = backend.db.save_ai_marketing_sales_activity.call_args.args
    assert record["제품명"] == "ERP 책"
    assert record["AI분석JSON"] == {"original": True}
    assert record["매출액"] == 15_000_000
    assert details[0]["횟수"] == 3
