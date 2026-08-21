from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from openpyxl import Workbook

from app.scm_import import parse_scm_ledger, preview_scm_sync


class ScmImportTests(TestCase):
    def _workbook(self, path: Path) -> None:
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "통합원장"
        sheet.append([
            "판매기준일", "거래처", "ISBN", "판매합계", "제품코드",
            "분석상품명", "출판일자", "원본파일", "원본시트",
        ])
        sheet.append([date(2026, 8, 1), "교보문고", "978-1-234", 5, "P1", "도서 1", date(2026, 7, 1), "a.xlsx", "판매"])
        sheet.append([date(2026, 8, 1), "교보문고", "9781234", -2, "P1", "도서 1", date(2026, 7, 1), "a.xlsx", "판매"])
        sheet.append(["20260802", "예스24", "9789999", 7, None, "미매칭 도서", None, "b.xlsx", "실판매"])
        sheet.append([date(2026, 8, 3), "알 수 없음", "9780000", 3, None, "제외", None, None, None])
        sheet.append([date(2026, 8, 3), "알라딘", "9780001", 0, None, "제로", None, None, None])
        workbook.save(path)

    def test_parse_preserves_negative_and_unmatched_rows(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "ledger.xlsx"
            self._workbook(path)
            ledger = parse_scm_ledger(path)

        self.assertEqual(ledger.source_count, 5)
        self.assertEqual(len(ledger.rows), 2)
        self.assertEqual(ledger.collapsed_count, 1)
        self.assertEqual(ledger.skipped_count, 2)
        self.assertEqual(ledger.total_quantity, 10)
        self.assertEqual(ledger.rows[0]["판매수량"], 3)
        self.assertEqual(ledger.rows[1]["거래처코드"], "YES24")
        self.assertIsNone(ledger.rows[1]["제품코드"])
        self.assertEqual(ledger.client_summary["YES24"]["unmatched"], 1)

    def test_preview_reports_same_grain_and_quantity(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "ledger.xlsx"
            self._workbook(path)
            result = preview_scm_sync(path)

        self.assertTrue(result["ok"])
        self.assertEqual(result["rows"], 2)
        self.assertEqual(result["total_quantity"], 10)
        self.assertEqual(result["missing_product_code_rows"], 1)
