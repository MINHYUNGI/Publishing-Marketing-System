from pathlib import Path

PROJECT_URL = "https://ttqeovahaitfkalbfucl.supabase.co"
OPENAI_MODEL = "gpt-5.6"
MAX_DOCUMENT_TEXT = 50000
PRODUCT_CANDIDATE_COUNT = 25
MAX_FILE_SIZE = 50 * 1024 * 1024

BASE_DIR = Path(__file__).resolve().parents[1]
UI_FILE = BASE_DIR / "ui" / "index.html"
PROMPT_DIR = BASE_DIR / "prompt"
LOG_DIR = BASE_DIR / "logs"
REPORT_DIR = BASE_DIR / "reports"

# 운영 시스템 최상위 폴더 바로 아래 documents에 원본을 저장합니다.
DOCUMENT_ROOT = BASE_DIR.parent / "documents"
# 도서별 참조 이미지/PDF 등은 운영 시스템 공용 data/attachments 아래에 저장합니다.
ATTACHMENT_ROOT = BASE_DIR / "data" / "attachments"
SCM_LEDGER_FILE = Path(r"Y:\출판사업본부\05. 영업 실적\70. 집계 결과\실판매_통합원장.xlsx")
YES24_DOWNLOAD_DIR = Path(r"Y:\출판사업본부\05. 영업 실적\01. 실판매\download")

ALLOWED_EXTENSIONS = {".xlsx", ".xls", ".pdf", ".docx", ".pptx"}

SUPABASE_KEYRING_CANDIDATES = [
    ("미래엔_출판마케팅_운영시스템", "SUPABASE_SECRET_KEY"),
    ("미래엔_출판마케팅_제품인덱스_동기화", "SUPABASE_SECRET_KEY"),
]

OPENAI_KEYRING = (
    "미래엔_출판마케팅_운영시스템",
    "OPENAI_API_KEY",
)

YOUTUBE_API_KEYRING = (
    "미래엔_출판마케팅_운영시스템",
    "YOUTUBE_DATA_API_KEY",
)
