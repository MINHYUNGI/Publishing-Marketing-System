from __future__ import annotations

import logging
import os
import sys
import time
import tkinter as tk
from pathlib import Path
from tkinter import messagebox

import webview

from .backend import Backend
from .config import UI_FILE, DOCUMENT_ROOT, LOG_DIR, REPORT_DIR
from .logging_utils import configure_logging


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
