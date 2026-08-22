from __future__ import annotations
from typing import Any
from datetime import date, datetime, timedelta
from supabase import create_client, Client

from .content_metrics import platform_from_url, youtube_statistics

class Database:
    def __init__(self, project_url: str, secret_key: str) -> None:
        self.client: Client = create_client(project_url, secret_key)

    def fetch_users(self) -> list[dict[str, Any]]:
        response = (
            self.client.table("사용자")
            .select("사용자ID,이름,이메일,담당BU,담당채널")
            .eq("사용여부", True)
            .order("이름")
            .execute()
        )
        return response.data or []

    def fetch_product_index(self) -> list[dict[str, Any]]:
        """제품인덱스 전체를 Supabase에서 페이지 단위로 모두 가져옵니다.

        Supabase/PostgREST의 단일 조회 행 제한 때문에 한 번의 select()만
        사용하면 일부 제품만 로드될 수 있으므로 1,000건씩 반복 조회합니다.
        """
        page_size = 1000
        start = 0
        rows: list[dict[str, Any]] = []

        while True:
            response = (
                self.client.table("제품인덱스")
                .select("제품코드,품목,제품명,정가,최종대분류,최종중분류")
                .order("제품명")
                .range(start, start + page_size - 1)
                .execute()
            )
            batch = response.data or []
            rows.extend(batch)

            if len(batch) < page_size:
                break

            start += page_size

        return rows

    def marketing_product_codes(self) -> set[str]:
        rows = (
            self.client.table("마케팅대상제품")
            .select("제품코드")
            .execute()
        ).data or []
        return {r["제품코드"] for r in rows if r.get("제품코드")}

    def fetch_channel_marketing_activities(self) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], dict[str, dict[str, Any]]]:
        """Fetch activities, product metadata, SCM facts, and actual executions in batches."""
        rows: list[dict[str, Any]] = []
        page_size = 1000
        for start in range(0, 1000000, page_size):
            batch = (
                self.client.table("마케팅활동")
                .select("활동ID,제품코드,활동분류,채널또는매체,활동명,시작일,종료일,일정비고,비용,URL,비고,계획실행구분,수정일시")
                .order("시작일")
                .range(start, start + page_size - 1)
                .execute()
            ).data or []
            rows.extend(batch)
            if len(batch) < page_size:
                break

        codes = sorted({str(row.get("제품코드") or "") for row in rows if row.get("제품코드")})
        marketing_products: dict[str, dict[str, Any]] = {}
        channel_products: dict[str, dict[str, Any]] = {}
        for start in range(0, len(codes), 200):
            batch = (
                self.client.table("마케팅대상제품")
                .select("제품코드,출간일")
                .in_("제품코드", codes[start:start + 200])
                .execute()
            ).data or []
            marketing_products.update({str(row["제품코드"]): row for row in batch})
            product_batch = (
                self.client.table("제품인덱스")
                .select("제품코드,제품명,최종대분류,최종중분류")
                .in_("제품코드", codes[start:start + 200])
                .execute()
            ).data or []
            channel_products.update({str(row["제품코드"]): row for row in product_batch})
        scm_rows: list[dict[str, Any]] = []
        for offset in range(0, len(codes), 200):
            code_batch = codes[offset:offset + 200]
            start = 0
            while code_batch:
                batch = (
                    self.client.table("SCM일별실판매")
                    .select("제품코드,판매일,거래처코드,판매수량")
                    .in_("제품코드", code_batch)
                    .order("판매일")
                    .range(start, start + 999)
                    .execute()
                ).data or []
                scm_rows.extend(batch)
                if len(batch) < 1000:
                    break
                start += 1000
        execution_rows: list[dict[str, Any]] = []
        for offset in range(0, len(codes), 200):
            execution_rows.extend((
                self.client.table("마케팅실행활동")
                .select("원본활동ID,제품코드,실제비용")
                .in_("제품코드", codes[offset:offset + 200])
                .execute()
            ).data or [])
        return rows, marketing_products, scm_rows, execution_rows, channel_products

    def ensure_marketing_product(self, product_code: str) -> None:
        existing = (
            self.client.table("마케팅대상제품")
            .select("제품코드")
            .eq("제품코드", product_code)
            .limit(1)
            .execute()
        )
        if existing.data:
            return
        self.client.table("마케팅대상제품").insert({"제품코드": product_code}).execute()

    def upsert_marketing_plan(self, row: dict[str, Any]) -> dict[str, Any]:
        """제품코드 기준으로 마케팅 기획 전략정보를 저장/갱신합니다."""
        response = (
            self.client.table("마케팅기획")
            .upsert(row, on_conflict="제품코드")
            .execute()
        )
        return (response.data or [row])[0]

    def upsert_sales_goal(self, product_code: str, goal: dict[str, Any], registrar_id: str | None = None, document_id: str | None = None) -> dict[str, Any] | None:
        """마케팅 기획서에 담당자가 입력한 영업목표 원본값을 저장합니다."""
        if not goal or not any(v not in (None, "", []) for v in goal.values()):
            return None
        mapping = {
            "initial_units": "초도배본부수", "initial_sales": "초도배본매출액",
            "month3_units": "출간3개월부수", "month3_sales": "출간3개월매출액",
            "month6_units": "출간6개월부수", "month6_sales": "출간6개월매출액",
            "month12_units": "출간12개월부수", "month12_sales": "출간12개월매출액",
            "bep_units": "BEP부수", "bep_sales": "BEP매출액",
            "bep_target_month": "BEP초과목표개월", "bep_target_note": "BEP초과목표메모",
        }
        row = {"제품코드": product_code, "등록자ID": registrar_id, "원본문서ID": document_id}
        for src, dst in mapping.items():
            if src in goal:
                row[dst] = goal.get(src)
        response = self.client.table("영업목표").upsert(row, on_conflict="제품코드").execute()
        return (response.data or [row])[0]

    def fetch_sales_goal(self, product_code: str) -> dict[str, Any]:
        response = (self.client.table("영업목표")
                    .select("제품코드,초도배본부수,초도배본매출액,출간3개월부수,출간3개월매출액,출간6개월부수,출간6개월매출액,출간12개월부수,출간12개월매출액,BEP부수,BEP매출액,BEP초과목표개월,BEP초과목표메모")
                    .eq("제품코드", product_code).limit(1).execute())
        return (response.data or [{}])[0]

    def fetch_business_plan_goal(self, product_code: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        summary_response = (self.client.table("사업계획목표")
                            .select("사업계획연도,제품코드,제품명,계획정가,계획첫출고일,연간계획부수,연간계획매출액")
                            .eq("제품코드", product_code).order("사업계획연도", desc=True).limit(1).execute())
        summary = (summary_response.data or [{}])[0]
        if not summary.get("사업계획연도"):
            return {}, []
        monthly_response = (self.client.table("사업계획월별목표")
                            .select("사업계획연도,제품코드,매출월,계획부수,계획매출액")
                            .eq("제품코드", product_code)
                            .eq("사업계획연도", summary["사업계획연도"])
                            .order("매출월").execute())
        return summary, (monthly_response.data or [])

    def fetch_existing_plan(self, product_code: str) -> dict[str, Any] | None:
        plan_response = (
            self.client.table("마케팅기획")
            .select("기획ID,제품코드,타깃독자,핵심키워드,마케팅문구,마케팅전략,USP,원본문서ID,등록자ID,수정일시")
            .eq("제품코드", product_code)
            .limit(1)
            .execute()
        )
        plan = plan_response.data[0] if plan_response.data else None

        activity_response = (
            self.client.table("마케팅활동")
            .select("활동ID,제품코드,활동분류,채널또는매체,활동명,시작일,종료일,일정비고,비용,URL,비고,계획실행구분,등록자ID,원본문서명,원본문서ID,수정일시,정렬순서,실행상태,실제시작일,실제종료일,실제비용,성과메모")
            .eq("제품코드", product_code)
            .eq("계획실행구분", "계획")
            .order("생성일시")
            .execute()
        )
        activities = activity_response.data or []

        document = None
        document_id = plan.get("원본문서ID") if plan else None
        if not document_id and activities:
            document_id = next((a.get("원본문서ID") for a in activities if a.get("원본문서ID")), None)

        if document_id:
            doc_response = (
                self.client.table("문서")
                .select("문서ID,문서명,제품코드,파일경로,등록자ID,AI분석상태,등록일시,수정일시")
                .eq("문서ID", document_id)
                .limit(1)
                .execute()
            )
            document = doc_response.data[0] if doc_response.data else None

        if not plan and not activities and not document:
            return None

        return {
            "plan": plan,
            "activities": activities,
            "document": document,
        }

    def update_existing_plan(
        self,
        product_code: str,
        strategy: dict[str, Any],
        activities: list[dict[str, Any]],
        registrar_id: str | None,
        document_id: str | None,
        sales_targets: dict[str, Any] | None = None,
    ) -> dict[str, int]:
        # 전략정보 저장
        plan_row = {
            "제품코드": product_code,
            "타깃독자": strategy.get("target_readers"),
            "핵심키워드": strategy.get("core_keywords") or [],
            "마케팅문구": strategy.get("marketing_message"),
            "마케팅전략": strategy.get("marketing_strategy"),
            "USP": strategy.get("usp"),
            "원본문서ID": document_id,
            "등록자ID": registrar_id,
        }
        self.upsert_marketing_plan(plan_row)
        self.upsert_sales_goal(product_code, sales_targets or {}, registrar_id, document_id)

        existing_response = (
            self.client.table("마케팅활동")
            .select("활동ID")
            .eq("제품코드", product_code)
            .eq("계획실행구분", "계획")
            .execute()
        )
        existing_ids = {r["활동ID"] for r in (existing_response.data or []) if r.get("활동ID")}
        keep_ids: set[str] = set()
        inserted = 0
        updated = 0

        for item in activities:
            if not item.get("selected", True):
                continue

            activity_id = item.get("activity_id")
            row = {
                "제품코드": product_code,
                "활동분류": item["activity_category"],
                "채널또는매체": item.get("channel_or_media"),
                "활동명": item["activity_name"],
                "시작일": item.get("start_date") or None,
                "종료일": item.get("end_date") or None,
                "일정비고": item.get("schedule_note"),
                "비용": item.get("cost"),
                "URL": item.get("url"),
                "비고": item.get("note"),
                "계획실행구분": item.get("plan_execution_type") or "계획",
                "등록자ID": registrar_id,
                "등록방식": item.get("registration_method") or "AI",
                "원본문서ID": document_id,
            }

            if activity_id and activity_id in existing_ids:
                (
                    self.client.table("마케팅활동")
                    .update(row)
                    .eq("활동ID", activity_id)
                    .execute()
                )
                keep_ids.add(activity_id)
                updated += 1
            else:
                response = self.client.table("마케팅활동").insert(row).execute()
                created = (response.data or [{}])[0]
                if created.get("활동ID"):
                    keep_ids.add(created["활동ID"])
                inserted += 1

        # 화면에서 체크 해제된 기존 활동은 삭제하여 화면과 DB를 동일하게 맞춤
        delete_ids = existing_ids - keep_ids
        for activity_id in delete_ids:
            (
                self.client.table("마케팅활동")
                .delete()
                .eq("활동ID", activity_id)
                .execute()
            )

        return {
            "updated": updated,
            "inserted": inserted,
            "deleted": len(delete_ids),
        }


    def fetch_marketing_plan_list(self) -> list[dict[str, Any]]:
        """마케팅 기획이 등록된 제품 목록과 활동 요약을 반환합니다."""
        plans = (
            self.client.table("마케팅기획")
            .select("제품코드,수정일시")
            .order("수정일시", desc=True)
            .execute()
        ).data or []
        if not plans:
            return []

        product_codes = [r.get("제품코드") for r in plans if r.get("제품코드")]
        marketing_products = (
            self.client.table("마케팅대상제품")
            .select("제품코드,저자명,출간일,담당편집자,마케팅PM명")
            .in_("제품코드", product_codes)
            .execute()
        ).data or []
        mp_map = {r.get("제품코드"): r for r in marketing_products}

        product_rows = (
            self.client.table("제품인덱스")
            .select("제품코드,제품명,정가,최종대분류,최종중분류")
            .in_("제품코드", product_codes)
            .execute()
        ).data or []
        pi_map = {r.get("제품코드"): r for r in product_rows}

        activity_rows = (
            self.client.table("마케팅활동")
            .select("제품코드,비용")
            .in_("제품코드", product_codes)
            .eq("계획실행구분", "계획")
            .execute()
        ).data or []
        activity_summary: dict[str, dict[str, int]] = {}
        for row in activity_rows:
            code = row.get("제품코드")
            if not code:
                continue
            summary = activity_summary.setdefault(code, {"count": 0, "cost": 0})
            summary["count"] += 1
            summary["cost"] += int(row.get("비용") or 0)

        result = []
        for plan in plans:
            code = plan.get("제품코드")
            if not code:
                continue
            mp = mp_map.get(code, {})
            pi = pi_map.get(code, {})
            summary = activity_summary.get(code, {"count": 0, "cost": 0})
            result.append({
                "제품코드": code,
                "제품명": pi.get("제품명") or code,
                "정가": pi.get("정가"),
                "대분류": pi.get("최종대분류"),
                "중분류": pi.get("최종중분류"),
                "저자명": mp.get("저자명"),
                "출간일": mp.get("출간일"),
                "개발PM": mp.get("담당편집자"),
                "마케팅PM": mp.get("마케팅PM명"),
                "활동수": summary["count"],
                "총비용": summary["cost"],
                "수정일시": plan.get("수정일시"),
            })
        return result

    def update_marketing_plan_strategy(self, product_code: str, payload: dict[str, Any]) -> dict[str, Any]:
        """상세 화면에서 마케팅 전략 5개 항목을 즉시 수정합니다."""
        if not product_code:
            raise ValueError("제품코드가 없습니다.")

        field_map = {
            "target_readers": "타깃독자",
            "core_keywords": "핵심키워드",
            "marketing_message": "마케팅문구",
            "usp": "USP",
            "marketing_strategy": "마케팅전략",
        }
        row: dict[str, Any] = {}
        for src, dst in field_map.items():
            if src in payload:
                value = payload.get(src)
                if src == "core_keywords":
                    if isinstance(value, str):
                        value = [x.strip().lstrip("#") for x in value.replace(",", " ").split() if x.strip().lstrip("#")]
                    elif isinstance(value, list):
                        value = [str(x).strip().lstrip("#") for x in value if str(x).strip().lstrip("#")]
                    else:
                        value = []
                elif isinstance(value, str):
                    value = value.strip() or None
                row[dst] = value

        if not row:
            raise ValueError("수정할 마케팅 전략 정보가 없습니다.")

        response = (
            self.client.table("마케팅기획")
            .update(row)
            .eq("제품코드", product_code)
            .execute()
        )
        if not response.data:
            raise RuntimeError("수정할 마케팅 기획을 찾지 못했습니다.")
        return response.data[0]


    def fetch_marketing_plan_detail(self, product_code: str) -> dict[str, Any] | None:
        """상세 대시보드용 기본정보·전략·계획 활동을 반환합니다."""
        existing = self.fetch_existing_plan(product_code)
        if not existing:
            return None

        mp_response = (
            self.client.table("마케팅대상제품")
            .select("제품코드,저자명,출간일,담당편집자,마케팅PM명")
            .eq("제품코드", product_code)
            .limit(1)
            .execute()
        )
        mp = mp_response.data[0] if mp_response.data else {}

        pi_response = (
            self.client.table("제품인덱스")
            .select("제품코드,제품명,정가,최종대분류,최종중분류")
            .eq("제품코드", product_code)
            .limit(1)
            .execute()
        )
        pi = pi_response.data[0] if pi_response.data else {}

        business_goal, business_monthly = self.fetch_business_plan_goal(product_code)
        sales_goal = self.fetch_sales_goal(product_code)

        activities = []
        for row in existing.get("activities") or []:
            item = dict(row)
            if item.get("활동분류") == "기타 추가 마케팅":
                item["활동분류"] = "추가 마케팅"
            activities.append(item)

        return {
            "기본정보": {
                "제품코드": product_code,
                "도서명": pi.get("제품명") or product_code,
                "저자명": mp.get("저자명"),
                "정가": pi.get("정가"),
                "대분류": pi.get("최종대분류"),
                "중분류": pi.get("최종중분류"),
                "출간일": mp.get("출간일"),
                "개발PM": mp.get("담당편집자"),
                "마케팅PM": mp.get("마케팅PM명"),
            },
            "마케팅기획": existing.get("plan") or {},
            "마케팅활동": activities,
            "사업계획목표": business_goal,
            "사업계획월별목표": business_monthly,
            "영업목표": sales_goal,
        }



    @staticmethod
    def _execution_db_category(value: str | None) -> str:
        if value == "추가 마케팅":
            return "기타 추가 마케팅"
        return value or "기타 추가 마케팅"

    @staticmethod
    def _execution_ui_category(value: str | None) -> str:
        if value == "기타 추가 마케팅":
            return "추가 마케팅"
        return value or "추가 마케팅"

    def fetch_execution_rows(self, product_code: str) -> list[dict[str, Any]]:
        return (
            self.client.table("마케팅실행활동")
            .select("*")
            .eq("제품코드", product_code)
            .order("생성일시")
            .execute()
        ).data or []

    def _find_execution_id(
        self,
        product_code: str,
        activity_category: str,
        item: dict[str, Any],
    ) -> str | None:
        if item.get("execution_activity_id"):
            return str(item["execution_activity_id"])
        original_id = item.get("original_activity_id")
        if original_id:
            rows = (
                self.client.table("마케팅실행활동")
                .select("실행활동ID")
                .eq("제품코드", product_code)
                .eq("원본활동ID", original_id)
                .limit(1)
                .execute()
            ).data or []
            return str(rows[0]["실행활동ID"]) if rows else None
        rows = (
            self.client.table("마케팅실행활동")
            .select("실행활동ID")
            .eq("제품코드", product_code)
            .eq("활동분류", self._execution_db_category(activity_category))
            .eq("활동명", str(item.get("activity_name") or "").strip())
            .is_("원본활동ID", "null")
            .order("생성일시", desc=True)
            .limit(1)
            .execute()
        ).data or []
        return str(rows[0]["실행활동ID"]) if rows else None

    def _save_execution_order(
        self,
        product_code: str,
        activity_category: str,
        items: list[dict[str, Any]],
    ) -> None:
        db_category = self._execution_db_category(activity_category)
        for index, item in enumerate(items or [], start=1):
            if item.get("delete_added"):
                continue
            order = int(item.get("sort_order") or index * 10)
            execution_id = item.get("execution_activity_id") or None
            original_id = item.get("original_activity_id") or None
            query = self.client.table("마케팅실행활동").update({"정렬순서": order}).eq("제품코드", product_code)
            if original_id:
                query.eq("원본활동ID", original_id).execute()
            elif execution_id:
                query.eq("실행활동ID", execution_id).execute()
            else:
                rows = (
                    self.client.table("마케팅실행활동")
                    .select("실행활동ID")
                    .eq("제품코드", product_code)
                    .eq("활동분류", db_category)
                    .eq("활동명", str(item.get("activity_name") or "").strip())
                    .is_("원본활동ID", "null")
                    .order("생성일시", desc=True)
                    .limit(1)
                    .execute()
                ).data or []
                if rows:
                    (
                        self.client.table("마케팅실행활동")
                        .update({"정렬순서": order})
                        .eq("실행활동ID", rows[0]["실행활동ID"])
                        .execute()
                    )

    def _save_execution_links(
        self,
        product_code: str,
        activity_category: str,
        items: list[dict[str, Any]],
    ) -> tuple[int, int]:
        if "SNS" not in activity_category and "바이럴" not in activity_category:
            return 0, 0
        youtube_prompted = False
        youtube_collected = 0
        youtube_failed = 0
        for item in items or []:
            if item.get("delete_added"):
                continue
            original_id = item.get("original_activity_id") or None
            execution_id = self._find_execution_id(product_code, activity_category, item)
            delete_query = (
                self.client.table("콘텐츠성과")
                .delete()
                .eq("제품코드", product_code)
                .eq("원천구분", "실행링크")
            )
            if original_id:
                delete_query.eq("활동ID", original_id).execute()
            elif execution_id:
                delete_query.eq("실행활동ID", execution_id).execute()
            else:
                continue
            if item.get("execution_type") == "활동취소":
                continue
            for index, raw_url in enumerate(item.get("links") or [], start=1):
                url = str(raw_url or "").strip()
                if not url:
                    continue
                if not url.lower().startswith(("http://", "https://")):
                    url = "https://" + url
                platform = platform_from_url(url)
                row = {
                    "제품코드": product_code,
                    "활동ID": original_id,
                    "실행활동ID": execution_id,
                    "플랫폼": platform,
                    "채널명": item.get("channel_or_media") or None,
                    "콘텐츠명": str(item.get("activity_name") or "SNS·바이럴 콘텐츠").strip(),
                    "게시일": item.get("actual_start_date") or None,
                    "URL": url,
                    "지표수집일": date.today().isoformat(),
                    "원천구분": "실행링크",
                    "링크순서": index * 10,
                }
                if platform == "YouTube":
                    try:
                        metrics = youtube_statistics(url, prompt_if_missing=not youtube_prompted)
                        youtube_prompted = True
                        if metrics:
                            row.update({key: value for key, value in metrics.items() if value is not None})
                            youtube_collected += 1
                        else:
                            youtube_failed += 1
                    except Exception as exc:
                        youtube_prompted = True
                        youtube_failed += 1
                        row["비고"] = f"YouTube 지표 수집 실패: {exc}"
                self.client.table("콘텐츠성과").insert(row).execute()
        return youtube_collected, youtube_failed

    def save_execution_group(
        self,
        product_code: str,
        activity_category: str,
        items: list[dict[str, Any]],
        registrar_id: str | None = None,
    ) -> dict[str, int]:
        if not product_code:
            raise ValueError("제품코드가 없습니다.")
        db_category = self._execution_db_category(activity_category)
        saved = added = cancelled = deleted = 0
        for item in items or []:
            execution_id = item.get("execution_activity_id") or None
            original_id = item.get("original_activity_id") or None
            if item.get("delete_added") and execution_id and not original_id:
                (
                    self.client.table("마케팅실행활동")
                    .delete()
                    .eq("실행활동ID", execution_id)
                    .eq("제품코드", product_code)
                    .execute()
                )
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
                response = (
                    self.client.table("마케팅실행활동")
                    .update(row)
                    .eq("실행활동ID", execution_id)
                    .eq("제품코드", product_code)
                    .execute()
                )
            else:
                response = self.client.table("마케팅실행활동").insert(row).execute()
                added += 1
            if not (response.data or []):
                raise RuntimeError("실제 실행 데이터 저장에 실패했습니다.")
            saved += 1
            if execution_type == "활동취소":
                cancelled += 1
        self._save_execution_order(product_code, activity_category, items)
        youtube_collected, youtube_failed = self._save_execution_links(product_code, activity_category, items)
        return {
            "saved": saved,
            "added": added,
            "cancelled": cancelled,
            "deleted": deleted,
            "youtube_collected": youtube_collected,
            "youtube_failed": youtube_failed,
        }

    def _merge_execution_rows(
        self,
        detail: dict[str, Any],
        product_code: str,
        execution_rows: list[dict[str, Any]],
    ) -> None:
        by_original = {str(row.get("원본활동ID")): row for row in execution_rows if row.get("원본활동ID")}
        merged: list[dict[str, Any]] = []
        for plan in detail.get("마케팅활동") or []:
            item = dict(plan)
            execution = by_original.get(str(plan.get("활동ID")))
            item["계획시작일"] = plan.get("시작일")
            item["계획종료일"] = plan.get("종료일")
            item["계획비용"] = plan.get("비용")
            if execution:
                item.update({
                    "실행활동ID": execution.get("실행활동ID"),
                    "실제시작일": execution.get("실제시작일"),
                    "실제종료일": execution.get("실제종료일"),
                    "실제비용": execution.get("실제비용"),
                    "실행구분": execution.get("실행구분") or "실행확인",
                    "실행내용": execution.get("실행내용"),
                    "실행확인여부": True,
                })
            else:
                item.update({
                    "실제시작일": plan.get("시작일"),
                    "실제종료일": plan.get("종료일"),
                    "실제비용": plan.get("비용"),
                    "실행구분": "미확인",
                    "실행확인여부": False,
                })
            merged.append(item)
        for execution in execution_rows:
            if execution.get("원본활동ID"):
                continue
            merged.append({
                "활동ID": None,
                "실행활동ID": execution.get("실행활동ID"),
                "제품코드": product_code,
                "활동분류": self._execution_ui_category(execution.get("활동분류")),
                "채널또는매체": execution.get("채널또는매체"),
                "활동명": execution.get("활동명"),
                "시작일": execution.get("실제시작일"),
                "종료일": execution.get("실제종료일"),
                "비용": 0,
                "계획시작일": None,
                "계획종료일": None,
                "계획비용": 0,
                "실제시작일": execution.get("실제시작일"),
                "실제종료일": execution.get("실제종료일"),
                "실제비용": execution.get("실제비용"),
                "실행구분": "활동추가",
                "실행내용": execution.get("실행내용"),
                "실행확인여부": True,
                "계획실행구분": "실행",
            })
        by_execution = {str(row.get("실행활동ID")): row for row in execution_rows if row.get("실행활동ID")}
        for index, item in enumerate(merged, start=1):
            execution = None
            if item.get("활동ID"):
                execution = by_original.get(str(item.get("활동ID")))
            if not execution and item.get("실행활동ID"):
                execution = by_execution.get(str(item.get("실행활동ID")))
            item["실행정렬순서"] = int((execution or {}).get("정렬순서") or item.get("정렬순서") or index * 10)
        detail["마케팅활동"] = merged
        detail["마케팅실행활동"] = execution_rows

    def _refresh_youtube_rows(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        from .security import get_youtube_api_key

        if not get_youtube_api_key(prompt_if_missing=False):
            return rows
        for row in rows:
            if row.get("원천구분") != "실행링크" or row.get("플랫폼") != "YouTube" or not row.get("URL"):
                continue
            try:
                metrics = youtube_statistics(str(row["URL"]), prompt_if_missing=False)
                if not metrics:
                    continue
                updates = {key: value for key, value in metrics.items() if value is not None}
                changed = any(row.get(key) != value for key, value in updates.items())
                row.update(updates)
                row["지표수집일"] = date.today().isoformat()
                if changed or not row.get("조회수"):
                    (
                        self.client.table("콘텐츠성과")
                        .update({**updates, "지표수집일": date.today().isoformat(), "비고": None})
                        .eq("콘텐츠성과ID", row["콘텐츠성과ID"])
                        .execute()
                    )
            except Exception:
                continue
        return rows

    def _attach_content_links(self, detail: dict[str, Any], rows: list[dict[str, Any]]) -> None:
        by_plan: dict[str, list[dict[str, Any]]] = {}
        by_execution: dict[str, list[dict[str, Any]]] = {}
        for row in rows:
            if row.get("원천구분") != "실행링크":
                continue
            if row.get("활동ID"):
                by_plan.setdefault(str(row["활동ID"]), []).append(row)
            if row.get("실행활동ID"):
                by_execution.setdefault(str(row["실행활동ID"]), []).append(row)
        for item in detail.get("마케팅활동") or []:
            links = by_plan.get(str(item.get("활동ID")), []) if item.get("활동ID") else []
            if not links and item.get("실행활동ID"):
                links = by_execution.get(str(item["실행활동ID"]), [])
            item["콘텐츠링크"] = links

    def _fetch_scm_rows(
        self,
        product_code: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        start = 0
        while True:
            query = self.client.table("SCM일별실판매").select(
                "판매일,거래처코드,ISBN13,제품코드,판매수량,원본파일명,원본시트"
            )
            if product_code:
                query = query.eq("제품코드", product_code)
            if date_from:
                query = query.gte("판매일", date_from)
            if date_to:
                query = query.lte("판매일", date_to)
            batch = query.order("판매일").range(start, start + 999).execute().data or []
            rows.extend(batch)
            if len(batch) < 1000:
                return rows
            start += 1000

    def fetch_scm_sync_status(self) -> dict[str, Any]:
        history = self.client.table("SCM동기화이력").select("*").order("시작일시", desc=True).limit(1).execute().data or []
        latest = history[0] if history else None
        clients = []
        if latest:
            clients = self.client.table("SCM동기화거래처결과").select("*").eq("동기화ID", latest["동기화ID"]).execute().data or []
        unmatched = self.client.table("SCM제품매핑").select("ISBN13,SCM상품명,최초확인일,최종확인일").is_("제품코드", "null").order("SCM상품명").execute().data or []
        return {"latest": latest, "clients": clients, "unmatched": unmatched}

    def fetch_scm_dashboard_data(self, options: dict[str, Any] | None = None) -> dict[str, Any]:
        options = options or {}
        earliest_rows = self.client.table("SCM일별실판매").select("판매일").order("판매일").limit(1).execute().data or []
        latest_rows = self.client.table("SCM일별실판매").select("판매일").order("판매일", desc=True).limit(1).execute().data or []
        available_date_min = str(earliest_rows[0]["판매일"]) if earliest_rows else ""
        available_date_max = str(latest_rows[0]["판매일"]) if latest_rows else ""
        requested_from = str(options.get("date_from") or "")
        requested_to = str(options.get("date_to") or "")
        date_to = requested_to or available_date_max
        date_from = requested_from
        if not date_from and date_to:
            date_from = (date.fromisoformat(date_to) - timedelta(days=45)).isoformat()
        facts = self._fetch_scm_rows(date_from=date_from or None, date_to=date_to or None)
        mappings: list[dict[str, Any]] = []
        start = 0
        while True:
            batch = self.client.table("SCM제품매핑").select("ISBN13,제품코드,SCM상품명,출판일자,매칭상태").range(start, start + 999).execute().data or []
            mappings.extend(batch)
            if len(batch) < 1000:
                break
            start += 1000
        mapping_by_isbn = {str(row.get("ISBN13")): row for row in mappings}
        products = {str(row.get("제품코드")): row for row in self.fetch_product_index() if row.get("제품코드")}
        client_names = {"KYOBO": "교보문고", "YPBOOKS": "영풍문고", "YES24": "예스24", "ALADIN": "알라딘"}
        first_sales: dict[str, str] = {}
        dashboard_rows = []
        for fact in facts:
            isbn = str(fact.get("ISBN13") or "")
            mapping = mapping_by_isbn.get(isbn, {})
            code = str(fact.get("제품코드") or mapping.get("제품코드") or "")
            product = products.get(code, {})
            name = product.get("제품명") or mapping.get("SCM상품명") or isbn
            main, middle = product.get("최종대분류") or "", product.get("최종중분류") or ""
            division = "아동" if any(token in f"{main} {middle}" for token in ("아동", "만화", "01.")) else "성인"
            sale_date = str(fact.get("판매일") or "")
            if code and sale_date and (code not in first_sales or sale_date < first_sales[code]):
                first_sales[code] = sale_date
            dashboard_rows.append([sale_date, division, main, middle, code, name, isbn, client_names.get(str(fact.get("거래처코드")), ""), "실판매", fact.get("판매수량") or 0])
        dashboard_products = []
        for code in sorted({str(row[4]) for row in dashboard_rows if row[4]}):
            product = products.get(code, {})
            product_mappings = [row for row in mappings if str(row.get("제품코드") or "") == code]
            publication_dates = sorted(str(row.get("출판일자")) for row in product_mappings if row.get("출판일자"))
            first_date = (publication_dates[0] if publication_dates else "") or first_sales.get(code, "")
            dashboard_products.append({"code": code, "name": product.get("제품명") or next((row.get("SCM상품명") for row in product_mappings if row.get("SCM상품명")), code), "firstDate": first_date, "firstShipDate": first_date, "ageForceOld": not bool(publication_dates), "baseDateSource": "출판일자" if publication_dates else "출판일자없음", "mainCat": product.get("최종대분류") or "", "midCat": product.get("최종중분류") or ""})
        dates = sorted({row[0] for row in dashboard_rows if row[0]})
        marketing_rows = self.client.table("마케팅활동").select("활동ID,제품코드,활동분류,채널또는매체,활동명,시작일,종료일,계획실행구분").execute().data or []
        marketing_records = []
        for row in marketing_rows:
            code = str(row.get("제품코드") or "")
            marketing_records.append({"id": row.get("활동ID"), "type": "viral" if any(token in str(row.get("활동분류") or "") for token in ("SNS", "바이럴")) else "store", "name": row.get("활동명") or row.get("채널또는매체") or "마케팅 활동", "start": row.get("시작일"), "end": row.get("종료일") or row.get("시작일"), "books": [{"code": code, "itemCode": code, "title": products.get(code, {}).get("제품명") or code}]})
        return {"generatedAt": datetime.now().isoformat(), "generatedDate": date.today().isoformat(), "source": "Supabase SCM일별실판매", "rowCount": len(dashboard_rows), "dateMin": dates[0] if dates else "", "dateMax": dates[-1] if dates else "", "availableDateMin": available_date_min, "availableDateMax": available_date_max, "loadedDateFrom": date_from, "loadedDateTo": date_to, "clients": sorted(set(client_names.values())), "products": dashboard_products, "rows": dashboard_rows, "marketingRecords": marketing_records}

    def fetch_yes24_buyer_demographics(self, product_code: str) -> list[dict[str, Any]]:
        snapshots = self.client.table("YES24구매자스냅샷").select("스냅샷ID,기준일,기간시작일,기간종료일,계정구분,ISBN13,제품코드,YES24상품번호,상품명,총판매수량,원본파일명").eq("제품코드", product_code).order("기준일").execute().data or []
        by_id = {row["스냅샷ID"]: row for row in snapshots}
        for row in snapshots:
            row["분포"] = {"성별": [], "연령": [], "지역": []}
        ids = list(by_id)
        for offset in range(0, len(ids), 200):
            distributions = self.client.table("YES24구매자분포").select("스냅샷ID,분포유형,구간값,수량,정렬순서").in_("스냅샷ID", ids[offset:offset + 200]).order("정렬순서").execute().data or []
            for item in distributions:
                if item.get("스냅샷ID") in by_id:
                    by_id[item["스냅샷ID"]]["분포"][item["분포유형"]].append({"구간": item["구간값"], "수량": item.get("수량") or 0})
        return snapshots

    def fetch_post_launch_performance(self, product_code: str) -> dict[str, Any] | None:
        """출간 후 성과 화면에 필요한 계획, 실행, 콘텐츠, ERP 데이터를 반환합니다."""
        detail = self.fetch_marketing_plan_detail(product_code)
        if not detail:
            return None
        buyer_rows = (
            self.client.table("구매자반응").select("*").eq("제품코드", product_code)
            .order("기준일", desc=True).limit(1).execute()
        ).data or []
        evaluation_rows = (
            self.client.table("마케팅성과평가").select("*").eq("제품코드", product_code)
            .order("평가기준일", desc=True).limit(1).execute()
        ).data or []
        erp_rows = (
            self.client.table("ERP일별판매실적")
            .select("제품코드,제품명,매출일자,매출부수,매출금액,출고부수,출고금액,반품부수,반품금액,원본파일명")
            .eq("제품코드", product_code).order("매출일자").execute()
        ).data or []
        by_date: dict[str, dict[str, Any]] = {}
        client_fields = {"KYOBO": "SCM교보부수", "YPBOOKS": "SCM영풍부수", "YES24": "SCMYES24부수", "ALADIN": "SCM알라딘부수"}
        for row in self._fetch_scm_rows(product_code):
            sale_date = str(row.get("판매일") or "")
            item = by_date.setdefault(sale_date, {"제품코드": product_code, "판매일": sale_date, "SCM실판매부수": 0, "SCM환산매출액": 0, "SCM교보부수": 0, "SCM영풍부수": 0, "SCMYES24부수": 0, "SCM알라딘부수": 0, "ERP출고부수": 0, "ERP매출액": 0, "ERP원출고부수": 0, "ERP원출고금액": 0, "ERP반품부수": 0, "ERP반품금액": 0})
            quantity = row.get("판매수량") or 0
            item["SCM실판매부수"] += quantity
            field = client_fields.get(str(row.get("거래처코드")))
            if field:
                item[field] += quantity
        for row in erp_rows:
            sale_date = str(row.get("매출일자") or "")
            item = by_date.setdefault(sale_date, {"제품코드": product_code, "판매일": sale_date, "SCM실판매부수": 0, "SCM환산매출액": 0, "SCM교보부수": 0, "SCM영풍부수": 0, "SCMYES24부수": 0, "SCM알라딘부수": 0})
            item.update({"ERP출고부수": row.get("매출부수") or 0, "ERP매출액": row.get("매출금액") or 0, "ERP원출고부수": row.get("출고부수") or 0, "ERP원출고금액": row.get("출고금액") or 0, "ERP반품부수": row.get("반품부수") or 0, "ERP반품금액": row.get("반품금액") or 0})
        sales_rows = [by_date[key] for key in sorted(by_date)]
        execution_rows = self.fetch_execution_rows(product_code)
        self._merge_execution_rows(detail, product_code, execution_rows)
        content_rows = (
            self.client.table("콘텐츠성과")
            .select("콘텐츠성과ID,제품코드,활동ID,실행활동ID,플랫폼,채널명,콘텐츠명,게시일,URL,조회수,좋아요수,댓글수,공유수,저장수,클릭수,지표수집일,원천구분,비고,링크순서")
            .eq("제품코드", product_code).order("링크순서").order("생성일시").execute()
        ).data or []
        content_rows = self._refresh_youtube_rows(content_rows)
        self._attach_content_links(detail, content_rows)
        return {
            **detail,
            "판매실적일별": sales_rows,
            "ERP일별판매실적": erp_rows,
            "콘텐츠성과": content_rows,
            "구매자반응": buyer_rows[0] if buyer_rows else None,
            "YES24구매자분포": self.fetch_yes24_buyer_demographics(product_code),
            "마케팅성과평가": evaluation_rows[0] if evaluation_rows else None,
            "대표표지": self.fetch_cover_reference(product_code),
        }

    def upsert_marketing_performance_evaluation(self, product_code: str, payload: dict[str, Any]) -> dict[str, Any]:
        """PM 성과평가를 제품코드+평가기준일 기준으로 저장합니다."""
        if not product_code:
            raise ValueError("제품코드가 없습니다.")
        review_date = payload.get("review_date") or datetime.now().date().isoformat()
        row = {
            "제품코드": product_code,
            "평가기준일": review_date,
            "PM자체평가": payload.get("pm_rating") or None,
            "성과코멘트": payload.get("performance_comment") or None,
            "잘된점": payload.get("strengths") or None,
            "개선보완필요": payload.get("improvements") or None,
            "다음액션플랜": payload.get("next_action") or None,
            "다음리뷰일": payload.get("next_review_date") or None,
            "수정일시": datetime.now().isoformat(),
        }
        response = (
            self.client.table("마케팅성과평가")
            .upsert(row, on_conflict="제품코드,평가기준일")
            .execute()
        )
        data = response.data or []
        if not data:
            raise RuntimeError("성과평가 저장에 실패했습니다.")
        return data[0]



    @staticmethod
    def _db_activity_category(value: str | None) -> str:
        """UI 표시명 '추가 마케팅'을 DB 제약조건 값으로 정규화합니다."""
        if value == "추가 마케팅":
            return "기타 추가 마케팅"
        return value or "기타 추가 마케팅"

    def _next_activity_sort_order(self, product_code: str, activity_category: str, start_date: str | None) -> int:
        query = (
            self.client.table("마케팅활동")
            .select("정렬순서")
            .eq("제품코드", product_code)
            .eq("활동분류", self._db_activity_category(activity_category))
            .eq("계획실행구분", "계획")
        )
        if start_date:
            query = query.eq("시작일", start_date)
        else:
            query = query.is_("시작일", "null")
        rows = query.order("정렬순서", desc=True).limit(1).execute().data or []
        return int((rows[0].get("정렬순서") if rows else 0) or 0) + 10

    def reorder_marketing_activities(self, product_code: str, activity_category: str, start_date: str | None, ordered_ids: list[str]) -> int:
        """동일 제품·분류·시작일 활동의 사용자 지정 우선순위를 저장합니다."""
        if not product_code or not ordered_ids:
            raise ValueError("정렬할 활동 정보가 없습니다.")
        db_category = self._db_activity_category(activity_category)
        response = (
            self.client.table("마케팅활동")
            .select("활동ID,제품코드,활동분류,시작일")
            .in_("활동ID", ordered_ids)
            .execute()
        )
        rows = response.data or []
        if len(rows) != len(set(ordered_ids)):
            raise ValueError("일부 마케팅 활동을 찾지 못했습니다.")
        normalized_start = start_date or None
        for row in rows:
            if row.get("제품코드") != product_code or row.get("활동분류") != db_category or (row.get("시작일") or None) != normalized_start:
                raise ValueError("같은 분류·같은 시작일의 활동끼리만 순서를 변경할 수 있습니다.")
        for index, activity_id in enumerate(ordered_ids, start=1):
            self.client.table("마케팅활동").update({"정렬순서": index * 10, "수정일시": datetime.now().isoformat()}).eq("활동ID", activity_id).execute()
        return len(ordered_ids)

    def update_marketing_activity(self, activity_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        """상세 시계열 화면에서 활동 1건을 즉시 수정합니다."""
        if not activity_id:
            raise ValueError("활동ID가 없습니다.")
        current_response = self.client.table("마케팅활동").select("제품코드,활동분류,시작일,정렬순서").eq("활동ID", activity_id).limit(1).execute()
        current = current_response.data[0] if current_response.data else None
        if not current:
            raise RuntimeError("수정할 마케팅 활동을 찾지 못했습니다.")
        new_category = self._db_activity_category(payload.get("activity_category"))
        new_start = payload.get("start_date") or None
        bucket_changed = current.get("활동분류") != new_category or (current.get("시작일") or None) != new_start
        sort_order = self._next_activity_sort_order(current.get("제품코드"), payload.get("activity_category") or "추가 마케팅", new_start) if bucket_changed else int(current.get("정렬순서") or 1000)
        row = {
            "활동분류": new_category,
            "채널또는매체": payload.get("channel_or_media") or None,
            "활동명": (payload.get("activity_name") or "").strip(),
            "시작일": payload.get("start_date") or None,
            "종료일": payload.get("end_date") or None,
            "일정비고": payload.get("schedule_note") or None,
            "비용": int(payload.get("cost") or 0),
            "URL": payload.get("url") or None,
            "비고": payload.get("note") or None,
            "정렬순서": sort_order,
            "수정일시": datetime.now().isoformat(),
        }
        if not row["활동명"]:
            raise ValueError("활동명을 입력해 주세요.")
        response = (
            self.client.table("마케팅활동")
            .update(row)
            .eq("활동ID", activity_id)
            .execute()
        )
        data = response.data or []
        if not data:
            raise RuntimeError("수정할 마케팅 활동을 찾지 못했습니다.")
        if "actual_cost" in payload:
            execution = {
                "제품코드": current.get("제품코드"),
                "원본활동ID": activity_id,
                "활동분류": new_category,
                "채널또는매체": row.get("채널또는매체"),
                "활동명": row.get("활동명"),
                "실제시작일": row.get("시작일"),
                "실제종료일": row.get("종료일"),
                "실제비용": int(payload.get("actual_cost") or 0),
                "실행구분": "실행확인",
                "수정일시": datetime.now().isoformat(),
            }
            self.client.table("마케팅실행활동").upsert(
                execution, on_conflict="원본활동ID"
            ).execute()
            data[0]["실제비용"] = execution["실제비용"]
        return data[0]

    def create_marketing_activity(self, product_code: str, payload: dict[str, Any]) -> dict[str, Any]:
        """상세 시계열 화면에서 신규 계획 활동 1건을 즉시 추가합니다."""
        if not product_code:
            raise ValueError("제품코드가 없습니다.")
        activity_name = (payload.get("activity_name") or "").strip()
        if not activity_name:
            raise ValueError("활동명을 입력해 주세요.")
        sort_order = self._next_activity_sort_order(product_code, payload.get("activity_category") or "추가 마케팅", payload.get("start_date") or None)
        row = {
            "제품코드": product_code,
            "활동분류": self._db_activity_category(payload.get("activity_category")),
            "채널또는매체": payload.get("channel_or_media") or None,
            "활동명": activity_name,
            "시작일": payload.get("start_date") or None,
            "종료일": payload.get("end_date") or None,
            "일정비고": payload.get("schedule_note") or None,
            "비용": int(payload.get("cost") or 0),
            "URL": payload.get("url") or None,
            "비고": payload.get("note") or None,
            "계획실행구분": "계획",
            "등록방식": "PM",
            "정렬순서": sort_order,
        }
        response = self.client.table("마케팅활동").insert(row).execute()
        data = response.data or []
        if not data:
            raise RuntimeError("마케팅 활동 추가에 실패했습니다.")
        return data[0]

    def delete_marketing_activity(self, activity_id: str) -> bool:
        """활동 이미지 FK를 정리한 뒤 활동 1건을 삭제합니다."""
        if not activity_id:
            raise ValueError("활동ID가 없습니다.")
        self.client.table("마케팅활동이미지").delete().eq("활동ID", activity_id).execute()
        response = self.client.table("마케팅활동").delete().eq("활동ID", activity_id).execute()
        return bool(response.data)

    def find_document_by_hash(self, file_hash: str) -> dict[str, Any] | None:
        response = (
            self.client.table("문서")
            .select("문서ID,문서명,제품코드,파일경로,등록일시")
            .eq("파일해시", file_hash)
            .limit(1)
            .execute()
        )
        return response.data[0] if response.data else None



    def fetch_reference_files(self, product_code: str) -> list[dict[str, Any]]:
        response = (
            self.client.table("마케팅참조파일")
            .select("파일ID,제품코드,활동ID,파일분류,원본파일명,저장파일명,파일경로,파일형식,파일크기,설명,등록자ID,생성일시,수정일시")
            .eq("제품코드", product_code)
            .order("생성일시", desc=True)
            .execute()
        )
        return response.data or []

    def fetch_reference_file(self, file_id: str) -> dict[str, Any] | None:
        response = (
            self.client.table("마케팅참조파일")
            .select("파일ID,제품코드,활동ID,파일분류,원본파일명,저장파일명,파일경로,파일형식,파일크기,설명,등록자ID,생성일시,수정일시")
            .eq("파일ID", file_id)
            .limit(1)
            .execute()
        )
        return response.data[0] if response.data else None

    def fetch_cover_reference(self, product_code: str) -> dict[str, Any] | None:
        response = (
            self.client.table("마케팅참조파일")
            .select("파일ID,제품코드,활동ID,파일분류,원본파일명,저장파일명,파일경로,파일형식,파일크기,설명,등록자ID,생성일시,수정일시")
            .eq("제품코드", product_code)
            .eq("파일분류", "도서표지")
            .order("생성일시", desc=True)
            .limit(1)
            .execute()
        )
        return response.data[0] if response.data else None

    def mark_reference_as_cover(self, product_code: str, file_id: str) -> None:
        now = datetime.now().isoformat()
        (
            self.client.table("마케팅참조파일")
            .update({"파일분류": "참조이미지", "수정일시": now})
            .eq("제품코드", product_code)
            .eq("파일분류", "도서표지")
            .neq("파일ID", file_id)
            .execute()
        )
        (
            self.client.table("마케팅참조파일")
            .update({"파일분류": "도서표지", "수정일시": now})
            .eq("파일ID", file_id)
            .execute()
        )

    def create_reference_file(self, row: dict[str, Any]) -> dict[str, Any]:
        response = self.client.table("마케팅참조파일").insert(row).execute()
        data = response.data or []
        if not data:
            raise RuntimeError("참조파일 DB 등록에 실패했습니다.")
        return data[0]

    def update_reference_file(self, file_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        row = {
            "파일분류": payload.get("file_category") or "참조파일",
            "활동ID": payload.get("activity_id") or None,
            "설명": payload.get("description") or None,
            "수정일시": datetime.now().isoformat(),
        }
        response = self.client.table("마케팅참조파일").update(row).eq("파일ID", file_id).execute()
        data = response.data or []
        if not data:
            raise RuntimeError("수정할 참조파일을 찾지 못했습니다.")
        return data[0]

    def delete_reference_file(self, file_id: str) -> dict[str, Any] | None:
        existing = self.fetch_reference_file(file_id)
        if not existing:
            return None
        self.client.table("마케팅참조파일").delete().eq("파일ID", file_id).execute()
        return existing

    def delete_marketing_plan(self, product_code: str) -> dict[str, int]:
        """마케팅 기획과 연결된 계획 활동/문서 등록정보를 삭제합니다.

        마케팅대상제품 및 제품인덱스는 보존합니다. 실제 파일 시스템의
        원본/복사 문서 파일도 안전을 위해 삭제하지 않습니다.
        """
        # 활동 이미지가 활동ID를 FK로 참조하므로 먼저 삭제
        activity_rows = (
            self.client.table("마케팅활동")
            .select("활동ID")
            .eq("제품코드", product_code)
            .execute()
        ).data or []
        activity_ids = [r.get("활동ID") for r in activity_rows if r.get("활동ID")]

        deleted_images = 0
        if activity_ids:
            image_response = (
                self.client.table("마케팅활동이미지")
                .delete()
                .in_("활동ID", activity_ids)
                .execute()
            )
            deleted_images = len(image_response.data or [])

        activity_response = (
            self.client.table("마케팅활동")
            .delete()
            .eq("제품코드", product_code)
            .execute()
        )
        deleted_activities = len(activity_response.data or [])

        plan_response = (
            self.client.table("마케팅기획")
            .delete()
            .eq("제품코드", product_code)
            .execute()
        )
        deleted_plans = len(plan_response.data or [])

        # 마케팅기획/활동이 문서를 더 이상 참조하지 않는 상태에서 문서 등록정보 삭제
        document_response = (
            self.client.table("문서")
            .delete()
            .eq("제품코드", product_code)
            .execute()
        )
        deleted_documents = len(document_response.data or [])

        return {
            "deleted_images": deleted_images,
            "deleted_activities": deleted_activities,
            "deleted_plans": deleted_plans,
            "deleted_documents": deleted_documents,
        }

    def insert_document(self, row: dict[str, Any]) -> dict[str, Any]:
        response = self.client.table("문서").insert(row).execute()
        return (response.data or [row])[0]

    def insert_activities(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not rows:
            return []
        response = self.client.table("마케팅활동").insert(rows).execute()
        return response.data or rows

    def update_document(self, document_id: str, values: dict[str, Any]) -> None:
        self.client.table("문서").update(values).eq("문서ID", document_id).execute()
