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

        # 현재 성과 UI가 사용하는 판매실적 배열에는 ERP만 공급합니다.
        # SCM 실판매는 사용자가 연결을 요청할 때까지 빈 상태로 유지합니다.
        erp_for_dashboard = []
        for row in rows:
            ym = str(row.get("년월") or "").replace("/", "-")
            sale_date = f"{ym}-01" if len(ym) == 7 else ym
            erp_for_dashboard.append({
                "제품코드": product_code,
                "판매일": sale_date,
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

    wrapped._erp_monthly_patched = True
    Database.fetch_post_launch_performance = wrapped
