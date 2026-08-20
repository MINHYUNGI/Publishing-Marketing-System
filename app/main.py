from __future__ import annotations

import logging
import os
import subprocess
import sys
import tempfile
import threading
import time
import tkinter as tk
import uuid
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
    ready_file = Path(tempfile.gettempdir()) / f"MiraeN_Publishing_Marketing_{uuid.uuid4().hex}.ready"
    try:
        root = Path(__file__).resolve().parent.parent
        run_script = root / "run.ps1"
        if not run_script.exists():
            raise RuntimeError("run.ps1을 찾을 수 없습니다.")
        ready_file.unlink(missing_ok=True)
        env = os.environ.copy()
        env["MIRAEN_READY_FILE"] = str(ready_file)
        flags = getattr(subprocess, "CREATE_NEW_CONSOLE", 0) or getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        proc = subprocess.Popen(
            ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(run_script)],
            cwd=str(root), env=env, creationflags=flags,
        )
        logging.info("최신 버전 새 실행 요청: pid=%s, ready=%s", proc.pid, ready_file)
        deadline = time.monotonic() + 120
        while time.monotonic() < deadline:
            if ready_file.exists():
                logging.info("새 프로그램 창 표시 확인 완료: %s", ready_file)
                def close_old_app() -> None:
                    time.sleep(1.0)
                    try:
                        ready_file.unlink(missing_ok=True)
                    finally:
                        os._exit(0)
                threading.Thread(target=close_old_app, daemon=True).start()
                return {"ok": True, "message": "최신 버전 창을 열었습니다."}
            code = proc.poll()
            if code is not None:
                raise RuntimeError(f"새 프로그램이 준비되기 전에 종료되었습니다. 종료 코드: {code}")
            time.sleep(0.4)
        raise TimeoutError("최신 버전 창이 120초 안에 열리지 않았습니다. 기존 프로그램은 그대로 유지됩니다.")
    except Exception as exc:
        logging.exception("최신 버전 재시작 실패")
        ready_file.unlink(missing_ok=True)
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
