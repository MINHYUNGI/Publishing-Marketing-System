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


def _browser_candidates() -> list[tuple[str, Path]]:
    """Windows에서 Chrome을 우선하고 Edge를 보조로 찾습니다."""
    candidates: list[tuple[str, Path]] = []
    local = os.environ.get("LOCALAPPDATA")
    pf = os.environ.get("PROGRAMFILES")
    pfx86 = os.environ.get("PROGRAMFILES(X86)")
    if local:
        candidates.append(("Chrome", Path(local) / "Google" / "Chrome" / "Application" / "chrome.exe"))
    if pf:
        candidates.append(("Chrome", Path(pf) / "Google" / "Chrome" / "Application" / "chrome.exe"))
    if pfx86:
        candidates.append(("Chrome", Path(pfx86) / "Google" / "Chrome" / "Application" / "chrome.exe"))
    if pf:
        candidates.append(("Edge", Path(pf) / "Microsoft" / "Edge" / "Application" / "msedge.exe"))
    if pfx86:
        candidates.append(("Edge", Path(pfx86) / "Microsoft" / "Edge" / "Application" / "msedge.exe"))
    return candidates


def _launch_external_browser(url: str) -> tuple[bool, str]:
    value = str(url or "").strip()
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return False, "올바른 웹 링크가 아닙니다."

    for name, exe in _browser_candidates():
        if exe.exists():
            try:
                subprocess.Popen([str(exe), "--new-window", value], close_fds=True)
                logging.info("외부 링크 %s 새 창 실행: %s", name, value)
                return True, name
            except Exception:
                logging.exception("%s 새 창 실행 실패: %s", name, value)

    try:
        if os.name == "nt":
            os.startfile(value)  # type: ignore[attr-defined]
            logging.info("외부 링크 Windows 기본 브라우저 실행: %s", value)
            return True, "기본 브라우저"
    except Exception:
        logging.exception("Windows 기본 브라우저 실행 실패: %s", value)

    try:
        if webbrowser.open(value, new=2, autoraise=True):
            logging.info("외부 링크 webbrowser 실행: %s", value)
            return True, "기본 브라우저"
    except Exception:
        logging.exception("webbrowser 실행 실패: %s", value)
    return False, "브라우저를 실행할 수 없습니다."


def _open_external_url(self, url: str) -> dict:
    """기존 JS API 호출 경로도 Chrome 우선 실행 방식으로 통일합니다."""
    value = str(url or "").strip()
    logging.info("외부 링크 열기 요청: %s", value)
    ok, detail = _launch_external_browser(value)
    return {"ok": ok, "message": "" if ok else detail, "browser": detail if ok else ""}


def _open_content_links_native(self, product_code: str | None = None) -> dict:
    # 과거 호환용. 새 UI에서는 사용하지 않습니다.
    return {"ok": False, "message": "콘텐츠 제목의 하이퍼링크를 사용해 주세요."}


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
    home_url = UI_FILE.as_uri()
    window = webview.create_window(
        "출판 마케팅 운영 시스템",
        url=home_url,
        js_api=backend,
        width=1500,
        height=930,
        min_size=(1100, 720),
    )

    # 일반 HTML 하이퍼링크가 현재 pywebview를 외부 사이트로 이동시키면,
    # JS 이벤트를 사용하지 않고 Python이 실제 이동된 URL을 감지해 Chrome 새 창으로 넘깁니다.
    navigation_guard = {"handling": False}

    def on_loaded() -> None:
        if navigation_guard["handling"]:
            return
        try:
            current = str(window.get_current_url() or "")
            parsed = urlparse(current)
            if parsed.scheme not in {"http", "https"}:
                return
            navigation_guard["handling"] = True
            logging.info("웹뷰 외부 이동 감지: %s", current)
            ok, browser = _launch_external_browser(current)
            if not ok:
                logging.error("웹뷰 외부 이동 브라우저 실행 실패: %s", current)
            else:
                logging.info("웹뷰 외부 이동 → %s 새 창 전환 완료", browser)
            # 외부 페이지를 앱 내부에 남겨두지 않고 즉시 앱 화면으로 복귀합니다.
            window.load_url(home_url)
        except Exception:
            logging.exception("웹뷰 외부 이동 처리 실패")
        finally:
            # load_url(home_url)의 loaded 이벤트가 뒤이어 오므로 약간 늦게 해제합니다.
            def release_guard():
                time.sleep(0.8)
                navigation_guard["handling"] = False
            threading.Thread(target=release_guard, daemon=True).start()

    window.events.loaded += on_loaded
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
