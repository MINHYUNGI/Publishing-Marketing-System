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

        # 현재 성과 UI의 일별 시리즈 필드에 ERP 순매출만 매핑합니다.
        # SCM 관련 값은 0으로 유지하며 별도 연결 시점까지 사용하지 않습니다.
        erp_for_dashboard = []
        for row in rows:
            erp_for_dashboard.append({
                "제품코드": product_code,
                "판매일": row.get("매출일자"),
                "SCM실판매부수": 0,
                "SCM환산매출액": 0,
                "ERP출고부수": row.get("매출부수") or 0,
                "ERP매출액": row.get("매출금액") or 0,
                "ERP원출고부수": row.get("출고부수") or 0,
                "ERP원출고금액": row.get("출고금액") or 0,
                "ERP반품부수": row.get("반품부수") or 0,
                "ERP반품금액": row.get("반품금액") or 0,
            })
        detail["판매실적일별"] = erp_for_dashboard
        return detail

    wrapped._erp_daily_patched = True
    Database.fetch_post_launch_performance = wrapped
