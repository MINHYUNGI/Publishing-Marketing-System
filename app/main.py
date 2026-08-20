from __future__ import annotations
import logging
import os
import subprocess
import sys
import threading
import time
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import messagebox
from urllib.parse import urlparse
import webview

from .backend import Backend
from .config import UI_FILE, DOCUMENT_ROOT, LOG_DIR, REPORT_DIR
from .erp_import import choose_and_import_erp
from .erp_performance_patch import apply_erp_performance_patch
from .execution_runtime import install_execution_runtime
from .execution_sort_runtime import install_execution_sort_runtime
from .content_link_runtime import install_content_link_runtime
from .logging_utils import configure_logging


def _import_erp_daily_excel(self, product_code: str | None = None) -> dict:
    return choose_and_import_erp(self, product_code)


def _open_external_url(self, url: str) -> dict:
    # 과거 호환용. SNS 콘텐츠는 pywebview 공식 target=_blank 외부 링크 기능을 사용합니다.
    value = str(url or "").strip()
    try:
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("올바른 웹 링크가 아닙니다.")
        if os.name == "nt":
            os.startfile(value)  # type: ignore[attr-defined]
        else:
            webbrowser.open(value, new=2, autoraise=True)
        return {"ok": True}
    except Exception as exc:
        logging.exception("외부 링크 열기 실패")
        return {"ok": False, "message": str(exc)}


def _restart_latest_version(self) -> dict:
    try:
        root = Path(__file__).resolve().parent.parent
        run_script = root / "run.ps1"
        if not run_script.exists():
            raise RuntimeError("run.ps1을 찾을 수 없습니다.")
        flags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        subprocess.Popen(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(run_script)], cwd=str(root), creationflags=flags)
        def exit_current() -> None:
            time.sleep(0.7)
            os._exit(0)
        threading.Thread(target=exit_current, daemon=True).start()
        return {"ok": True}
    except Exception as exc:
        logging.exception("최신 버전 재시작 실패")
        return {"ok": False, "message": str(exc)}


Backend.import_erp_daily_excel = _import_erp_daily_excel
Backend.import_erp_monthly_excel = lambda self: choose_and_import_erp(self, None)
Backend.open_external_url = _open_external_url
Backend.restart_latest_version = _restart_latest_version
apply_erp_performance_patch()
install_execution_runtime()
install_execution_sort_runtime()
install_content_link_runtime()


def main() -> None:
    configure_logging()
    for path in (DOCUMENT_ROOT, LOG_DIR, REPORT_DIR):
        path.mkdir(parents=True, exist_ok=True)

    # pywebview 공식 설정: target="_blank" 링크를 앱 내부가 아니라 Windows 기본 브라우저에서 엽니다.
    webview.settings["OPEN_EXTERNAL_LINKS_IN_BROWSER"] = True

    backend = Backend()
    webview.create_window(
        "출판 마케팅 운영 시스템",
        url=UI_FILE.as_uri(),
        js_api=backend,
        width=1500,
        height=930,
        min_size=(1100, 720),
    )
    webview.start(debug=False)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        logging.exception("치명적 오류")
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("실행 실패", str(exc), parent=root)
        root.destroy()
        sys.exit(1)
