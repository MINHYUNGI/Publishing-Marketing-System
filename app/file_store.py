from __future__ import annotations
import shutil
import base64
from datetime import datetime
from pathlib import Path
from .config import DOCUMENT_ROOT, ATTACHMENT_ROOT

def sanitize_filename(filename: str) -> str:
    cleaned = "".join(ch for ch in filename if ch not in '<>:"/\\|?*')
    return cleaned.strip().rstrip(".") or "document"

def copy_document(source: Path) -> Path:
    month_dir = DOCUMENT_ROOT / datetime.now().strftime("%Y") / datetime.now().strftime("%m")
    month_dir.mkdir(parents=True, exist_ok=True)
    safe = sanitize_filename(source.name)
    stem, suffix = Path(safe).stem, Path(safe).suffix.lower()
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = month_dir / f"{stamp}_{stem}{suffix}"
    n = 1
    while dest.exists():
        dest = month_dir / f"{stamp}_{stem}_{n}{suffix}"
        n += 1
    shutil.copy2(source, dest)
    return dest


def copy_reference_file(source: Path, product_code: str) -> Path:
    """도서별 참조파일을 Y드라이브 data/attachments/<제품코드>/ 에 복사합니다."""
    product_dir = ATTACHMENT_ROOT / sanitize_filename(str(product_code))
    product_dir.mkdir(parents=True, exist_ok=True)
    safe = sanitize_filename(source.name)
    stem, suffix = Path(safe).stem, Path(safe).suffix.lower()
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = product_dir / f"{stamp}_{stem}{suffix}"
    n = 1
    while dest.exists():
        dest = product_dir / f"{stamp}_{stem}_{n}{suffix}"
        n += 1
    shutil.copy2(source, dest)
    return dest


def save_reference_bytes(data: bytes, original_name: str, product_code: str) -> Path:
    """브라우저 드래그앤드롭으로 전달된 파일 바이트를 제품별 참조폴더에 저장합니다."""
    product_dir = ATTACHMENT_ROOT / sanitize_filename(str(product_code))
    product_dir.mkdir(parents=True, exist_ok=True)
    safe = sanitize_filename(original_name)
    stem, suffix = Path(safe).stem, Path(safe).suffix.lower()
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = product_dir / f"{stamp}_{stem}{suffix}"
    n = 1
    while dest.exists():
        dest = product_dir / f"{stamp}_{stem}_{n}{suffix}"
        n += 1
    dest.write_bytes(data)
    return dest
