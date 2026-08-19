from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Any

import openpyxl
import webview

REQUIRED_COLUMNS = ("제품코드", "제품명", "매출일자", "매출부수", "매출금액")
ALL_COLUMNS = (
    "브랜드", "계열", "시리즈", "제품코드", "제품명", "매출일자", "정가", "첫출고일",
    "출고부수", "출고금액", "반품부수", "반품금액", "매출부수", "매출금액", "입고부수", "기증부수", "재고",
)
INTEGER_COLUMNS = {
    "출고부수", "출고금액", "반품부수", "반품금액", "매출부수", "매출금액", "입고부수", "기증부수", "재고"
}


def _date_text(value: Any) -> str | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    text = str(value).strip().replace("/", "-").replace(".", "-")
    if not text:
        return None
    parts = [p for p in text.split("-") if p]
    if len(parts) >= 3:
        try:
            return date(int(parts[0]), int(parts[1]), int(parts[2])).isoformat()
        except ValueError:
            pass
    return text


def _number(value: Any, integer: bool = False) -> int | float | None:
    if value in (None, ""):
        return 0 if integer else None
    try:
        number = float(str(value).replace(",", ""))
        return int(round(number)) if integer else number
    except (TypeError, ValueError):
        return 0 if integer else None


def _find_header_row(ws) -> tuple[int, list[str]]:
    """ERP 다운로드 파일에서 헤더 행을 찾습니다. 보통 1행이지만 상단 안내행이 있어도 처리합니다."""
    for row_no, values in enumerate(ws.iter_rows(min_row=1, max_row=20, values_only=True), start=1):
        headers = [str(x).strip() if x is not None else "" for x in values]
        if all(name in headers for name in REQUIRED_COLUMNS):
            return row_no, headers
    raise RuntimeError("필수 열을 찾을 수 없습니다: " + ", ".join(REQUIRED_COLUMNS))


def choose_and_import_erp(backend: Any, expected_product_code: str | None = None) -> dict[str, Any]:
    """현재 성과 화면의 도서 1권에 ERP 일별 매출 엑셀을 연결합니다."""
    try:
        if not backend.db:
            raise RuntimeError("Supabase가 연결되지 않았습니다.")
        if not expected_product_code:
            raise RuntimeError("먼저 출간 후 성과 화면에서 도서를 선택해 주세요.")
        if not webview.windows:
            raise RuntimeError("파일 선택 창을 열 수 없습니다.")

        selected = webview.windows[0].create_file_dialog(
            webview.OPEN_DIALOG,
            allow_multiple=False,
            file_types=("Excel 파일 (*.xlsx)",),
        )
        if not selected:
            return {"ok": False, "cancelled": True, "message": "파일 선택을 취소했습니다."}

        path = Path(selected[0])
        workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
        ws = workbook[workbook.sheetnames[0]]
        header_row, headers = _find_header_row(ws)

        rows: list[dict[str, Any]] = []
        skipped = 0
        product_codes: set[str] = set()
        dates: list[str] = []

        for values in ws.iter_rows(min_row=header_row + 1, values_only=True):
            source = dict(zip(headers, values))
            code = str(source.get("제품코드") or "").strip()
            sales_date = _date_text(source.get("매출일자"))
            # ERP 파일 하단 소계/총계 등 제품코드 없는 행은 제외합니다.
            if not code or not sales_date:
                skipped += 1
                continue
            product_codes.add(code)
            if code != str(expected_product_code).strip():
                continue

            row: dict[str, Any] = {}
            for col in ALL_COLUMNS:
                value = source.get(col)
                if col in {"매출일자", "첫출고일"}:
                    row[col] = _date_text(value)
                elif col in INTEGER_COLUMNS:
                    row[col] = _number(value, integer=True)
                elif col == "정가":
                    row[col] = _number(value, integer=False)
                elif value is None:
                    row[col] = None
                else:
                    row[col] = str(value).strip()
            row["제품코드"] = code
            row["원본파일명"] = path.name
            row["수정일시"] = datetime.now().isoformat()
            rows.append(row)
            dates.append(sales_date)

        expected = str(expected_product_code).strip()
        if not product_codes:
            raise RuntimeError("제품코드가 있는 ERP 일별 데이터가 없습니다. 소계/총계만 있는 파일인지 확인해 주세요.")
        if product_codes != {expected}:
            found = ", ".join(sorted(product_codes))
            raise RuntimeError(f"선택한 도서의 제품코드는 {expected}인데, 업로드 파일에는 {found} 제품코드가 있습니다. 해당 도서만 조회한 ERP 파일을 사용해 주세요.")
        if not rows:
            raise RuntimeError("업로드할 ERP 일별 데이터가 없습니다.")

        batch_size = 500
        for start in range(0, len(rows), batch_size):
            backend.db.client.table("ERP일별판매실적").upsert(
                rows[start:start + batch_size],
                on_conflict="제품코드,매출일자",
            ).execute()

        return {
            "ok": True,
            "file_name": path.name,
            "product_code": expected,
            "total": len(rows),
            "skipped": skipped,
            "date_from": min(dates) if dates else None,
            "date_to": max(dates) if dates else None,
        }
    except Exception as exc:
        return {"ok": False, "message": str(exc)}
