from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from openpyxl import Workbook

from app.yes24_demographics import parse_yes24_demographics, preview_yes24_demographics


HEADERS = [
    "상품번호", "ISBN10", "ISBN13", "바코드", "상품명", "총계", "남", "녀", "미가입",
    "기타", "10대 이하", "20대 초", "20대 후", "30대 초", "30대 후", "40대 초",
    "40대 후", "50대 초", "50대 후", "60대 이상", "서울", "경기", "충청", "경상",
    "전라", "강원", "제주",
]


class Yes24DemographicsTests(TestCase):
    def _write_source(self, path: Path, quantity: int = 3) -> None:
        workbook = Workbook()
        sheet = workbook.active
        sheet.append(HEADERS)
        sheet.append([0, "", "", "", "합계", quantity, 1, 1, quantity - 2, quantity - 1, 1] + [0] * 9 + [quantity] + [0] * 6)
        sheet.append([123, "", "9791234567890", "9791234567890", "테스트 도서", quantity, 1, 1, quantity - 2, quantity - 1, 1] + [0] * 9 + [quantity] + [0] * 6)
        workbook.save(path)

    def test_parser_keeps_original_gender_age_and_region_grain(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self._write_source(root / "20260820_예스24_성인.xls")
            self._write_source(root / "20260820_예스24_아동.xls", 4)
            parsed = parse_yes24_demographics(root)

        self.assertEqual(parsed.file_count, 2)
        self.assertEqual(len(parsed.rows), 2)
        self.assertEqual(parsed.total_quantity, 7)
        self.assertEqual(parsed.distribution_count, 42)
        self.assertEqual(parsed.rows[0]["연령분포"]["20대 초"], 0)
        self.assertEqual(parsed.rows[1]["성별분포"]["미가입"], 2)
        self.assertEqual(parsed.rows[1]["지역분포"]["서울"], 4)

    def test_preview_reports_file_and_distribution_counts(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self._write_source(root / "20260820_예스24_성인.xls")
            result = preview_yes24_demographics(root)

        self.assertEqual(result["files"], 1)
        self.assertEqual(result["rows"], 1)
        self.assertEqual(result["distribution_rows"], 21)
