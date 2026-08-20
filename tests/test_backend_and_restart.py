from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import app.main
from app.backend import Backend


class _ImmediateThread:
    def __init__(self, target, daemon=None):
        self.target = target

    def start(self):
        self.target()


class BackendAndRestartTests(unittest.TestCase):
    def test_existing_plan_lookup_uses_repository(self):
        backend = Backend()
        backend.db = MagicMock()
        backend.product_index = [{"제품코드": "P1", "제품명": "도서"}]
        backend.db.fetch_existing_plan.return_value = {
            "plan": {"제품코드": "P1"},
            "activities": [],
            "document": None,
        }
        backend.db.fetch_sales_goal.return_value = {}
        result = backend.load_existing_plan("P1")
        self.assertTrue(result["ok"])
        backend.db.fetch_existing_plan.assert_called_once_with("P1")

    @patch("app.backend.analyze_document", return_value={"product_code": "P1", "activities": []})
    @patch("app.backend.get_openai_api_key", return_value="test-key")
    def test_ai_document_analysis_core_flow(self, _key, analyze):
        backend = Backend()
        backend.db = MagicMock()
        backend.product_index = [{"제품코드": "P1", "제품명": "도서"}]
        result = backend.analyze_files([{"path": __file__, "product_code": "P1"}])
        self.assertTrue(result["ok"])
        self.assertEqual(len(result["results"]), 1)
        analyze.assert_called_once()

    @patch("app.backend.os.startfile")
    def test_external_link_opens_only_http_urls(self, startfile):
        backend = Backend()
        self.assertTrue(backend.open_external_url("https://example.com/page")["ok"])
        startfile.assert_called_once_with("https://example.com/page")
        self.assertFalse(backend.open_external_url("file:///C:/secret.txt")["ok"])

    @patch("app.backend.threading.Thread", _ImmediateThread)
    @patch("app.backend.os._exit")
    @patch("app.backend.subprocess.Popen")
    def test_restart_failure_keeps_current_app_open(self, popen, exit_process):
        process = MagicMock()
        process.pid = 123
        process.wait.return_value = 1
        popen.return_value = process
        result = Backend().restart_latest_version()
        self.assertTrue(result["ok"])
        exit_process.assert_not_called()

    def test_restart_scripts_require_ready_before_success(self):
        root = Path(__file__).resolve().parents[1]
        helper = (root / "restart_latest.ps1").read_text(encoding="utf-8-sig")
        main = (root / "app" / "main.py").read_text(encoding="utf-8")
        backend = (root / "app" / "backend.py").read_text(encoding="utf-8")
        self.assertIn("Test-Path -LiteralPath $ready", helper)
        self.assertLess(helper.index("Test-Path -LiteralPath $ready"), helper.index("exit 0"))
        self.assertIn("window.events.shown += mark_ready", main)
        self.assertIn("if code == 0:", backend)


if __name__ == "__main__":
    unittest.main()
