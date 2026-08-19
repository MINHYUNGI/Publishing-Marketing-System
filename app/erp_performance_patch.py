from __future__ import annotations

from .database import Database


def apply_erp_performance_patch() -> None:
    original = Database.fetch_post_launch_performance
    if getattr(original, "_erp_daily_patched", False):
        return

    def wrapped(self: Database, product_code: str):
        detail = original(self, product_code)
        if not detail:
            return detail
        rows = (
            self.client.table("ERP일별판매실적")
            .select("제품코드,제품명,매출일자,매출부수,매출금액,출고부수,출고금액,반품부수,반품금액,원본파일명")
            .eq("제품코드", product_code)
            .order("매출일자")
            .execute()
        ).data or []
        detail["ERP일별판매실적"] = rows

        # 현재 단계에서는 SCM을 연결하지 않고 ERP 일별 데이터만 성과 그래프에 공급합니다.
        erp_for_dashboard = []
        for row in rows:
            erp_for_dashboard.append({
                "제품코드": product_code,
                "판매일": row.get("매출일자"),
                "데이터구분": "ERP",
                "판매구분": "ERP",
                "판매부수": row.get("매출부수") or 0,
                "판매금액": row.get("매출금액") or 0,
                "매출부수": row.get("매출부수") or 0,
                "매출금액": row.get("매출금액") or 0,
                "출고부수": row.get("출고부수") or 0,
                "출고금액": row.get("출고금액") or 0,
                "반품부수": row.get("반품부수") or 0,
                "반품금액": row.get("반품금액") or 0,
            })
        detail["판매실적일별"] = erp_for_dashboard
        return detail

    wrapped._erp_daily_patched = True
    Database.fetch_post_launch_performance = wrapped
