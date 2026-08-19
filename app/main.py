from __future__ import annotations
import logging
import os
import subprocess
import sys
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import messagebox
import webview

from .backend import Backend
from .config import UI_FILE, DOCUMENT_ROOT, LOG_DIR, REPORT_DIR
from .erp_import import choose_and_import_erp
from .erp_performance_patch import apply_erp_performance_patch
from .logging_utils import configure_logging


def _import_erp_daily_excel(self, product_code: str | None = None) -> dict:
    return choose_and_import_erp(self, product_code)


def _restart_latest_version(self) -> dict:
    """현재 앱을 종료하고 run.ps1을 새 프로세스로 실행해 GitHub 최신본으로 재시작합니다."""
    try:
        root = Path(__file__).resolve().parent.parent
        run_script = root / "run.ps1"
        if not run_script.exists():
            raise RuntimeError("run.ps1을 찾을 수 없습니다.")
        flags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        subprocess.Popen(
            ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(run_script)],
            cwd=str(root),
            creationflags=flags,
        )

        def exit_current() -> None:
            time.sleep(0.7)
            os._exit(0)

        threading.Thread(target=exit_current, daemon=True).start()
        return {"ok": True}
    except Exception as exc:
        logging.exception("최신 버전 재시작 실패")
        return {"ok": False, "message": str(exc)}


# pywebview JS API에 ERP 일별 업로드 기능을 노출합니다.
# 제품코드를 넘기지 않으면 엑셀 내부 제품코드를 자동 감지합니다.
Backend.import_erp_daily_excel = _import_erp_daily_excel
# 하위 호환용 이름도 동일한 자동 감지 로직으로 연결합니다.
Backend.import_erp_monthly_excel = lambda self: choose_and_import_erp(self, None)
Backend.restart_latest_version = _restart_latest_version
# 출간 후 성과 조회에 ERP 일별 판매실적을 결합합니다.
apply_erp_performance_patch()


def main() -> None:
    configure_logging()
    for path in (DOCUMENT_ROOT, LOG_DIR, REPORT_DIR):
        path.mkdir(parents=True, exist_ok=True)

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
