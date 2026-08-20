from __future__ import annotations

from typing import Any

from .database import Database


def install_execution_sort_runtime() -> None:
    if not hasattr(Database, "save_execution_group"):
        return
    original_save = Database.save_execution_group
    original_fetch = Database.fetch_post_launch_performance
    if getattr(original_save, "_sort_order_patched", False):
        return

    def save_with_sort(self: Database, product_code: str, activity_category: str, items: list[dict[str, Any]], registrar_id: str | None = None):
        result = original_save(self, product_code, activity_category, items, registrar_id)
        db_category = "기타 추가 마케팅" if activity_category == "추가 마케팅" else activity_category
        for idx, item in enumerate(items or [], start=1):
            if item.get("delete_added"):
                continue
            order = int(item.get("sort_order") or idx * 10)
            execution_id = item.get("execution_activity_id") or None
            original_id = item.get("original_activity_id") or None
            if original_id:
                self.client.table("마케팅실행활동").update({"정렬순서": order}).eq("제품코드", product_code).eq("원본활동ID", original_id).execute()
            elif execution_id:
                self.client.table("마케팅실행활동").update({"정렬순서": order}).eq("제품코드", product_code).eq("실행활동ID", execution_id).execute()
            else:
                # 방금 추가된 계획외 활동은 동일 제품·분류·활동명 중 가장 최근 레코드에 순서를 기록합니다.
                rows = (self.client.table("마케팅실행활동")
                        .select("실행활동ID")
                        .eq("제품코드", product_code)
                        .eq("활동분류", db_category)
                        .eq("활동명", str(item.get("activity_name") or "").strip())
                        .is_("원본활동ID", "null")
                        .order("생성일시", desc=True)
                        .limit(1).execute()).data or []
                if rows:
                    self.client.table("마케팅실행활동").update({"정렬순서": order}).eq("실행활동ID", rows[0]["실행활동ID"]).execute()
        return result

    def fetch_with_sort(self: Database, product_code: str):
        detail = original_fetch(self, product_code)
        if not detail:
            return detail
        rows = detail.get("마케팅실행활동") or []
        by_original = {str(r.get("원본활동ID")): r for r in rows if r.get("원본활동ID")}
        by_execution = {str(r.get("실행활동ID")): r for r in rows if r.get("실행활동ID")}
        for idx, item in enumerate(detail.get("마케팅활동") or [], start=1):
            ex = None
            if item.get("활동ID"):
                ex = by_original.get(str(item.get("활동ID")))
            if not ex and item.get("실행활동ID"):
                ex = by_execution.get(str(item.get("실행활동ID")))
            item["실행정렬순서"] = int((ex or {}).get("정렬순서") or item.get("정렬순서") or idx * 10)
        return detail

    save_with_sort._sort_order_patched = True
    Database.save_execution_group = save_with_sort
    Database.fetch_post_launch_performance = fetch_with_sort
