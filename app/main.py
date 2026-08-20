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
    value = str(url or "").strip()
    logging.info("외부 링크 열기 요청: %s", value)
    try:
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("올바른 웹 링크가 아닙니다.")
        if os.name == "nt":
            try:
                os.startfile(value)  # type: ignore[attr-defined]
                logging.info("외부 링크 열기 성공(os.startfile): %s", value)
                return {"ok": True}
            except Exception:
                logging.exception("os.startfile 외부 링크 실행 실패")
        opened = bool(webbrowser.open(value, new=2, autoraise=True))
        if not opened:
            raise RuntimeError("기본 브라우저를 열 수 없습니다.")
        logging.info("외부 링크 열기 성공(webbrowser): %s", value)
        return {"ok": True}
    except Exception as exc:
        logging.exception("외부 링크 열기 실패")
        return {"ok": False, "message": str(exc)}


def _open_content_links_native(self, product_code: str | None = None) -> dict:
    """HTML 동적 링크 버튼을 우회해 Windows 네이티브 선택창에서 콘텐츠 링크를 엽니다."""
    try:
        if not self.db:
            raise RuntimeError("Supabase가 연결되지 않았습니다.")
        code = str(product_code or "").strip()
        if not code:
            raise RuntimeError("조회 중인 도서의 제품코드를 확인할 수 없습니다.")

        rows = (
            self.db.client.table("콘텐츠성과")
            .select("플랫폼,채널명,콘텐츠명,URL,게시일,링크순서")
            .eq("제품코드", code)
            .not_.is_("URL", "null")
            .order("링크순서")
            .execute()
        ).data or []
        rows = [r for r in rows if str(r.get("URL") or "").strip()]
        logging.info("네이티브 콘텐츠 링크 창 요청: 제품=%s, 링크=%s건", code, len(rows))
        if not rows:
            raise RuntimeError("이 도서에 등록된 콘텐츠 링크가 없습니다.")

        root = tk.Tk()
        root.title("콘텐츠 링크 열기")
        root.geometry("820x430")
        root.minsize(650, 320)
        root.attributes("-topmost", True)

        title = tk.Label(root, text="열 콘텐츠를 선택하세요", font=("Segoe UI", 14, "bold"), anchor="w")
        title.pack(fill="x", padx=18, pady=(16, 4))
        guide = tk.Label(root, text=f"제품코드 {code} · 등록 링크 {len(rows)}건", font=("Segoe UI", 10), fg="#667085", anchor="w")
        guide.pack(fill="x", padx=18, pady=(0, 10))

        frame = tk.Frame(root)
        frame.pack(fill="both", expand=True, padx=18)
        scrollbar = tk.Scrollbar(frame)
        scrollbar.pack(side="right", fill="y")
        listbox = tk.Listbox(frame, yscrollcommand=scrollbar.set, font=("Segoe UI", 10), activestyle="none", selectmode="browse")
        listbox.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=listbox.yview)

        for r in rows:
            platform = str(r.get("플랫폼") or "웹").strip()
            channel = str(r.get("채널명") or "").strip()
            content = str(r.get("콘텐츠명") or "콘텐츠").strip().replace("\n", " ")
            if len(content) > 78:
                content = content[:77] + "…"
            date_text = str(r.get("게시일") or "").strip()
            parts = [platform]
            if channel:
                parts.append(channel)
            parts.append(content)
            if date_text:
                parts.append(date_text)
            listbox.insert("end", "  |  ".join(parts))
        listbox.selection_set(0)
        listbox.activate(0)

        status = tk.Label(root, text="항목을 더블클릭하거나 [브라우저에서 열기]를 누르세요.", font=("Segoe UI", 9), fg="#667085", anchor="w")
        status.pack(fill="x", padx=18, pady=(8, 6))

        buttons = tk.Frame(root)
        buttons.pack(fill="x", padx=18, pady=(0, 16))

        def open_selected(event=None):
            selection = listbox.curselection()
            if not selection:
                messagebox.showinfo("콘텐츠 링크", "열 콘텐츠를 선택해 주세요.", parent=root)
                return
            idx = int(selection[0])
            url = str(rows[idx].get("URL") or "").strip()
            result = _open_external_url(self, url)
            if not result.get("ok"):
                messagebox.showerror("링크 열기 실패", result.get("message") or "링크를 열 수 없습니다.", parent=root)
            else:
                status.config(text="브라우저에서 링크를 열었습니다.")

        open_btn = tk.Button(buttons, text="브라우저에서 열기", command=open_selected, width=18)
        open_btn.pack(side="right", padx=(8, 0))
        close_btn = tk.Button(buttons, text="닫기", command=root.destroy, width=10)
        close_btn.pack(side="right")
        listbox.bind("<Double-Button-1>", open_selected)
        root.bind("<Return>", open_selected)
        root.bind("<Escape>", lambda e: root.destroy())
        root.focus_force()
        root.mainloop()
        return {"ok": True, "count": len(rows)}
    except Exception as exc:
        logging.exception("네이티브 콘텐츠 링크 창 실패")
        try:
            root = tk.Tk(); root.withdraw(); root.attributes("-topmost", True)
            messagebox.showerror("콘텐츠 링크", str(exc), parent=root)
            root.destroy()
        except Exception:
            pass
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
Backend.open_content_links_native = _open_content_links_native
Backend.restart_latest_version = _restart_latest_version
apply_erp_performance_patch()
install_execution_runtime()
install_execution_sort_runtime()
install_content_link_runtime()


def main() -> None:
    configure_logging()
    for path in (DOCUMENT_ROOT, LOG_DIR, REPORT_DIR):
        path.mkdir(parents=True, exist_ok=True)
    backend = Backend()
    webview.create_window("출판 마케팅 운영 시스템", url=UI_FILE.as_uri(), js_api=backend, width=1500, height=930, min_size=(1100, 720))
    webview.start(debug=False)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        logging.exception("치명적 오류")
        root = tk.Tk(); root.withdraw(); messagebox.showerror("실행 실패", str(exc), parent=root); root.destroy(); sys.exit(1)
