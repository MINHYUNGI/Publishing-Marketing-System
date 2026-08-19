from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Any

import openpyxl
import webview

EXPECTED_SHEETS = ("아이세움", "북폴리오")
REQUIRED_COLUMNS = ("제품코드", "제품명", "년월", "매출부수", "매출금액")
ALL_COLUMNS = (
    "브랜드", "계열", "시리즈", "제품코드", "제품명", "년월", "정가", "첫출고일", "제품형태",
    "출고부수", "출고금액", "반품부수", "반품금액", "매출부수", "매출금액", "입고부수", "기증부수", "반품율", "재고",
)
INTEGER_COLUMNS = {
    "정가", "출고부수", "출고금액", "반품부수", "반품금액", "매출부수", "매출금액", "입고부수", "기증부수", "재고"
}


def _date_text(value: Any) -> str | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    text = str(value).strip().replace("/", "-")
    return text or None


def _month_text(value: Any) -> str | None:
    if value in (None, ""):
        return None
    if isinstance(value, (datetime, date)):
        return value.strftime("%Y/%m")
    text = str(value).strip().replace("-", "/")
    if len(text) >= 7:
        return text[:7]
    return text or None


def _number(value: Any, integer: bool = False) -> int | float | None:
    if value in (None, ""):
        return 0 if integer else None
    try:
        number = float(value)
        return int(round(number)) if integer else number
    except (TypeError, ValueError):
        return 0 if integer else None


def choose_and_import_erp(backend: Any) -> dict[str, Any]:
    try:
        if not backend.db:
            raise RuntimeError("Supabase가 연결되지 않았습니다.")
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
        missing_sheets = [name for name in EXPECTED_SHEETS if name not in workbook.sheetnames]
        if missing_sheets:
            raise RuntimeError("필수 시트가 없습니다: " + ", ".join(missing_sheets))

        rows: list[dict[str, Any]] = []
        skipped = 0
        sheet_counts: dict[str, int] = {}
        months: set[str] = set()

        for sheet_name in EXPECTED_SHEETS:
            ws = workbook[sheet_name]
            iterator = ws.iter_rows(values_only=True)
            headers = [str(x).strip() if x is not None else "" for x in next(iterator)]
            missing_columns = [name for name in REQUIRED_COLUMNS if name not in headers]
            if missing_columns:
                raise RuntimeError(f"{sheet_name} 시트 필수 열 누락: {', '.join(missing_columns)}")

            count = 0
            for values in iterator:
                source = dict(zip(headers, values))
                code = str(source.get("제품코드") or "").strip()
                month = _month_text(source.get("년월"))
                if not code or not month:
                    skipped += 1
                    continue

                row: dict[str, Any] = {}
                for col in ALL_COLUMNS:
                    value = source.get(col)
                    if col == "첫출고일":
                        row[col] = _date_text(value)
                    elif col == "년월":
                        row[col] = month
                    elif col in INTEGER_COLUMNS:
                        row[col] = _number(value, integer=True)
                    elif col == "반품율":
                        row[col] = _number(value, integer=False)
                    elif value is None:
                        row[col] = None
                    else:
                        row[col] = str(value).strip()

                row["제품코드"] = code
                row["원천시트"] = sheet_name
                row["원천파일명"] = path.name
                row["수정일시"] = datetime.now().isoformat()
                rows.append(row)
                count += 1
                months.add(month)
            sheet_counts[sheet_name] = count

        if not rows:
            raise RuntimeError("업로드할 ERP 데이터가 없습니다.")

        # 같은 제품코드+년월을 다시 올리면 기존 값을 갱신합니다.
        batch_size = 500
        for start in range(0, len(rows), batch_size):
            batch = rows[start:start + batch_size]
            backend.db.client.table("ERP월별판매실적").upsert(
                batch,
                on_conflict="제품코드,년월",
            ).execute()

        return {
            "ok": True,
            "file_name": path.name,
            "total": len(rows),
            "skipped": skipped,
            "sheet_counts": sheet_counts,
            "months": sorted(months),
        }
    except Exception as exc:
        return {"ok": False, "message": str(exc)}
