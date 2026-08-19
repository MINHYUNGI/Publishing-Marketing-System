from __future__ import annotations

from .database import Database


def apply_erp_performance_patch() -> None:
    original = Database.fetch_post_launch_performance
    if getattr(original, "_erp_monthly_patched", False):
        return

    def wrapped(self: Database, product_code: str):
        detail = original(self, product_code)
        if not detail:
            return detail
        rows = (
            self.client.table("ERP월별판매실적")
            .select("제품코드,제품명,년월,매출부수,매출금액,출고부수,출고금액,반품부수,반품금액,원천시트")
            .eq("제품코드", product_code)
            .order("년월")
            .execute()
        ).data or []
        detail["ERP월별판매실적"] = rows
        # SCM은 아직 연결하지 않습니다. 기존 빈 일별 테이블도 ERP 계산에 사용하지 않습니다.
        return detail

    wrapped._erp_monthly_patched = True
    Database.fetch_post_launch_performance = wrapped
