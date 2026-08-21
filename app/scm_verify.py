from __future__ import annotations

from collections import defaultdict
from typing import Any

from .scm_import import parse_scm_ledger
from .yes24_demographics import parse_yes24_demographics


def _aggregate(rows: list[dict[str, Any]], key_name: str, quantity_name: str) -> dict[str, int]:
    result: dict[str, int] = defaultdict(int)
    for row in rows:
        result[str(row.get(key_name) or "미매칭")] += int(row.get(quantity_name) or 0)
    return dict(result)


def _fetch_all(client: Any, table: str, columns: str, order: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    start = 0
    while True:
        batch = client.table(table).select(columns).order(order).range(start, start + 999).execute().data or []
        rows.extend(batch)
        if len(batch) < 1000:
            return rows
        start += 1000


def verify_live_scm(backend: Any) -> dict[str, Any]:
    if not backend.db:
        raise RuntimeError("Supabase가 연결되지 않았습니다.")
    source = parse_scm_ledger()
    yes24 = parse_yes24_demographics()
    db_rows = _fetch_all(
        backend.db.client,
        "SCM일별실판매",
        "판매일,거래처코드,ISBN13,제품코드,판매수량",
        "판매일",
    )
    source_natural = {
        (row["판매일"], row["거래처코드"], row["ISBN13"]): int(row["판매수량"])
        for row in source.rows
    }
    db_natural = {
        (str(row.get("판매일")), str(row.get("거래처코드")), str(row.get("ISBN13"))): int(row.get("판매수량") or 0)
        for row in db_rows
    }
    source_by_date: dict[str, int] = defaultdict(int)
    source_by_client: dict[str, int] = defaultdict(int)
    source_by_isbn: dict[str, int] = defaultdict(int)
    valid_codes = {str(row.get("제품코드")) for row in backend.product_index if row.get("제품코드")}
    source_code_by_isbn: dict[str, str] = {}
    for row in source.rows:
        code = str(row.get("제품코드") or "")
        if code in valid_codes:
            source_code_by_isbn[row["ISBN13"]] = max(code, source_code_by_isbn.get(row["ISBN13"], ""))
    source_by_product: dict[str, int] = defaultdict(int)
    for row in source.rows:
        quantity = int(row["판매수량"])
        source_by_date[row["판매일"]] += quantity
        source_by_client[row["거래처코드"]] += quantity
        source_by_isbn[row["ISBN13"]] += quantity
        source_by_product[source_code_by_isbn.get(row["ISBN13"], "미매칭")] += quantity
    db_by_date = _aggregate(db_rows, "판매일", "판매수량")
    db_by_client = _aggregate(db_rows, "거래처코드", "판매수량")
    db_by_isbn = _aggregate(db_rows, "ISBN13", "판매수량")
    db_by_product = _aggregate(db_rows, "제품코드", "판매수량")
    return {
        "ok": source_natural == db_natural,
        "sales": {
            "source_rows": len(source.rows), "db_rows": len(db_rows),
            "source_quantity": source.total_quantity,
            "db_quantity": sum(int(row.get("판매수량") or 0) for row in db_rows),
            "natural_grain_equal": source_natural == db_natural,
            "date_aggregate_equal": dict(source_by_date) == db_by_date,
            "client_aggregate_equal": dict(source_by_client) == db_by_client,
            "isbn_aggregate_equal": dict(source_by_isbn) == db_by_isbn,
            "product_aggregate_equal": dict(source_by_product) == db_by_product,
            "product_link_equal": all(
                (row.get("제품코드") or "미매칭") == source_code_by_isbn.get(str(row.get("ISBN13")), "미매칭")
                for row in db_rows
            ),
            "client_totals": db_by_client,
            "product_groups": len(db_by_product),
            "unmatched_rows": sum(1 for row in db_rows if not row.get("제품코드")),
            "unmatched_isbns": len({str(row.get("ISBN13")) for row in db_rows if not row.get("제품코드")}),
        },
        "yes24_source": {
            "files": yes24.file_count,
            "snapshots": len(yes24.rows),
            "quantity": yes24.total_quantity,
            "distribution_rows": yes24.distribution_count,
        },
    }


if __name__ == "__main__":
    import json
    from .backend import Backend

    app = Backend()
    initialized = app.initialize()
    if not initialized.get("ok"):
        raise RuntimeError(initialized.get("message") or "초기화 실패")
    print(json.dumps(verify_live_scm(app), ensure_ascii=False, indent=2))
