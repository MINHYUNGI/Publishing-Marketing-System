from __future__ import annotations

import base64
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.backend import Backend

from tests.fakes import database_with, performance_tables


class PerformanceAndCoverTests(unittest.TestCase):
    @patch("app.security.get_youtube_api_key", return_value=None)
    def test_performance_read_combines_execution_links_erp_and_cover(self, _key):
        database = database_with(performance_tables())
        detail = database.fetch_post_launch_performance("P1")
        self.assertEqual(detail["대표표지"]["파일ID"], "cover-1")
        self.assertEqual(detail["ERP일별판매실적"][0]["매출부수"], 12)
        self.assertEqual(detail["판매실적일별"][0]["ERP출고부수"], 12)
        activity = detail["마케팅활동"][0]
        self.assertEqual(activity["실행활동ID"], "execution-1")
        self.assertEqual(activity["실행정렬순서"], 20)
        self.assertEqual(activity["콘텐츠링크"][0]["콘텐츠성과ID"], "content-1")

    def test_mark_reference_as_cover_demotes_previous_cover(self):
        database = database_with(
            {
                "마케팅참조파일": [
                    {"파일ID": "old", "제품코드": "P1", "파일분류": "도서표지", "생성일시": "1"},
                    {"파일ID": "new", "제품코드": "P1", "파일분류": "참조이미지", "생성일시": "2"},
                ]
            }
        )
        database.mark_reference_as_cover("P1", "new")
        rows = {row["파일ID"]: row for row in database.client.tables["마케팅참조파일"]}
        self.assertEqual(rows["old"]["파일분류"], "참조이미지")
        self.assertEqual(rows["new"]["파일분류"], "도서표지")
        self.assertEqual(database.fetch_cover_reference("P1")["파일ID"], "new")

    def test_backend_registers_jfif_cover_without_real_storage_or_db(self):
        backend = Backend()
        backend.db = database_with({"마케팅대상제품": [], "마케팅참조파일": []})
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "cover.jfif"
            destination.write_bytes(b"jfif-image")
            encoded = base64.b64encode(b"jfif-image").decode("ascii")
            with patch("app.backend.save_reference_bytes", return_value=destination):
                result = backend.add_reference_files(
                    "P1",
                    [{"name": "cover.jfif", "data_base64": encoded}],
                    file_category="도서표지",
                )
        self.assertTrue(result["ok"])
        self.assertEqual(result["files"][0]["파일형식"], "jfif")
        self.assertEqual(backend.db.fetch_cover_reference("P1")["파일ID"], result["files"][0]["파일ID"])


if __name__ == "__main__":
    unittest.main()
