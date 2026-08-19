from __future__ import annotations
import hashlib
import keyring
import tkinter as tk
from tkinter import simpledialog

from .config import SUPABASE_KEYRING_CANDIDATES, OPENAI_KEYRING

def _ask_secret(title: str, message: str) -> str:
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    try:
        value = simpledialog.askstring(title, message, show="*", parent=root)
        if not value:
            raise RuntimeError(f"{title} 입력이 취소되었습니다.")
        return value.strip()
    finally:
        root.destroy()

def get_supabase_secret_key() -> str:
    for service, account in SUPABASE_KEYRING_CANDIDATES:
        value = keyring.get_password(service, account)
        if value:
            return value.strip()

    value = _ask_secret(
        "Supabase Secret Key",
        "Supabase API Keys 화면의 Secret key(sb_secret_...)를 입력해 주세요.\n"
        "Windows 자격 증명 관리자에 안전하게 저장됩니다.",
    )
    if not value.startswith("sb_secret_"):
        raise ValueError("Supabase Secret Key 형식이 올바르지 않습니다.")
    keyring.set_password(
        "미래엔_출판마케팅_운영시스템",
        "SUPABASE_SECRET_KEY",
        value,
    )
    return value

def get_openai_api_key() -> str:
    service, account = OPENAI_KEYRING
    value = keyring.get_password(service, account)
    if value:
        return value.strip()

    value = _ask_secret(
        "OpenAI API Key",
        "OpenAI API 플랫폼에서 생성한 Secret Key(sk-...)를 입력해 주세요.\n"
        "Windows 자격 증명 관리자에 안전하게 저장됩니다.",
    )
    if not value.startswith("sk-"):
        raise ValueError("OpenAI API Key 형식이 올바르지 않습니다.")
    keyring.set_password(service, account, value)
    return value

def sha256_file(path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
