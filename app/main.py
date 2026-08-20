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
    """등록된 콘텐츠 URL을 Windows 기본 브라우저에서 엽니다."""
    value = str(url or "").strip()
    try:
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("올바른 웹 링크가 아닙니다.")
        logging.info("외부 링크 열기 요청: %s", value)
        if os.name == "nt":
            os.startfile(value)  # type: ignore[attr-defined]
        elif not webbrowser.open(value, new=2, autoraise=True):
            raise RuntimeError("기본 브라우저를 열 수 없습니다.")
        return {"ok": True}
    except Exception as exc:
        logging.exception("외부 링크 열기 실패")
        return {"ok": False, "message": str(exc)}


def _restart_latest_version(self) -> dict:
    """새 창이 실제로 표시된 뒤에만 현재 프로그램을 종료합니다."""
    try:
        root = Path(__file__).resolve().parent.parent
        restart_script = root / "restart_latest.ps1"
        if not restart_script.exists():
            raise RuntimeError("restart_latest.ps1을 찾을 수 없습니다.")
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        proc = subprocess.Popen(
            [
                "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
                "-File", str(restart_script), "-ProjectDir", str(root),
            ],
            cwd=str(root),
            creationflags=flags,
        )
        logging.info("최신 버전 재시작 helper 실행: pid=%s", proc.pid)

        def finish_restart() -> None:
            code = proc.wait()
            if code == 0:
                logging.info("새 프로그램 창 표시 확인 완료. 기존 프로그램을 종료합니다.")
                time.sleep(1.0)
                os._exit(0)
            logging.error("최신 버전 재시작 helper 실패: exit=%s. 기존 프로그램을 유지합니다.", code)

        threading.Thread(target=finish_restart, daemon=True).start()
        return {"ok": True, "message": "최신 버전을 확인하고 다시 시작하고 있습니다."}
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

    if not UI_FILE.exists():
        raise FileNotFoundError(f"UI 파일을 찾을 수 없습니다: {UI_FILE}")

    backend = Backend()
    window = webview.create_window(
        "출판 마케팅 운영 시스템",
        url=UI_FILE.as_uri(),
        js_api=backend,
        width=1500,
        height=930,
        min_size=(1100, 720),
    )

    ready_path = os.environ.get("MIRAEN_READY_FILE")
    if ready_path:
        def mark_ready(*_args) -> None:
            try:
                Path(ready_path).write_text(
                    f"pid={os.getpid()}\nshown={time.time()}\n",
                    encoding="utf-8",
                )
                logging.info("재시작 준비 신호 기록: %s", ready_path)
            except Exception:
                logging.exception("재시작 준비 신호 기록 실패")
        window.events.shown += mark_ready

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
