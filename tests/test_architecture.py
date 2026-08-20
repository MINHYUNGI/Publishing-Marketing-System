from __future__ import annotations

import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app"


class ArchitectureTests(unittest.TestCase):
    def test_no_runtime_patch_modules_remain(self):
        leftovers = sorted(
            path.name
            for path in APP.glob("*.py")
            if "patch" in path.stem or "runtime" in path.stem
        )
        self.assertEqual(leftovers, [])

    def test_main_has_no_class_monkey_patch_assignments(self):
        tree = ast.parse((APP / "main.py").read_text(encoding="utf-8"))
        assignments = []
        for node in ast.walk(tree):
            if not isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
                continue
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                if isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name):
                    if target.value.id in {"Backend", "Database"}:
                        assignments.append(f"{target.value.id}.{target.attr}")
        self.assertEqual(assignments, [])

    def test_local_ui_and_production_webview_settings_are_preserved(self):
        source = (APP / "main.py").read_text(encoding="utf-8")
        self.assertIn("url=UI_FILE.as_uri()", source)
        self.assertIn("webview.start(debug=False)", source)


if __name__ == "__main__":
    unittest.main()
