from __future__ import annotations

import json
import re
import uuid
from typing import Any
import keyring

SERVICE = "mirae-n-publishing-marketing-scm"
ACCOUNTS = {"KYOBO":"교보문고","YPBOOKS":"영풍문고","YES24_CHILD":"YES24 아동","YES24_ADULT":"YES24 성인","ALADIN_CHILD":"알라딘 아동","ALADIN_ADULT":"알라딘 성인"}
DEFAULT_URLS = {"KYOBO":"https://scm.kyobobook.co.kr/","YPBOOKS":"https://ypscm.ypbooks.co.kr/Account/Logout","YES24_CHILD":"https://scm.yes24.com/","YES24_ADULT":"https://scm.yes24.com/","ALADIN_CHILD":"https://www.aladin.co.kr/supplier/wStatSalesBook.aspx","ALADIN_ADULT":"https://www.aladin.co.kr/supplier/wStatSalesBook.aspx"}

def _read(name: str, default: Any) -> Any:
    value = keyring.get_password(SERVICE, name)
    if not value: return default
    try: return json.loads(value)
    except Exception: return default

def _write(name: str, value: Any) -> None:
    keyring.set_password(SERVICE, name, json.dumps(value, ensure_ascii=False))

def save_account(key: str, login_id: str, password: str = "", url: str = "") -> dict[str, Any]:
    key = str(key or "").upper()
    if key not in ACCOUNTS: raise ValueError("알 수 없는 SCM 계정입니다.")
    current = _read(f"account:{key}", {}); login_id = str(login_id or "").strip()
    if not login_id: raise ValueError("아이디를 입력해주세요.")
    if not password and not current.get("password"): raise ValueError("비밀번호를 입력해주세요.")
    _write(f"account:{key}", {"login_id":login_id,"password":str(password) if password else current["password"],"url":str(url or current.get("url") or DEFAULT_URLS[key]).strip()})
    return {"ok": True}

def get_account(key: str) -> dict[str, str]:
    key = str(key).upper(); value = _read(f"account:{key}", {})
    if not value.get("login_id") or not value.get("password"): raise RuntimeError(f"{ACCOUNTS.get(key,key)} 접속 정보가 저장되어 있지 않습니다.")
    return value

def save_recipient(name: str, phone: str, recipient_id: str = "") -> dict[str, Any]:
    name = str(name or "").strip(); phone = re.sub(r"\D", "", str(phone or ""))
    if not name: raise ValueError("인증 수신자 이름을 입력해주세요.")
    if len(phone) not in (10,11): raise ValueError("휴대폰 번호를 확인해주세요.")
    rows = _read("yes24:recipients", []); rid = recipient_id or str(uuid.uuid4()); record={"id":rid,"name":name,"phone":phone}
    found=False
    for i,row in enumerate(rows):
        if row.get("id")==rid: rows[i]=record; found=True
    if not found: rows.append(record)
    _write("yes24:recipients", rows); return {"ok":True,"id":rid}

def delete_recipient(recipient_id: str) -> dict[str, Any]:
    _write("yes24:recipients", [r for r in _read("yes24:recipients",[]) if r.get("id")!=recipient_id]); return {"ok":True}

def get_recipient(recipient_id: str) -> dict[str, str]:
    for row in _read("yes24:recipients",[]):
        if row.get("id")==recipient_id: return row
    raise RuntimeError("YES24 인증 수신자를 선택해주세요.")

def public_settings() -> dict[str, Any]:
    accounts=[]
    for key,label in ACCOUNTS.items():
        row=_read(f"account:{key}",{})
        accounts.append({"key":key,"label":label,"login_id":row.get("login_id",""),"url":row.get("url",DEFAULT_URLS[key]),"configured":bool(row.get("login_id") and row.get("password"))})
    recipients=[]
    for row in _read("yes24:recipients",[]):
        phone=str(row.get("phone","")); masked=phone[:3]+"-****-"+phone[-4:] if len(phone)>=7 else "****"
        recipients.append({"id":row.get("id"),"name":row.get("name"),"phone_masked":masked})
    return {"ok":True,"accounts":accounts,"recipients":recipients}
