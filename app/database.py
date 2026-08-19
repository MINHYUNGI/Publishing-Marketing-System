from __future__ import annotations
from typing import Any
from datetime import datetime
from supabase import create_client, Client

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



    def fetch_post_launch_performance(self, product_code: str) -> dict[str, Any] | None:
        """출간 후 성과 화면용 실제 Supabase 데이터를 통합 반환합니다."""
        detail = self.fetch_marketing_plan_detail(product_code)
        if not detail:
            return None

        sales_rows = (
            self.client.table("판매실적일별")
            .select("*")
            .eq("제품코드", product_code)
            .order("판매일")
            .execute()
        ).data or []

        content_rows = (
            self.client.table("콘텐츠성과")
            .select("*")
            .eq("제품코드", product_code)
            .order("게시일")
            .execute()
        ).data or []

        buyer_rows = (
            self.client.table("구매자반응")
            .select("*")
            .eq("제품코드", product_code)
            .order("기준일", desc=True)
            .limit(1)
            .execute()
        ).data or []

        evaluation_rows = (
            self.client.table("마케팅성과평가")
            .select("*")
            .eq("제품코드", product_code)
            .order("평가기준일", desc=True)
            .limit(1)
            .execute()
        ).data or []

        return {
            **detail,
            "판매실적일별": sales_rows,
            "콘텐츠성과": content_rows,
            "구매자반응": buyer_rows[0] if buyer_rows else None,
            "마케팅성과평가": evaluation_rows[0] if evaluation_rows else None,
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
