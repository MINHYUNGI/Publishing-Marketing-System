from __future__ import annotations
import logging
import sys
import tkinter as tk
from tkinter import messagebox
import webview

from .backend import Backend
from .config import UI_FILE, DOCUMENT_ROOT, LOG_DIR, REPORT_DIR
from .erp_import import choose_and_import_erp
from .erp_performance_patch import apply_erp_performance_patch
from .logging_utils import configure_logging


def _import_erp_monthly_excel(self) -> dict:
    return choose_and_import_erp(self)


# pywebview JS API에 ERP 업로드 기능을 노출합니다.
Backend.import_erp_monthly_excel = _import_erp_monthly_excel
# 출간 후 성과 조회에 ERP 월별 판매실적을 결합합니다.
apply_erp_performance_patch()


def main() -> None:
    configure_logging()
    for path in (DOCUMENT_ROOT, LOG_DIR, REPORT_DIR):
        path.mkdir(parents=True, exist_ok=True)

    backend = Backend()
    window = webview.create_window(
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
