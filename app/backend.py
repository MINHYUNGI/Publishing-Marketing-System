from __future__ import annotations
import logging
import base64
import mimetypes
import os
import subprocess
import sys
import threading
import time
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
import webview

from .analyzer import analyze_document
from .config import ALLOWED_EXTENSIONS, MAX_FILE_SIZE, PROJECT_URL, ATTACHMENT_ROOT
from .database import Database
from .erp_import import choose_and_import_erp
from .scm_import import preview_scm_sync, sync_scm_ledger
from .scm_collection import get_scm_collection_status, plan_scm_collection, start_scm_collection, submit_scm_collection_input
from .scm_credentials import public_settings, save_account, save_recipient, delete_recipient
from .channel_activity import build_bookstore_timeline_rows
from .file_store import copy_document, copy_reference_file, save_reference_bytes
from .security import get_openai_api_key, get_supabase_secret_key, sha256_file

class Backend:
    def __init__(self) -> None:
        self.db: Database | None = None
        self.users: list[dict[str, Any]] = []
        self.product_index: list[dict[str, Any]] = []

    def import_erp_daily_excel(self, product_code: str | None = None) -> dict[str, Any]:
        return choose_and_import_erp(self, product_code)

    def import_erp_monthly_excel(self) -> dict[str, Any]:
        return choose_and_import_erp(self, None)

    def preview_scm_daily_sales(self) -> dict[str, Any]:
        try:
            return preview_scm_sync()
        except Exception as exc:
            logging.exception("SCM 실판매 원장 사전검증 실패")
            return {"ok": False, "message": str(exc)}

    def sync_scm_daily_sales(self) -> dict[str, Any]:
        try:
            return sync_scm_ledger(self)
        except Exception as exc:
            logging.exception("SCM 실판매 동기화 실패")
            return {"ok": False, "message": str(exc)}

    def preview_scm_collection(self, options: dict[str, Any] | None = None) -> dict[str, Any]:
        try:
            return {"ok": True, **plan_scm_collection(self, options)}
        except Exception as exc:
            logging.exception("SCM 직접 수집 계획 조회 실패")
            return {"ok": False, "message": str(exc)}

    def start_scm_collection(self, options: dict[str, Any] | None = None) -> dict[str, Any]:
        try:
            return start_scm_collection(self, options)
        except Exception as exc:
            logging.exception("SCM 직접 수집 시작 실패")
            return {"ok": False, "message": str(exc)}

    def get_scm_collection_status(self, job_id: str) -> dict[str, Any]:
        try:
            return get_scm_collection_status(job_id)
        except Exception as exc:
            logging.exception("SCM 직접 수집 상태 조회 실패")
            return {"ok": False, "message": str(exc)}

    def get_scm_credentials(self) -> dict[str, Any]:
        try: return public_settings()
        except Exception as exc: return {"ok": False, "message": str(exc)}

    def save_scm_credential(self, payload: dict[str, Any]) -> dict[str, Any]:
        try: return save_account(payload.get("key", ""), payload.get("login_id", ""), payload.get("password", ""), payload.get("url", ""))
        except Exception as exc: return {"ok": False, "message": str(exc)}

    def save_yes24_recipient(self, payload: dict[str, Any]) -> dict[str, Any]:
        try: return save_recipient(payload.get("name", ""), payload.get("phone", ""), payload.get("id", ""))
        except Exception as exc: return {"ok": False, "message": str(exc)}

    def delete_yes24_recipient(self, recipient_id: str) -> dict[str, Any]:
        try: return delete_recipient(recipient_id)
        except Exception as exc: return {"ok": False, "message": str(exc)}

    def submit_scm_collection_input(self, job_id: str, request_id: str, value: str) -> dict[str, Any]:
        try: return submit_scm_collection_input(job_id, request_id, value)
        except Exception as exc: return {"ok": False, "message": str(exc)}

    def get_scm_sync_status(self) -> dict[str, Any]:
        try:
            if not self.db:
                raise RuntimeError("Supabase가 연결되지 않았습니다.")
            return {"ok": True, **self.db.fetch_scm_sync_status()}
        except Exception as exc:
            logging.exception("SCM 동기화 상태 조회 실패")
            return {"ok": False, "message": str(exc)}

    def get_scm_dashboard_data(self, options: dict[str, Any] | None = None) -> dict[str, Any]:
        try:
            if not self.db:
                raise RuntimeError("Supabase가 연결되지 않았습니다.")
            return {"ok": True, **self.db.fetch_scm_dashboard_data(options)}
        except Exception as exc:
            logging.exception("SCM 실판매 대시보드 조회 실패")
            return {"ok": False, "message": str(exc)}

    def get_major_bookstore_marketing_activities(self) -> dict[str, Any]:
        try:
            if not self.db:
                raise RuntimeError("Supabase가 연결되지 않았습니다.")
            activities, marketing_products, scm_rows, execution_rows = self.db.fetch_channel_marketing_activities()
            product_map = {str(row.get("제품코드") or ""): row for row in self.product_index}
            bookstores = build_bookstore_timeline_rows(activities, product_map, marketing_products)
            client_store = {"KYOBO": "교보문고", "YPBOOKS": "영풍문고", "YES24": "YES24", "ALADIN": "알라딘"}
            sales_by_key: dict[tuple[str, str], list[tuple[str, int]]] = {}
            for sale in scm_rows:
                key = (str(sale.get("제품코드") or ""), client_store.get(str(sale.get("거래처코드") or ""), ""))
                if key[0] and key[1]:
                    sales_by_key.setdefault(key, []).append((str(sale.get("판매일") or ""), int(sale.get("판매수량") or 0)))
            for store, rows in bookstores.items():
                for row in rows:
                    start = str(row.get("시작일") or row.get("종료일") or "")
                    end = str(row.get("종료일") or row.get("시작일") or "")
                    row["실판매부수"] = sum(
                        quantity for sale_date, quantity in sales_by_key.get((str(row.get("제품코드") or ""), store), [])
                        if start and end and start <= sale_date <= end
                    )
            actual_cost_by_activity = {
                str(row.get("원본활동ID")): int(row.get("실제비용") or 0)
                for row in execution_rows if row.get("원본활동ID")
            }
            for rows in bookstores.values():
                for row in rows:
                    row["실제집행비용"] = actual_cost_by_activity.get(str(row.get("활동ID") or ""), 0)
            dates = sorted({str(row.get(key)) for rows in bookstores.values() for row in rows for key in ("시작일", "종료일") if row.get(key)})
            products = sorted(
                ({"제품코드": code, "제품명": row.get("제품명") or code} for code, row in product_map.items() if any(str(item.get("제품코드") or "") == code for items in bookstores.values() for item in items)),
                key=lambda row: str(row["제품명"]),
            )
            return {"ok": True, "bookstores": bookstores, "products": products, "date_from": dates[0] if dates else None, "date_to": dates[-1] if dates else None}
        except Exception as exc:
            logging.exception("주요 4개 서점 마케팅 활동 조회 실패")
            return {"ok": False, "message": str(exc)}

    def open_external_url(self, url: str) -> dict[str, Any]:
        """등록된 콘텐츠 URL을 운영체제의 기본 브라우저에서 엽니다."""
        value = str(url or "").strip()
        try:
            parsed = urlparse(value)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                raise ValueError("올바른 웹 링크가 아닙니다.")
            logging.info("외부 링크 열기 요청: %s", value)
            if os.name == "nt":
                os.startfile(value)  # type: ignore[attr-defined]
            elif not webbrowser.open(value, new=2, autoraise=True):
                raise RuntimeError("기본 브라우저를 열 수 없습니다.")
            return {"ok": True}
        except Exception as exc:
            logging.exception("외부 링크 열기 실패")
            return {"ok": False, "message": str(exc)}

    def restart_latest_version(self) -> dict[str, Any]:
        """새 창이 실제로 표시된 뒤에만 현재 프로그램을 종료합니다."""
        try:
            root = Path(__file__).resolve().parent.parent
            restart_script = root / "restart_latest.ps1"
            if not restart_script.exists():
                raise RuntimeError("restart_latest.ps1을 찾을 수 없습니다.")
            flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            process = subprocess.Popen(
                [
                    "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
                    "-File", str(restart_script), "-ProjectDir", str(root),
                ],
                cwd=str(root),
                creationflags=flags,
            )
            logging.info("최신 버전 재시작 helper 실행: pid=%s", process.pid)

            def finish_restart() -> None:
                code = process.wait()
                if code == 0:
                    logging.info("새 프로그램 창 표시 확인 완료. 기존 프로그램을 종료합니다.")
                    time.sleep(1.0)
                    os._exit(0)
                logging.error("최신 버전 재시작 helper 실패: exit=%s. 기존 프로그램을 유지합니다.", code)

            threading.Thread(target=finish_restart, daemon=True).start()
            return {"ok": True, "message": "최신 버전을 확인하고 다시 시작하고 있습니다."}
        except Exception as exc:
            logging.exception("최신 버전 재시작 실패")
            return {"ok": False, "message": str(exc)}

    def save_marketing_execution_group(
        self,
        product_code: str,
        activity_category: str,
        items: list[dict[str, Any]],
        registrar_id: str | None = None,
    ) -> dict[str, Any]:
        try:
            if not self.db:
                raise RuntimeError("Supabase가 연결되지 않았습니다.")
            result = self.db.save_execution_group(
                product_code,
                activity_category,
                items or [],
                registrar_id,
            )
            return {"ok": True, **result}
        except Exception as exc:
            logging.exception("마케팅 실행활동 저장 실패")
            return {"ok": False, "message": str(exc)}

    def initialize(self) -> dict[str, Any]:
        try:
            secret = get_supabase_secret_key()
            self.db = Database(PROJECT_URL, secret)
            self.users = self.db.fetch_users()
            self.product_index = self.db.fetch_product_index()
            marketing_codes = self.db.marketing_product_codes()

            products = []
            for p in self.product_index:
                row = dict(p)
                row["마케팅대상등록"] = p.get("제품코드") in marketing_codes
                products.append(row)

            return {"ok": True, "users": self.users, "products": products}
        except Exception as exc:
            logging.exception("초기화 실패")
            return {"ok": False, "message": str(exc)}

    def load_existing_plan(self, product_code: str) -> dict[str, Any]:
        try:
            if not self.db:
                raise RuntimeError("Supabase가 연결되지 않았습니다.")

            product_map = {
                p["제품코드"]: p
                for p in self.product_index
                if p.get("제품코드")
            }
            product = product_map.get(product_code)
            if not product:
                return {"ok": False, "message": "제품인덱스에서 해당 제품을 찾을 수 없습니다."}

            existing = self.db.fetch_existing_plan(product_code)
            if not existing:
                return {"ok": False, "message": "등록된 마케팅 기획이 없습니다."}

            plan = existing.get("plan") or {}
            document = existing.get("document") or {}
            activities = []

            for a in existing.get("activities") or []:
                activities.append({
                    "activity_id": a.get("활동ID"),
                    "activity_category": a.get("활동분류") or "기타 추가 마케팅",
                    "channel_or_media": a.get("채널또는매체"),
                    "activity_name": a.get("활동명") or "",
                    "start_date": a.get("시작일"),
                    "end_date": a.get("종료일"),
                    "schedule_note": a.get("일정비고"),
                    "cost": a.get("비용"),
                    "url": a.get("URL"),
                    "note": a.get("비고"),
                    "plan_execution_type": a.get("계획실행구분") or "계획",
                    "registration_method": a.get("등록방식") or "AI",
                    "confidence": 1.0,
                    "needs_review": False,
                    "selected": True,
                })

            original_registrar_id = (
                plan.get("등록자ID")
                or document.get("등록자ID")
                or next((a.get("등록자ID") for a in (existing.get("activities") or []) if a.get("등록자ID")), None)
            )

            sales_goal = self.db.fetch_sales_goal(product_code)
            result = {
                "file_path": document.get("파일경로") or "",
                "file_name": document.get("문서명") or f"{product.get('제품명')} 기존 마케팅 기획",
                "document_id": document.get("문서ID"),
                "registrar_id": original_registrar_id,
                "existing_mode": True,
                "analysis": {
                    "matched": True,
                    "product_code": product_code,
                    "product_name": product.get("제품명"),
                    "product_confidence": 1.0,
                    "product_reason": "기존 등록 기획 불러오기",
                    "product_evidence": "Supabase 기존 데이터",
                    "strategy": {
                        "target_readers": plan.get("타깃독자"),
                        "core_keywords": plan.get("핵심키워드") or [],
                        "marketing_message": plan.get("마케팅문구"),
                        "marketing_strategy": plan.get("마케팅전략"),
                        "usp": plan.get("USP"),
                        "confidence": 1.0,
                        "evidence": "기존 저장 데이터",
                    },
                    "activities": activities,
                    "sales_targets": {
                        "initial_units": sales_goal.get("초도배본부수"),
                        "initial_sales": sales_goal.get("초도배본매출액"),
                        "month3_units": sales_goal.get("출간3개월부수"),
                        "month3_sales": sales_goal.get("출간3개월매출액"),
                        "month6_units": sales_goal.get("출간6개월부수"),
                        "month6_sales": sales_goal.get("출간6개월매출액"),
                        "month12_units": sales_goal.get("출간12개월부수"),
                        "month12_sales": sales_goal.get("출간12개월매출액"),
                        "bep_units": sales_goal.get("BEP부수"),
                        "bep_sales": sales_goal.get("BEP매출액"),
                        "bep_target_month": sales_goal.get("BEP초과목표개월"),
                        "bep_target_note": sales_goal.get("BEP초과목표메모"),
                    },
                    "review_notes": [],
                },
            }
            return {"ok": True, "result": result}
        except Exception as exc:
            logging.exception("기존 기획 불러오기 실패")
            return {"ok": False, "message": str(exc)}

    def save_existing_plan(self, document: dict[str, Any], registrar_id: str) -> dict[str, Any]:
        try:
            if not self.db:
                raise RuntimeError("Supabase가 연결되지 않았습니다.")

            analysis = document.get("analysis") or {}
            product_code = analysis.get("product_code")
            if not product_code:
                raise RuntimeError("제품코드가 없습니다.")

            strategy = analysis.get("strategy") or {}
            activities = analysis.get("activities") or []
            sales_targets = analysis.get("sales_targets") or {}
            document_id = document.get("document_id")

            result = self.db.update_existing_plan(
                product_code=product_code,
                strategy=strategy,
                activities=activities,
                registrar_id=registrar_id or None,
                document_id=document_id,
                sales_targets=sales_targets,
            )
            return {"ok": True, **result}
        except Exception as exc:
            logging.exception("기존 기획 수정 저장 실패")
            return {"ok": False, "message": str(exc)}


    def get_marketing_plan_list(self) -> dict[str, Any]:
        try:
            if not self.db:
                raise RuntimeError("Supabase가 연결되지 않았습니다.")
            return {"ok": True, "plans": self.db.fetch_marketing_plan_list()}
        except Exception as exc:
            logging.exception("마케팅 기획 목록 조회 실패")
            return {"ok": False, "message": str(exc)}

    def get_marketing_plan_detail(self, product_code: str) -> dict[str, Any]:
        try:
            if not self.db:
                raise RuntimeError("Supabase가 연결되지 않았습니다.")
            detail = self.db.fetch_marketing_plan_detail(product_code)
            if not detail:
                return {"ok": False, "message": "등록된 마케팅 기획이 없습니다."}
            return {"ok": True, "detail": detail}
        except Exception as exc:
            logging.exception("마케팅 기획 상세 조회 실패")
            return {"ok": False, "message": str(exc)}



    def get_post_launch_performance(self, product_code: str) -> dict[str, Any]:
        try:
            if not self.db:
                raise RuntimeError("Supabase가 연결되지 않았습니다.")
            detail = self.db.fetch_post_launch_performance(product_code)
            if not detail:
                return {"ok": False, "message": "등록된 마케팅 기획이 없습니다."}
            return {"ok": True, "detail": detail}
        except Exception as exc:
            logging.exception("출간 후 성과 조회 실패")
            return {"ok": False, "message": str(exc)}

    def save_marketing_performance_evaluation(self, product_code: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            if not self.db:
                raise RuntimeError("Supabase가 연결되지 않았습니다.")
            row = self.db.upsert_marketing_performance_evaluation(product_code, payload or {})
            return {"ok": True, "evaluation": row}
        except Exception as exc:
            logging.exception("마케팅 성과평가 저장 실패")
            return {"ok": False, "message": str(exc)}



    def update_marketing_plan_strategy(self, product_code: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            if not self.db:
                raise RuntimeError("Supabase가 연결되지 않았습니다.")
            row = self.db.update_marketing_plan_strategy(product_code, payload or {})
            return {"ok": True, "plan": row}
        except Exception as exc:
            logging.exception("마케팅 전략 수정 실패")
            return {"ok": False, "message": str(exc)}


    def delete_marketing_plan(self, product_code: str) -> dict[str, Any]:
        try:
            if not self.db:
                raise RuntimeError("Supabase가 연결되지 않았습니다.")
            if not product_code:
                raise RuntimeError("제품코드가 없습니다.")
            result = self.db.delete_marketing_plan(product_code)
            return {"ok": True, **result}
        except Exception as exc:
            logging.exception("마케팅 기획 삭제 실패")
            return {"ok": False, "message": str(exc)}


    def update_marketing_activity(self, activity_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            if not self.db:
                raise RuntimeError("Supabase가 연결되지 않았습니다.")
            row = self.db.update_marketing_activity(activity_id, payload or {})
            return {"ok": True, "activity": row}
        except Exception as exc:
            logging.exception("마케팅 활동 수정 실패")
            return {"ok": False, "message": str(exc)}

    def create_marketing_activity(self, product_code: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            if not self.db:
                raise RuntimeError("Supabase가 연결되지 않았습니다.")
            row = self.db.create_marketing_activity(product_code, payload or {})
            return {"ok": True, "activity": row}
        except Exception as exc:
            logging.exception("마케팅 활동 추가 실패")
            return {"ok": False, "message": str(exc)}

    def delete_marketing_activity(self, activity_id: str) -> dict[str, Any]:
        try:
            if not self.db:
                raise RuntimeError("Supabase가 연결되지 않았습니다.")
            deleted = self.db.delete_marketing_activity(activity_id)
            if not deleted:
                return {"ok": False, "message": "삭제할 마케팅 활동을 찾지 못했습니다."}
            return {"ok": True}
        except Exception as exc:
            logging.exception("마케팅 활동 삭제 실패")
            return {"ok": False, "message": str(exc)}


    def reorder_marketing_activities(self, product_code: str, activity_category: str, start_date: str | None, ordered_ids: list[str]) -> dict[str, Any]:
        try:
            if not self.db:
                raise RuntimeError("Supabase가 연결되지 않았습니다.")
            count = self.db.reorder_marketing_activities(product_code, activity_category, start_date, ordered_ids or [])
            return {"ok": True, "count": count}
        except Exception as exc:
            logging.exception("마케팅 활동 우선순위 저장 실패")
            return {"ok": False, "message": str(exc)}


    def select_reference_files(self) -> dict[str, Any]:
        try:
            result = webview.windows[0].create_file_dialog(
                webview.FileDialog.OPEN,
                allow_multiple=True,
                file_types=(
                    "참조 파일 (*.jpg;*.jpeg;*.jfif;*.png;*.webp;*.gif;*.bmp;*.pdf;*.docx;*.xlsx;*.pptx)",
                    "이미지 (*.jpg;*.jpeg;*.jfif;*.png;*.webp;*.gif;*.bmp)",
                    "PDF (*.pdf)",
                    "모든 파일 (*.*)",
                ),
            )
            allowed = {".jpg",".jpeg", ".jfif",".png",".webp",".gif",".bmp",".pdf",".docx",".xlsx",".pptx"}
            files = []
            for raw in list(result or []):
                path = Path(raw)
                if not path.exists() or path.suffix.lower() not in allowed:
                    continue
                if path.stat().st_size > MAX_FILE_SIZE:
                    continue
                files.append({"path": str(path), "name": path.name, "size": path.stat().st_size, "extension": path.suffix.lower().lstrip(".")})
            return {"ok": True, "files": files}
        except Exception as exc:
            logging.exception("참조파일 선택 실패")
            return {"ok": False, "message": str(exc)}

    def select_and_save_cover_image(self, product_code: str, registrar_id: str | None = None) -> dict[str, Any]:
        try:
            if not product_code:
                raise ValueError("제품코드가 없습니다.")
            result = webview.windows[0].create_file_dialog(
                webview.FileDialog.OPEN,
                allow_multiple=False,
                file_types=(
                    "표지 이미지 (*.jpg;*.jpeg;*.jfif;*.png;*.webp)",
                    "모든 파일 (*.*)",
                ),
            )
            selected = list(result or [])
            if not selected:
                return {"ok": True, "cancelled": True}
            source = Path(selected[0])
            allowed = {".jpg", ".jpeg", ".jfif", ".png", ".webp"}
            if not source.exists() or source.suffix.lower() not in allowed:
                raise ValueError("JPG, JPEG, JFIF, PNG, WebP 이미지만 표지로 등록할 수 있습니다.")
            if source.stat().st_size > MAX_FILE_SIZE:
                raise ValueError("파일 크기가 50MB를 초과합니다.")
            saved = self.add_reference_files(
                product_code,
                [{
                    "path": str(source),
                    "name": source.name,
                    "size": source.stat().st_size,
                    "extension": source.suffix.lower().lstrip("."),
                }],
                "도서표지",
                "출간 후 성과 대표 표지",
                None,
                registrar_id,
            )
            if not saved.get("ok"):
                return saved
            cover = (saved.get("files") or [None])[-1]
            thumbnail = self.get_reference_thumbnail(str(cover.get("파일ID"))) if cover else {"thumbnail": None}
            return {
                "ok": True,
                "cancelled": False,
                "file": cover,
                "thumbnail": thumbnail.get("thumbnail"),
            }
        except Exception as exc:
            logging.exception("대표 표지 등록 실패")
            return {"ok": False, "message": str(exc)}

    def get_reference_files(self, product_code: str) -> dict[str, Any]:
        try:
            if not self.db:
                raise RuntimeError("Supabase가 연결되지 않았습니다.")
            return {"ok": True, "files": self.db.fetch_reference_files(product_code)}
        except Exception as exc:
            logging.exception("참조파일 목록 조회 실패")
            return {"ok": False, "message": str(exc)}

    def add_reference_files(self, product_code: str, files: list[dict[str, Any]], file_category: str = "참조파일", description: str | None = None, activity_id: str | None = None, registrar_id: str | None = None) -> dict[str, Any]:
        try:
            if not self.db:
                raise RuntimeError("Supabase가 연결되지 않았습니다.")
            if not product_code:
                raise ValueError("제품코드가 없습니다.")
            self.db.ensure_marketing_product(product_code)
            registered = []
            allowed = {".jpg",".jpeg",".jfif",".png",".webp",".gif",".bmp",".pdf",".docx",".xlsx",".pptx"}
            for item in files or []:
                raw_path = item.get("path") or ""
                source = Path(raw_path) if raw_path else None
                original_name = str(item.get("name") or (source.name if source else "reference_file"))
                suffix = Path(original_name).suffix.lower()
                if suffix not in allowed:
                    raise ValueError(f"지원하지 않는 파일 형식입니다: {suffix or original_name}")
                if source and source.exists():
                    if source.stat().st_size > MAX_FILE_SIZE:
                        raise ValueError(f"파일 크기가 너무 큽니다: {source.name}")
                    destination = copy_reference_file(source, product_code)
                    file_size = source.stat().st_size
                else:
                    encoded = item.get("data_base64") or ""
                    if not encoded:
                        raise FileNotFoundError(f"파일 데이터를 찾을 수 없습니다: {original_name}")
                    if "," in encoded and encoded.lstrip().startswith("data:"):
                        encoded = encoded.split(",", 1)[1]
                    data = base64.b64decode(encoded)
                    if len(data) > MAX_FILE_SIZE:
                        raise ValueError(f"파일 크기가 너무 큽니다: {original_name}")
                    destination = save_reference_bytes(data, original_name, product_code)
                    file_size = len(data)
                try:
                    row = self.db.create_reference_file({
                        "제품코드": product_code,
                        "활동ID": activity_id or None,
                        "파일분류": file_category or "참조파일",
                        "원본파일명": original_name,
                        "저장파일명": destination.name,
                        "파일경로": str(destination),
                        "파일형식": suffix.lstrip("."),
                        "파일크기": file_size,
                        "설명": description or None,
                        "등록자ID": registrar_id or None,
                    })
                    if file_category == "도서표지":
                        try:
                            self.db.mark_reference_as_cover(product_code, str(row.get("파일ID")))
                        except Exception:
                            self.db.delete_reference_file(str(row.get("파일ID")))
                            raise
                    registered.append(row)
                except Exception:
                    try:
                        destination.unlink(missing_ok=True)
                    except Exception:
                        pass
                    raise
            return {"ok": True, "files": registered, "count": len(registered), "storage_root": str(ATTACHMENT_ROOT / str(product_code))}
        except Exception as exc:
            logging.exception("참조파일 등록 실패")
            return {"ok": False, "message": str(exc)}

    def get_reference_thumbnail(self, file_id: str) -> dict[str, Any]:
        try:
            if not self.db:
                raise RuntimeError("Supabase가 연결되지 않았습니다.")
            row = self.db.fetch_reference_file(file_id)
            if not row:
                return {"ok": False, "message": "참조파일 정보를 찾지 못했습니다."}
            ext = str(row.get("파일형식") or "").lower()
            if ext not in {"jpg","jpeg","jfif","png","webp","gif","bmp"}:
                return {"ok": True, "thumbnail": None}
            path = Path(row.get("파일경로") or "")
            if not path.exists():
                return {"ok": False, "message": "이미지 파일을 찾지 못했습니다."}
            mime = "image/jpeg" if ext in {"jpg","jpeg","jfif"} else (mimetypes.guess_type(path.name)[0] or f"image/{ext}")
            data = base64.b64encode(path.read_bytes()).decode("ascii")
            return {"ok": True, "thumbnail": f"data:{mime};base64,{data}"}
        except Exception as exc:
            logging.exception("참조파일 썸네일 생성 실패")
            return {"ok": False, "message": str(exc)}

    def update_reference_file(self, file_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            if not self.db:
                raise RuntimeError("Supabase가 연결되지 않았습니다.")
            row = self.db.update_reference_file(file_id, payload or {})
            return {"ok": True, "file": row}
        except Exception as exc:
            logging.exception("참조파일 정보 수정 실패")
            return {"ok": False, "message": str(exc)}

    def open_reference_file(self, file_id: str) -> dict[str, Any]:
        try:
            if not self.db:
                raise RuntimeError("Supabase가 연결되지 않았습니다.")
            row = self.db.fetch_reference_file(file_id)
            if not row:
                raise FileNotFoundError("참조파일 DB 정보를 찾지 못했습니다.")
            path = Path(row.get("파일경로") or "")
            if not path.exists():
                raise FileNotFoundError(f"Y드라이브 파일을 찾지 못했습니다: {path}")
            if hasattr(os, "startfile"):
                os.startfile(str(path))
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(path)])
            else:
                subprocess.Popen(["xdg-open", str(path)])
            return {"ok": True}
        except Exception as exc:
            logging.exception("참조파일 열기 실패")
            return {"ok": False, "message": str(exc)}

    def delete_reference_file(self, file_id: str) -> dict[str, Any]:
        try:
            if not self.db:
                raise RuntimeError("Supabase가 연결되지 않았습니다.")
            row = self.db.delete_reference_file(file_id)
            if not row:
                return {"ok": False, "message": "삭제할 참조파일을 찾지 못했습니다."}
            path = Path(row.get("파일경로") or "")
            try:
                root = ATTACHMENT_ROOT.resolve()
                target = path.resolve()
                if target == root or root in target.parents:
                    target.unlink(missing_ok=True)
            except Exception as file_exc:
                logging.warning("Y드라이브 참조파일 삭제 실패(메타데이터는 삭제됨): %s", file_exc)
            return {"ok": True}
        except Exception as exc:
            logging.exception("참조파일 삭제 실패")
            return {"ok": False, "message": str(exc)}

    def select_files(self) -> dict[str, Any]:
        try:
            result = webview.windows[0].create_file_dialog(
                webview.FileDialog.OPEN,
                allow_multiple=True,
                file_types=(
                    "지원 문서 (*.xlsx;*.xls;*.pdf;*.docx;*.pptx)",
                    "모든 파일 (*.*)",
                ),
            )
            valid = []
            for raw in list(result or []):
                p = Path(raw)
                if p.suffix.lower() not in ALLOWED_EXTENSIONS:
                    continue
                if p.stat().st_size > MAX_FILE_SIZE:
                    continue
                valid.append({
                    "path": str(p),
                    "name": p.name,
                    "size": p.stat().st_size,
                    "extension": p.suffix.lower().lstrip("."),
                })
            return {"ok": True, "files": valid}
        except Exception as exc:
            logging.exception("파일 선택 실패")
            return {"ok": False, "message": str(exc)}

    def analyze_files(self, documents: list[dict[str, Any]]) -> dict[str, Any]:
        try:
            if not self.db:
                raise RuntimeError("Supabase가 연결되지 않았습니다.")
            api_key = get_openai_api_key()
            product_map = {p["제품코드"]: p for p in self.product_index if p.get("제품코드")}

            results, errors = [], []
            for doc in documents:
                path = Path(doc["path"])
                product_code = (doc.get("product_code") or "").strip()
                if not product_code or product_code not in product_map:
                    errors.append({"file_name": path.name, "message": "제품인덱스에서 제품이 연결되지 않았습니다."})
                    continue
                try:
                    results.append(analyze_document(path, product_map[product_code], api_key))
                except Exception as exc:
                    logging.exception("문서 분석 실패: %s", path)
                    errors.append({"file_name": path.name, "message": str(exc)})

            if not results and errors:
                detail = "\n".join(
                    f"- {e.get('file_name', '문서')}: {e.get('message', '알 수 없는 오류')}"
                    for e in errors
                )
                return {
                    "ok": False,
                    "message": "AI 분석에 실패했습니다.",
                    "detail": detail,
                    "errors": errors,
                }

            return {"ok": True, "results": results, "errors": errors}
        except Exception as exc:
            logging.exception("AI 분석 실패")
            return {"ok": False, "message": str(exc), "detail": str(exc)}

    def register_results(self, documents: list[dict[str, Any]], registrar_id: str) -> dict[str, Any]:
        if not self.db:
            return {"ok": False, "message": "Supabase가 연결되지 않았습니다."}

        registered_docs = 0
        registered_activities = 0
        skipped = []

        try:
            for item in documents:
                path = Path(item["file_path"])
                file_hash = sha256_file(path)
                duplicate = self.db.find_document_by_hash(file_hash)

                if duplicate:
                    skipped.append({"file_name": path.name, "reason": "동일 파일이 이미 등록되어 있습니다."})
                    continue

                analysis = item["analysis"]
                product_code = analysis.get("product_code")
                if not product_code:
                    skipped.append({"file_name": path.name, "reason": "제품코드가 확정되지 않았습니다."})
                    continue

                # 문서 FK 제약 때문에 제품이 마케팅대상제품에 없으면 최종 등록 시 자동 추가
                self.db.ensure_marketing_product(product_code)

                destination = copy_document(path)
                doc_row = {
                    "문서명": path.stem,
                    "문서종류": "마케팅 계획서",
                    "파일형식": path.suffix.lower().lstrip("."),
                    "파일경로": str(destination),
                    "파일크기": path.stat().st_size,
                    "파일해시": file_hash,
                    "제품코드": product_code,
                    "등록자ID": registrar_id,
                    "AI분석상태": "확정",
                    "AI분석결과": analysis,
                    "분석완료일시": datetime.now().isoformat(),
                }

                try:
                    created = self.db.insert_document(doc_row)
                except Exception:
                    if destination.exists():
                        destination.unlink()
                    raise

                document_id = created.get("문서ID")

                strategy = analysis.get("strategy") or {}
                strategy_row = {
                    "제품코드": product_code,
                    "타깃독자": strategy.get("target_readers"),
                    "핵심키워드": strategy.get("core_keywords") or [],
                    "마케팅문구": strategy.get("marketing_message"),
                    "마케팅전략": strategy.get("marketing_strategy"),
                    "USP": strategy.get("usp"),
                    "원본문서ID": document_id,
                    "등록자ID": registrar_id,
                }
                self.db.upsert_marketing_plan(strategy_row)
                self.db.upsert_sales_goal(product_code, analysis.get("sales_targets") or {}, registrar_id, document_id)

                rows = []
                for a in analysis.get("activities", []):
                    if not a.get("selected", True):
                        continue
                    rows.append({
                        "제품코드": product_code,
                        "활동분류": a["activity_category"],
                        "채널또는매체": a.get("channel_or_media"),
                        "활동명": a["activity_name"],
                        "시작일": a.get("start_date") or None,
                        "종료일": a.get("end_date") or None,
                        "일정비고": a.get("schedule_note"),
                        "비용": a.get("cost"),
                        "URL": a.get("url"),
                        "비고": a.get("note"),
                        "계획실행구분": a.get("plan_execution_type") or "계획",
                        "등록자ID": registrar_id,
                        "원본문서명": path.name,
                        "등록방식": "AI",
                        "원본문서ID": document_id,
                    })

                self.db.insert_activities(rows)
                registered_docs += 1
                registered_activities += len(rows)

            return {
                "ok": True,
                "registered_documents": registered_docs,
                "registered_activities": registered_activities,
                "skipped": skipped,
            }
        except Exception as exc:
            logging.exception("확정 등록 실패")
            return {"ok": False, "message": str(exc)}
