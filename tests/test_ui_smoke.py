from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
UI = ROOT / "ui" / "index.html"
SCM_UI = ROOT / "ui" / "scm-dashboard.html"
LEGACY_SCM_UI = Path(r"Y:\출판사업본부\05. 영업 실적\01. 실판매_대시보드(교보,영풍,예스,알라).html")


class UiSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = UI.read_text(encoding="utf-8")

    def test_required_views_and_functions_exist(self):
        for marker in (
            'id="uploadPage"',
            'id="detailPage"',
            'id="performancePage"',
            'id="scmPage"',
            'id="navScm"',
            'id="bookstorePage"',
            'id="navBookstore"',
            'id="socialPage"',
            'id="navSocial"',
            "채널별 마케팅 활동 현황",
            "주요 4개 서점 현황",
            "loadMajorBookstoreTimeline",
            "renderMajorBookstoreTimeline",
            'id="bookstoreProductFilter"',
            "bookstore-weekend",
            "bookstore-resizer",
            "실판매부수",
            "openSharedActivityEditor",
            "openBookstoreActivityEditor",
            "loadSocialViralDashboard",
            "renderSocialViralDashboard",
            "openSocialActivityEditor",
            "게시 후 7일",
            "social-chart-post",
            "공통 Y축 최대",
            "social-y-label zero",
            '<polyline class="sales-line"',
            'ondblclick="openBookstoreActivityEditor',
            "실제 집행 비용",
            'Math.round(Number(value||0)/100000)/10',
            "function openSnsContent",
            "function loadMarketingPlanDetail",
            "function loadPerformanceDetail",
            "function selectPerformanceCover",
            "pywebview.api.restart_latest_version",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, self.html)

    def test_runtime_contract_markers_are_preserved(self):
        self.assertIn("await window.pywebview.api.open_external_url", self.html)
        self.assertIn("실행활동ID", self.html)
        self.assertIn("ERP일별판매실적", self.html)
        self.assertIn('role="dialog"', self.html)

    def test_scm_chart_stops_after_last_collected_date(self):
        self.assertIn("hasScm?perfNum(x.SCM실판매부수):null", self.html)
        self.assertIn("key<=currentPerformanceData.SCM최종데이터일", self.html)
        self.assertIn("scm:hasScm?0:null", self.html)
        self.assertIn("function perfScmSvg(rows,centerX,y)", self.html)
        self.assertEqual(self.html.count("const scmLine=perfScmSvg(rows,centerX,y);"), 3)
        self.assertNotIn("const hasScm=rows.some", self.html)

    def test_social_chart_uses_straight_segments_and_shared_book_scale(self):
        self.assertIn('stroke-width:1.4', self.html)
        self.assertIn('stroke-linejoin:miter', self.html)
        self.assertIn('items.flatMap(item=>(item.판매포인트||[])', self.html)
        self.assertIn('point.sales===null?""', self.html)
        self.assertNotIn('class="social-curve"', self.html)

    def test_bookstore_hover_and_million_won_contract(self):
        tooltips = re.findall(r"function tooltip\(row\)\{[^\r\n]+", self.html)
        self.assertTrue(tooltips)
        active_tooltip = tooltips[-1]
        self.assertIn("일정 비고", active_tooltip)
        self.assertIn("마케팅 세부 내용 / 비고", active_tooltip)
        for removed in ("해당 서점 실판매", "실제 집행비용", "채널·매체"):
            self.assertNotIn(removed, active_tooltip)
        formatter = re.search(r"function bookstoreMillionWon\(value\)\{.*?\}", self.html)
        self.assertIsNotNone(formatter)
        node = shutil.which("node")
        if not node:
            return
        source = formatter.group(0) + "\nconsole.log([3850000,3840000,1000000,550000,0].map(bookstoreMillionWon).join('|'));"
        result = subprocess.run([node, "-e", source], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "3.9백만원|3.8백만원|1.0백만원|0.6백만원|0.0백만원")

    def test_inline_javascript_has_valid_syntax(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("Node.js is unavailable")
        scripts = re.findall(r"<script[^>]*>(.*?)</script>", self.html, flags=re.DOTALL | re.IGNORECASE)
        self.assertGreater(len(scripts), 0)
        source = "\n".join(scripts)
        with tempfile.NamedTemporaryFile("w", suffix=".js", encoding="utf-8", delete=False) as handle:
            handle.write(source)
            path = Path(handle.name)
        try:
            result = subprocess.run([node, "--check", str(path)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
        finally:
            path.unlink(missing_ok=True)

    def test_preserved_scm_dashboard_contract_and_syntax(self):
        html = SCM_UI.read_text(encoding="utf-8")
        legacy = LEGACY_SCM_UI.read_text(encoding="utf-8")
        self.assertIn("get_scm_dashboard_data", html)
        self.assertEqual(
            set(re.findall(r'id=["\']([^"\']+)', legacy)),
            set(re.findall(r'id=["\']([^"\']+)', html)),
        )
        functions = lambda text: set(re.findall(r"function\s+([A-Za-z_$][\w$]*)\s*\(", text))
        self.assertTrue(functions(legacy).issubset(functions(html)))
        node = shutil.which("node")
        if not node:
            return
        scripts = re.findall(r"<script[^>]*>(.*?)</script>", html, flags=re.DOTALL | re.IGNORECASE)
        with tempfile.NamedTemporaryFile("w", suffix=".js", encoding="utf-8", delete=False) as handle:
            handle.write("\n".join(scripts))
            path = Path(handle.name)
        try:
            result = subprocess.run([node, "--check", str(path)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
        finally:
            path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
