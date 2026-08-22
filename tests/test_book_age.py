from datetime import date, timedelta

from app.book_age import classify_book_age


REFERENCE = date(2026, 8, 22)


def test_erp_publication_date_within_365_days_is_new():
    result = classify_book_age(REFERENCE - timedelta(days=364), "2020-01-01", REFERENCE)
    assert result.status == "신간"
    assert result.source == "ERP제품마스터.초판발행일"


def test_exactly_365_days_is_new_and_366_days_is_backlist():
    assert classify_book_age(REFERENCE - timedelta(days=365), None, REFERENCE).status == "신간"
    assert classify_book_age(REFERENCE - timedelta(days=366), None, REFERENCE).status == "구간"


def test_erp_date_overrides_old_scm_first_sale():
    assert classify_book_age("2026-07-30", "2020-01-01", REFERENCE).status == "신간"


def test_old_erp_date_overrides_recent_scm_first_sale():
    assert classify_book_age("2020-01-01", "2026-08-01", REFERENCE).status == "구간"


def test_missing_erp_date_falls_back_to_first_scm_sale():
    result = classify_book_age(None, "2026-08-01", REFERENCE)
    assert result.status == "신간"
    assert result.source == "SCM최초실판매일(fallback)"


def test_future_erp_product_is_upcoming():
    assert classify_book_age("2026-09-01", "2020-01-01", REFERENCE).status == "출간예정"


def test_missing_erp_and_scm_dates_is_unknown():
    assert classify_book_age(None, None, REFERENCE).status == "미확인"


def test_legacy_title_rule_does_not_override_erp_date():
    result = classify_book_age("2026-08-01", "2020-01-01", REFERENCE, force_old_without_erp=True)
    assert result.status == "신간"


def test_legacy_title_rule_is_retained_only_without_erp_date():
    result = classify_book_age(None, "2026-08-01", REFERENCE, force_old_without_erp=True)
    assert result.status == "구간"
