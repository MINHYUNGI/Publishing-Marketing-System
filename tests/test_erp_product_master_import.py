from __future__ import annotations

from datetime import date

import openpyxl
import pytest

from app.erp_product_master_import import (
    SOURCE_COLUMNS,
    compare_source_and_database,
    parse_product_master_excel,
    upsert_product_master,
)
from tests.fakes import FakeClient


def _workbook(path, rows):
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.append(SOURCE_COLUMNS)
    for row in rows:
        sheet.append([row.get(column) for column in SOURCE_COLUMNS])
    workbook.save(path)
    workbook.close()


def _row(code: str, name: str, price: int = 10_000):
    row = {column: f"{column}-값" for column in SOURCE_COLUMNS}
    row.update({
        "제품코드": code,
        "제품명": name,
        "정가": price,
        "구정가": None,
        "페이지수": 100,
        "박스부수": None,
        "묶음부수": 5,
        "초판발행일": date(2026, 8, 1),
        "첫출고일": "2026/08/02",
        "첫출고일(제품)": None,
        "자료입력일": "20260803",
        "자료수정일": None,
        "UCI코드": None,
    })
    return row


def test_parse_validates_and_normalises_all_columns(tmp_path):
    path = tmp_path / "master.xlsx"
    _workbook(path, [_row("P1", "첫 책"), _row("P2", "둘째 책")])

    parsed = parse_product_master_excel(path, expected_rows=2)

    assert parsed.validation.row_count == 2
    assert parsed.validation.unique_product_codes == 2
    assert parsed.rows[0]["초판발행일"] == "2026-08-01"
    assert parsed.rows[0]["첫출고일"] == "2026-08-02"
    assert parsed.rows[0]["자료입력일"] == "2026-08-03"
    assert parsed.rows[0]["UCI코드"] is None
    assert parsed.rows[0]["정가"] == 10_000


def test_parse_stops_on_duplicate_product_code(tmp_path):
    path = tmp_path / "duplicate.xlsx"
    _workbook(path, [_row("P1", "첫 책"), _row("P1", "중복 책")])

    with pytest.raises(ValueError, match="제품코드 중복 1건"):
        parse_product_master_excel(path, expected_rows=2)


def test_upsert_inserts_and_updates_by_product_code(tmp_path):
    path = tmp_path / "master.xlsx"
    _workbook(path, [_row("P1", "수정된 책"), _row("P2", "새 책")])
    parsed = parse_product_master_excel(path, expected_rows=2)
    client = FakeClient({"ERP제품마스터": [_row("P1", "이전 책")]})

    result = upsert_product_master(client, parsed, batch_size=1)

    assert result.inserted == 1
    assert result.updated == 1
    assert result.batches == 2
    stored = {row["제품코드"]: row for row in client.tables["ERP제품마스터"]}
    assert stored["P1"]["제품명"] == "수정된 책"
    assert stored["P2"]["제품명"] == "새 책"
    assert all(row["원본파일명"] == "master.xlsx" for row in stored.values())
    assert all(row["적재일시"] for row in stored.values())


def test_compare_checks_every_source_field(tmp_path):
    path = tmp_path / "master.xlsx"
    _workbook(path, [_row("P1", "첫 책")])
    parsed = parse_product_master_excel(path, expected_rows=1)

    assert compare_source_and_database(parsed, parsed.rows) == []
    changed = [{**parsed.rows[0], "규격": "변경"}]
    assert compare_source_and_database(parsed, changed) == ["34개 원본 필드 값 불일치: 1건"]
