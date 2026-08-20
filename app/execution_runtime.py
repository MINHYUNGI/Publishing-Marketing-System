from __future__ import annotations

from datetime import datetime
from typing import Any

from .backend import Backend
from .database import Database


def _ui_category(value: str | None) -> str:
    if value == "기타 추가 마케팅":
        return "추가 마케팅"
    return value or "추가 마케팅"


def _db_category(value: str | None) -> str:
    if value == "추가 마케팅":
        return "기타 추가 마케팅"
    return value or "기타 추가 마케팅"


def install_execution_runtime() -> None:
    original_fetch = Database.fetch_post_launch_performance
    if getattr(original_fetch, "_execution_patched", False):
        return

    def fetch_execution_rows(self: Database, product_code: str) -> list[dict[str, Any]]:
        return (
            self.client.table("마케팅실행활동")
            .select("*")
            .eq("제품코드", product_code)
            .order("생성일시")
            .execute()
        ).data or []

    def save_execution_group(
        self: Database,
        product_code: str,
        activity_category: str,
        items: list[dict[str, Any]],
        registrar_id: str | None = None,
    ) -> dict[str, int]:
        if not product_code:
            raise ValueError("제품코드가 없습니다.")
        db_category = _db_category(activity_category)
        saved = added = cancelled = deleted = 0

        for item in items or []:
            execution_id = item.get("execution_activity_id") or None
            original_id = item.get("original_activity_id") or None
            if item.get("delete_added") and execution_id and not original_id:
                self.client.table("마케팅실행활동").delete().eq("실행활동ID", execution_id).eq("제품코드", product_code).execute()
                deleted += 1
                continue

            name = str(item.get("activity_name") or "").strip()
            if not name:
                raise ValueError("활동명을 입력해 주세요.")
            execution_type = item.get("execution_type") or ("활동추가" if not original_id else "실행확인")
            if execution_type not in {"실행확인", "활동추가", "활동취소"}:
                execution_type = "실행확인"

            row = {
                "제품코드": product_code,
                "원본활동ID": original_id,
                "활동분류": db_category,
                "채널또는매체": item.get("channel_or_media") or None,
                "활동명": name,
                "실제시작일": item.get("actual_start_date") or None,
                "실제종료일": item.get("actual_end_date") or None,
                "실제비용": int(item.get("actual_cost") or 0),
                "실행구분": execution_type,
                "실행내용": item.get("execution_note") or None,
                "등록자ID": registrar_id or None,
                "수정일시": datetime.now().isoformat(),
            }

            if original_id:
                response = self.client.table("마케팅실행활동").upsert(row, on_conflict="원본활동ID").execute()
            elif execution_id:
                response = self.client.table("마케팅실행활동").update(row).eq("실행활동ID", execution_id).eq("제품코드", product_code).execute()
            else:
                response = self.client.table("마케팅실행활동").insert(row).execute()
                added += 1
            if not (response.data or []):
                raise RuntimeError("실제 실행 데이터 저장에 실패했습니다.")
            saved += 1
            if execution_type == "활동취소":
                cancelled += 1

        return {"saved": saved, "added": added, "cancelled": cancelled, "deleted": deleted}

    def wrapped_fetch(self: Database, product_code: str):
        detail = original_fetch(self, product_code)
        if not detail:
            return detail
        execution_rows = fetch_execution_rows(self, product_code)
        by_original = {str(r.get("원본활동ID")): r for r in execution_rows if r.get("원본활동ID")}
        merged: list[dict[str, Any]] = []

        for plan in detail.get("마케팅활동") or []:
            item = dict(plan)
            ex = by_original.get(str(plan.get("활동ID")))
            item["계획시작일"] = plan.get("시작일")
            item["계획종료일"] = plan.get("종료일")
            item["계획비용"] = plan.get("비용")
            if ex:
                item["실행활동ID"] = ex.get("실행활동ID")
                item["실제시작일"] = ex.get("실제시작일")
                item["실제종료일"] = ex.get("실제종료일")
                item["실제비용"] = ex.get("실제비용")
                item["실행구분"] = ex.get("실행구분") or "실행확인"
                item["실행내용"] = ex.get("실행내용")
                item["실행확인여부"] = True
            else:
                # 화면 기본값은 기획값을 보여주되 DB에는 아직 실제 실행 레코드를 만들지 않습니다.
                item["실제시작일"] = plan.get("시작일")
                item["실제종료일"] = plan.get("종료일")
                item["실제비용"] = plan.get("비용")
                item["실행구분"] = "미확인"
                item["실행확인여부"] = False
            merged.append(item)

        for ex in execution_rows:
            if ex.get("원본활동ID"):
                continue
            merged.append({
                "활동ID": None,
                "실행활동ID": ex.get("실행활동ID"),
                "제품코드": product_code,
                "활동분류": _ui_category(ex.get("활동분류")),
                "채널또는매체": ex.get("채널또는매체"),
                "활동명": ex.get("활동명"),
                "시작일": ex.get("실제시작일"),
                "종료일": ex.get("실제종료일"),
                "비용": 0,
                "계획시작일": None,
                "계획종료일": None,
                "계획비용": 0,
                "실제시작일": ex.get("실제시작일"),
                "실제종료일": ex.get("실제종료일"),
                "실제비용": ex.get("실제비용"),
                "실행구분": "활동추가",
                "실행내용": ex.get("실행내용"),
                "실행확인여부": True,
                "계획실행구분": "실행",
            })

        detail["마케팅활동"] = merged
        detail["마케팅실행활동"] = execution_rows
        return detail

    wrapped_fetch._execution_patched = True
    Database.fetch_post_launch_performance = wrapped_fetch
    Database.fetch_execution_rows = fetch_execution_rows
    Database.save_execution_group = save_execution_group

    def save_marketing_execution_group(self: Backend, product_code: str, activity_category: str, items: list[dict[str, Any]], registrar_id: str | None = None) -> dict[str, Any]:
        try:
            if not self.db:
                raise RuntimeError("Supabase가 연결되지 않았습니다.")
            result = self.db.save_execution_group(product_code, activity_category, items or [], registrar_id)
            return {"ok": True, **result}
        except Exception as exc:
            return {"ok": False, "message": str(exc)}

    Backend.save_marketing_execution_group = save_marketing_execution_group
