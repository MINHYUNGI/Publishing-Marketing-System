from __future__ import annotations

import json
from datetime import date
from typing import Any
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

from .database import Database
from .security import get_x_bearer_token


def _x_post_id(url: str) -> str | None:
    parsed = urlparse(url)
    host = (parsed.netloc or "").lower().replace("www.", "")
    if host not in {"x.com", "twitter.com", "mobile.twitter.com"} and not host.endswith(".x.com"):
        return None
    parts = [p for p in parsed.path.split("/") if p]
    if "status" not in parts:
        return None
    i = parts.index("status")
    if i + 1 >= len(parts):
        return None
    value = parts[i + 1]
    return value if value.isdigit() else None


def _fetch_x_post(url: str, prompt_if_missing: bool = False) -> dict[str, Any] | None:
    post_id = _x_post_id(url)
    if not post_id:
        return None
    token = get_x_bearer_token(prompt_if_missing=prompt_if_missing)
    if not token:
        return None

    query = urlencode({
        "tweet.fields": "created_at,public_metrics,author_id",
        "expansions": "author_id",
        "user.fields": "name,username",
    })
    req = Request(
        f"https://api.x.com/2/tweets/{post_id}?{query}",
        headers={
            "Authorization": f"Bearer {token}",
            "User-Agent": "MiraeN-Publishing-Marketing-System/1.0",
        },
    )
    with urlopen(req, timeout=12) as response:
        payload = json.loads(response.read().decode("utf-8"))

    post = payload.get("data") or {}
    if not post:
        return None
    public = post.get("public_metrics") or {}
    users = (payload.get("includes") or {}).get("users") or []
    author = users[0] if users else {}
    name = str(author.get("name") or author.get("username") or "").strip()
    username = str(author.get("username") or "").strip()
    channel = name or username or None
    if channel and username and channel != username:
        channel = f"{channel} (@{username})"
    created_at = str(post.get("created_at") or "").strip()

    return {
        "채널명": channel,
        "콘텐츠명": str(post.get("text") or "").strip() or None,
        "게시일": created_at[:10] if created_at else None,
        "조회수": int(public["impression_count"]) if public.get("impression_count") is not None else None,
        "좋아요수": int(public["like_count"]) if public.get("like_count") is not None else None,
        "댓글수": int(public["reply_count"]) if public.get("reply_count") is not None else None,
    }


def install_x_content_runtime() -> None:
    original_save = Database.save_execution_group
    original_fetch = Database.fetch_post_launch_performance
    if getattr(original_save, "_x_content_patched", False):
        return

    def _refresh_rows(self: Database, product_code: str, prompt_if_missing: bool) -> tuple[int, int]:
        rows = (
            self.client.table("콘텐츠성과")
            .select("콘텐츠성과ID,플랫폼,URL,채널명,콘텐츠명,게시일,조회수,좋아요수,댓글수,원천구분")
            .eq("제품코드", product_code)
            .eq("플랫폼", "X")
            .eq("원천구분", "실행링크")
            .execute()
        ).data or []
        if not rows:
            return 0, 0

        collected = 0
        failed = 0
        prompted = False
        for row in rows:
            url = str(row.get("URL") or "").strip()
            if not url:
                continue
            try:
                values = _fetch_x_post(url, prompt_if_missing=prompt_if_missing and not prompted)
                prompted = True
                if not values:
                    failed += 1
                    continue
                updates = {k: v for k, v in values.items() if v is not None}
                updates["지표수집일"] = date.today().isoformat()
                updates["비고"] = None
                self.client.table("콘텐츠성과").update(updates).eq("콘텐츠성과ID", row["콘텐츠성과ID"]).execute()
                collected += 1
            except Exception as exc:
                prompted = True
                failed += 1
                try:
                    self.client.table("콘텐츠성과").update({
                        "비고": f"X 지표 수집 실패: {exc}",
                        "지표수집일": date.today().isoformat(),
                    }).eq("콘텐츠성과ID", row["콘텐츠성과ID"]).execute()
                except Exception:
                    pass
        return collected, failed

    def save_with_x(self: Database, product_code: str, activity_category: str, items: list[dict[str, Any]], registrar_id: str | None = None):
        result = original_save(self, product_code, activity_category, items, registrar_id)
        if "SNS" in activity_category or "바이럴" in activity_category:
            collected, failed = _refresh_rows(self, product_code, prompt_if_missing=True)
            if isinstance(result, dict):
                result["x_collected"] = collected
                result["x_failed"] = failed
        return result

    def fetch_with_x(self: Database, product_code: str):
        # 저장된 Bearer Token이 있을 때만 조용히 최신 지표를 갱신합니다.
        if get_x_bearer_token(prompt_if_missing=False):
            _refresh_rows(self, product_code, prompt_if_missing=False)
        return original_fetch(self, product_code)

    save_with_x._x_content_patched = True
    Database.save_execution_group = save_with_x
    Database.fetch_post_launch_performance = fetch_with_x
