from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import openpyxl

from .config import YES24_DOWNLOAD_DIR


FILE_PATTERN = re.compile(r"^(\d{8})_예스24_(성인|아동)\.(?:xls|xlsx)$", re.IGNORECASE)
REQUIRED_COLUMNS = (
    "상품번호", "ISBN13", "상품명", "총계", "남", "녀", "미가입", "기타",
    "10대 이하", "20대 초", "20대 후", "30대 초", "30대 후", "40대 초",
    "40대 후", "50대 초", "50대 후", "60대 이상", "서울", "경기", "충청",
    "경상", "전라", "강원", "제주",
)
GENDER_COLUMNS = ("남", "녀", "미가입")
AGE_COLUMNS = (
    "기타", "10대 이하", "20대 초", "20대 후", "30대 초", "30대 후",
    "40대 초", "40대 후", "50대 초", "50대 후", "60대 이상",
)
REGION_COLUMNS = ("서울", "경기", "충청", "경상", "전라", "강원", "제주")


@dataclass(frozen=True)
class Yes24Demographics:
    rows: list[dict[str, Any]]
    file_count: int
    date_from: str
    date_to: str
    total_quantity: int
    distribution_count: int
    missing_product_code_rows: int = 0


def _text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _isbn(value: Any) -> str:
    text = _text(value)
    if text.endswith(".0"):
        text = text[:-2]
    return "".join(character for character in text if character.isdigit())


def _integer(value: Any) -> int:
    try:
        return int(round(float(str(value or 0).replace(",", ""))))
    except (TypeError, ValueError):
        return 0


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def parse_yes24_demographics(directory: Path = YES24_DOWNLOAD_DIR) -> Yes24Demographics:
    """YES24 일별 원본을 수정하지 않고 원본 수준의 구매자 분포로 읽습니다."""
    if not directory.exists():
        raise FileNotFoundError(f"YES24 원본 폴더를 찾을 수 없습니다: {directory}")
    files = sorted(
        path for path in directory.iterdir()
        if path.is_file() and FILE_PATTERN.match(path.name)
    )
    if not files:
        raise RuntimeError(f"YES24 성인/아동 원본 파일이 없습니다: {directory}")

    normalized: dict[tuple[str, str, str], dict[str, Any]] = {}
    for path in files:
        match = FILE_PATTERN.match(path.name)
        if not match:
            continue
        base_date = datetime.strptime(match.group(1), "%Y%m%d").date().isoformat()
        account_type = match.group(2)
        file_hash = _sha256(path)
        with path.open("rb") as stream:
            workbook = openpyxl.load_workbook(stream, read_only=True, data_only=True)
            try:
                worksheet = workbook.active
                iterator = worksheet.iter_rows(values_only=True)
                header_values = next(iterator, None) or []
                headers = [_text(value) for value in header_values]
                missing = [column for column in REQUIRED_COLUMNS if column not in headers]
                if missing:
                    raise RuntimeError(f"{path.name} 필수 컬럼 누락: {', '.join(missing)}")
                positions = {name: headers.index(name) for name in headers if name}
                for values in iterator:
                    isbn13 = _isbn(values[positions["ISBN13"]])
                    product_name = _text(values[positions["상품명"]])
                    if not isbn13 or product_name == "합계":
                        continue
                    total = _integer(values[positions["총계"]])
                    gender = {column: _integer(values[positions[column]]) for column in GENDER_COLUMNS}
                    age = {column: _integer(values[positions[column]]) for column in AGE_COLUMNS}
                    region = {column: _integer(values[positions[column]]) for column in REGION_COLUMNS}
                    if sum(gender.values()) != total:
                        raise RuntimeError(f"{path.name} {isbn13}: 성별 합계가 총계와 다릅니다.")
                    if sum(age.values()) != total:
                        raise RuntimeError(f"{path.name} {isbn13}: 연령 합계가 총계와 다릅니다.")
                    key = (base_date, account_type, isbn13)
                    if key in normalized:
                        raise RuntimeError(f"YES24 원본 Grain 중복: {base_date}/{account_type}/{isbn13}")
                    normalized[key] = {
                        "기준일": base_date,
                        "계정구분": account_type,
                        "ISBN13": isbn13,
                        "YES24상품번호": _text(values[positions["상품번호"]]),
                        "상품명": product_name,
                        "총판매수량": total,
                        "성별분포": gender,
                        "연령분포": age,
                        "지역분포": region,
                        "원본파일명": path.name,
                        "원본파일해시": file_hash,
                        "원본시트": worksheet.title,
                    }
            finally:
                workbook.close()

    rows = [normalized[key] for key in sorted(normalized)]
    if not rows:
        raise RuntimeError("YES24 원본에서 구매자 분포 데이터를 찾지 못했습니다.")
    return Yes24Demographics(
        rows=rows,
        file_count=len(files),
        date_from=rows[0]["기준일"],
        date_to=rows[-1]["기준일"],
        total_quantity=sum(row["총판매수량"] for row in rows),
        distribution_count=len(rows) * (len(GENDER_COLUMNS) + len(AGE_COLUMNS) + len(REGION_COLUMNS)),
    )


def preview_yes24_demographics(directory: Path = YES24_DOWNLOAD_DIR) -> dict[str, Any]:
    parsed = parse_yes24_demographics(directory)
    return {
        "files": parsed.file_count,
        "rows": len(parsed.rows),
        "date_from": parsed.date_from,
        "date_to": parsed.date_to,
        "total_quantity": parsed.total_quantity,
        "distribution_rows": parsed.distribution_count,
        "gender_categories": list(GENDER_COLUMNS),
        "age_categories": list(AGE_COLUMNS),
        "region_categories": list(REGION_COLUMNS),
    }
