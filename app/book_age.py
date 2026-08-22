from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True)
class BookAgeClassification:
    status: str
    base_date: str | None
    source: str


def _as_date(value: str | date | datetime | None) -> date | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()[:10]
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def classify_book_age(
    erp_publication_date: str | date | datetime | None,
    first_scm_sale_date: str | date | datetime | None,
    reference_date: str | date | datetime,
    *,
    force_old_without_erp: bool = False,
) -> BookAgeClassification:
    """ERP 초판발행일을 최우선으로 신간/구간을 판정합니다.

    공식 발행일이 없을 때만 SCM 최초 실판매일을 fallback으로 사용합니다.
    과거 도서명 강제규칙은 ERP 날짜가 없는 경우에만 보존합니다.
    """
    reference = _as_date(reference_date)
    if reference is None:
        raise ValueError(f"유효하지 않은 판정 기준일입니다: {reference_date!r}")

    erp_date = _as_date(erp_publication_date)
    if erp_date is not None:
        if erp_date > reference:
            status = "출간예정"
        else:
            status = "신간" if (reference - erp_date).days <= 365 else "구간"
        return BookAgeClassification(status, erp_date.isoformat(), "ERP제품마스터.초판발행일")

    scm_date = _as_date(first_scm_sale_date)
    if force_old_without_erp:
        return BookAgeClassification(
            "구간",
            scm_date.isoformat() if scm_date else None,
            "도서명 강제규칙(ERP 출간일 없음)",
        )
    if scm_date is None:
        return BookAgeClassification("미확인", None, "판정일자없음")
    if scm_date > reference:
        status = "출간예정"
    else:
        status = "신간" if (reference - scm_date).days <= 365 else "구간"
    return BookAgeClassification(status, scm_date.isoformat(), "SCM최초실판매일(fallback)")
