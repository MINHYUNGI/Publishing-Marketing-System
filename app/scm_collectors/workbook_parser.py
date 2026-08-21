from __future__ import annotations

import re
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable

import openpyxl

from ..scm_import import CLIENT_CODES, ScmLedger


HEADER_HINTS = {
    "교보문고": ("ISBN",),
    "영풍문고": ("바코드", "ISBN", "ISBN13"),
    "예스24": ("ISBN13",),
    "알라딘": ("ISBN",),
}


def _text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _column(value: Any) -> str:
    return _text(value).replace("\n", "").replace(" ", "")


def _isbn(value: Any) -> str:
    text = _text(value)
    if text.endswith(".0"):
        text = text[:-2]
    if "E+" in text.upper():
        try:
            text = str(int(float(text)))
        except ValueError:
            pass
    return "".join(character for character in text if character.isdigit())


def _integer(value: Any) -> int:
    if value in (None, ""):
        return 0
    cleaned = re.sub(r"[^0-9.\-]", "", str(value).replace(",", ""))
    if cleaned in {"", "-", ".", "-."}:
        return 0
    try:
        return int(float(cleaned))
    except ValueError:
        return 0


def _date_text(value: Any) -> str | None:
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    text = _text(value).replace(".", "-").replace("/", "-")
    parts = [part for part in text.split("-") if part]
    if len(parts) >= 3:
        try:
            return date(int(parts[0]), int(parts[1]), int(parts[2])).isoformat()
        except ValueError:
            return None
    return None


def _client(sheet_name: str) -> str | None:
    if "교보" in sheet_name:
        return "교보문고"
    if "영풍" in sheet_name:
        return "영풍문고"
    if "예스" in sheet_name or "YES" in sheet_name.upper():
        return "예스24"
    if "알라딘" in sheet_name:
        return "알라딘"
    return None


def _find_header(rows: list[tuple[Any, ...]], client_name: str) -> int:
    hints = HEADER_HINTS[client_name]
    for index, row in enumerate(rows[:30]):
        values = {_column(value) for value in row if _text(value)}
        if any(any(hint in value for value in values) for hint in hints):
            return index
    raise RuntimeError(f"{client_name} 시트에서 헤더 행을 찾지 못했습니다.")


def _position(headers: list[str], candidates: Iterable[str], required: bool = False) -> int | None:
    normalized = [_column(value) for value in headers]
    for candidate in candidates:
        target = _column(candidate)
        for index, value in enumerate(normalized):
            if value == target:
                return index
        for index, value in enumerate(normalized):
            if target in value:
                return index
    if required:
        raise RuntimeError("필수 컬럼을 찾지 못했습니다: " + ", ".join(candidates))
    return None


def _value(row: tuple[Any, ...], position: int | None) -> Any:
    return row[position] if position is not None and position < len(row) else None


def _parse_sheet(
    worksheet: Any,
    sale_date: str,
    source_name: str,
) -> list[dict[str, Any]]:
    client_name = _client(worksheet.title)
    if not client_name:
        return []
    raw_rows = list(worksheet.iter_rows(values_only=True))
    if not raw_rows:
        return []
    # 판매가 없는 거래처/계정은 날짜 작업파일에 빈 템플릿 시트로 남는다.
    # 단일 제목 셀만 있는 시트도 같은 의미이므로 정상적인 0건으로 건너뛴다.
    meaningful_cells = sum(1 for row in raw_rows for value in row if _text(value))
    if meaningful_cells <= 1:
        return []
    header_index = _find_header(raw_rows, client_name)
    headers = [_text(value) for value in raw_rows[header_index]]
    isbn_pos = _position(headers, ("ISBN13", "ISBN", "바코드"), required=True)
    name_pos = _position(headers, ("상품명", "도서명"))
    publication_pos = _position(headers, ("출판일자", "발행일", "출간일"))

    if client_name == "교보문고":
        quantity_positions = [
            _position(headers, ("판매(영업점)", "판매영업점", "영업점")),
            _position(headers, ("판매(온라인)", "판매온라인", "온라인")),
            _position(headers, ("판매(인터파크)", "판매인터파크", "인터파크")),
        ]
    elif client_name == "영풍문고":
        quantity_positions = [_position(headers, ("판매수량", "판매수", "수량"), required=True)]
    elif client_name == "예스24":
        quantity_positions = [_position(headers, ("총계",), required=True)]
    else:
        quantity_positions = [_position(headers, ("판매권수", "판매수량", "판매수", "권수"), required=True)]

    parsed: list[dict[str, Any]] = []
    for row in raw_rows[header_index + 1 :]:
        isbn13 = _isbn(_value(row, isbn_pos))
        product_name = _text(_value(row, name_pos))
        quantity = sum(_integer(_value(row, position)) for position in quantity_positions)
        if not isbn13 or not product_name or product_name == "합계" or quantity == 0:
            continue
        parsed.append(
            {
                "판매일": sale_date,
                "거래처코드": CLIENT_CODES[client_name],
                "ISBN13": isbn13,
                "제품코드": None,
                "SCM상품명": product_name,
                "출판일자": _date_text(_value(row, publication_pos)),
                "판매수량": quantity,
                "원본파일명": source_name,
                "원본시트": worksheet.title,
            }
        )
    return parsed


def parse_date_workbooks(paths: Iterable[Path], allow_empty: bool = False) -> ScmLedger:
    """선택 날짜 작업파일만 읽어 기존 DB Grain으로 정규화합니다."""
    normalized: dict[tuple[str, str, str], dict[str, Any]] = {}
    source_count = skipped = 0
    workbook_dates: list[str] = []
    for path in sorted(Path(value) for value in paths):
        if not path.exists():
            raise FileNotFoundError(f"SCM 날짜 작업파일을 찾을 수 없습니다: {path}")
        if not re.fullmatch(r"\d{8}", path.stem):
            raise RuntimeError(f"SCM 날짜 작업파일명이 YYYYMMDD 형식이 아닙니다: {path.name}")
        sale_date = datetime.strptime(path.stem, "%Y%m%d").date().isoformat()
        workbook_dates.append(sale_date)
        workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
        try:
            for worksheet in workbook.worksheets:
                rows = _parse_sheet(worksheet, sale_date, path.name)
                source_count += len(rows)
                for row in rows:
                    key = (row["판매일"], row["거래처코드"], row["ISBN13"])
                    if key in normalized:
                        normalized[key]["판매수량"] += row["판매수량"]
                    else:
                        normalized[key] = row
        finally:
            workbook.close()

    rows = [normalized[key] for key in sorted(normalized)]
    if not rows and not allow_empty:
        raise RuntimeError("수집된 작업파일에서 유효한 SCM 실판매를 찾지 못했습니다.")
    summary: dict[str, dict[str, int]] = defaultdict(lambda: {"rows": 0, "quantity": 0, "unmatched": 0})
    for row in rows:
        values = summary[row["거래처코드"]]
        values["rows"] += 1
        values["quantity"] += row["판매수량"]
        values["unmatched"] += 1
    return ScmLedger(
        rows=rows,
        source_count=source_count,
        collapsed_count=source_count - len(rows),
        skipped_count=skipped,
        date_from=rows[0]["판매일"] if rows else min(workbook_dates),
        date_to=rows[-1]["판매일"] if rows else max(workbook_dates),
        total_quantity=sum(row["판매수량"] for row in rows),
        client_summary=dict(summary),
        product_codes=set(),
    )
