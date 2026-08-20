from __future__ import annotations

import json
from datetime import date
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import Request, urlopen

from .database import Database
from .security import get_youtube_api_key


def _platform_from_url(url: str) -> str:
    host = (urlparse(url).netloc or "").lower().replace("www.", "")
    if "youtube.com" in host or "youtu.be" in host:
        return "YouTube"
    if "instagram.com" in host:
        return "Instagram"
    if host in {"x.com", "twitter.com"} or host.endswith(".x.com") or host.endswith(".twitter.com"):
        return "X"
    if "blog.naver.com" in host:
        return "네이버 블로그"
    if "cafe.naver.com" in host:
        return "네이버 카페"
    if "tiktok.com" in host:
        return "TikTok"
    if "threads.net" in host:
        return "Threads"
    if "facebook.com" in host:
        return "Facebook"
    return host or "웹"


def _youtube_video_id(url: str) -> str | None:
    parsed = urlparse(url)
    host = (parsed.netloc or "").lower().replace("www.", "")
    if host == "youtu.be":
        value = parsed.path.strip("/").split("/")[0]
        return value or None
    if "youtube.com" not in host:
        return None
    if parsed.path == "/watch":
        value = (parse_qs(parsed.query).get("v") or [None])[0]
        return str(value) if value else None
    parts = [p for p in parsed.path.split("/") if p]
    if len(parts) >= 2 and parts[0] in {"shorts", "embed", "live"}:
        return parts[1]
    return None


def _youtube_statistics(url: str, prompt_if_missing: bool = False) -> dict[str, int] | None:
    video_id = _youtube_video_id(url)
    if not video_id:
        return None
    key = get_youtube_api_key(prompt_if_missing=prompt_if_missing)
    if not key:
        return None
    query = urlencode({"part": "statistics", "id": video_id, "key": key})
    req = Request(
        "https://www.googleapis.com/youtube/v3/videos?" + query,
        headers={"User-Agent": "MiraeN-Publishing-Marketing-System/1.0"},
    )
    with urlopen(req, timeout=12) as response:
        payload = json.loads(response.read().decode("utf-8"))
    items = payload.get("items") or []
    if not items:
        return None
    stats = items[0].get("statistics") or {}
    return {
        "조회수": int(stats["viewCount"]) if stats.get("viewCount") is not None else None,
        "좋아요수": int(stats["likeCount"]) if stats.get("likeCount") is not None else None,
        "댓글수": int(stats["commentCount"]) if stats.get("commentCount") is not None else None,
    }


def install_content_link_runtime() -> None:
    if not hasattr(Database, "save_execution_group"):
        return
    original_save = Database.save_execution_group
    original_fetch = Database.fetch_post_launch_performance
    if getattr(original_save, "_content_link_patched", False):
        return

    def _find_execution_id(self: Database, product_code: str, activity_category: str, item: dict[str, Any]) -> str | None:
        if item.get("execution_activity_id"):
            return str(item["execution_activity_id"])
        original_id = item.get("original_activity_id")
        if original_id:
            rows = (self.client.table("마케팅실행활동")
                    .select("실행활동ID")
                    .eq("제품코드", product_code)
                    .eq("원본활동ID", original_id)
                    .limit(1).execute()).data or []
            return str(rows[0]["실행활동ID"]) if rows else None
        db_category = "기타 추가 마케팅" if activity_category == "추가 마케팅" else activity_category
        q = (self.client.table("마케팅실행활동")
             .select("실행활동ID")
             .eq("제품코드", product_code)
             .eq("활동분류", db_category)
             .eq("활동명", str(item.get("activity_name") or "").strip())
             .is_("원본활동ID", "null")
             .order("생성일시", desc=True)
             .limit(1).execute())
        rows = q.data or []
        return str(rows[0]["실행활동ID"]) if rows else None

    def save_with_links(self: Database, product_code: str, activity_category: str, items: list[dict[str, Any]], registrar_id: str | None = None):
        result = original_save(self, product_code, activity_category, items, registrar_id)
        if "SNS" not in activity_category and "바이럴" not in activity_category:
            return result

        youtube_prompted = False
        youtube_collected = 0
        youtube_failed = 0

        for item in items or []:
            if item.get("delete_added"):
                continue
            original_id = item.get("original_activity_id") or None
            execution_id = _find_execution_id(self, product_code, activity_category, item)

            delete_q = (self.client.table("콘텐츠성과").delete()
                        .eq("제품코드", product_code)
                        .eq("원천구분", "실행링크"))
            if original_id:
                delete_q = delete_q.eq("활동ID", original_id)
            elif execution_id:
                delete_q = delete_q.eq("실행활동ID", execution_id)
            else:
                continue
            delete_q.execute()

            if item.get("execution_type") == "활동취소":
                continue

            links = item.get("links") or []
            for idx, raw in enumerate(links, start=1):
                url = str(raw or "").strip()
                if not url:
                    continue
                if not url.lower().startswith(("http://", "https://")):
                    url = "https://" + url
                platform = _platform_from_url(url)
                row = {
                    "제품코드": product_code,
                    "활동ID": original_id,
                    "실행활동ID": execution_id,
                    "플랫폼": platform,
                    "채널명": item.get("channel_or_media") or None,
                    "콘텐츠명": str(item.get("activity_name") or "SNS·바이럴 콘텐츠").strip(),
                    "게시일": item.get("actual_start_date") or None,
                    "URL": url,
                    "지표수집일": date.today().isoformat(),
                    "원천구분": "실행링크",
                    "링크순서": idx * 10,
                }
                if platform == "YouTube":
                    try:
                        metrics = _youtube_statistics(url, prompt_if_missing=not youtube_prompted)
                        youtube_prompted = True
                        if metrics:
                            row.update(metrics)
                            youtube_collected += 1
                        else:
                            youtube_failed += 1
                    except Exception as exc:
                        youtube_prompted = True
                        youtube_failed += 1
                        row["비고"] = f"YouTube 지표 수집 실패: {exc}"
                self.client.table("콘텐츠성과").insert(row).execute()

        if isinstance(result, dict):
            result["youtube_collected"] = youtube_collected
            result["youtube_failed"] = youtube_failed
        return result

    def _refresh_youtube_rows(self: Database, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        key = get_youtube_api_key(prompt_if_missing=False)
        if not key:
            return rows
        for row in rows:
            if row.get("원천구분") != "실행링크" or row.get("플랫폼") != "YouTube" or not row.get("URL"):
                continue
            try:
                metrics = _youtube_statistics(str(row["URL"]), prompt_if_missing=False)
                if not metrics:
                    continue
                changed = any(row.get(k) != v for k, v in metrics.items())
                row.update(metrics)
                row["지표수집일"] = date.today().isoformat()
                if changed or not row.get("조회수"):
                    self.client.table("콘텐츠성과").update({
                        **metrics,
                        "지표수집일": date.today().isoformat(),
                        "비고": None,
                    }).eq("콘텐츠성과ID", row["콘텐츠성과ID"]).execute()
            except Exception:
                continue
        return rows

    def fetch_with_links(self: Database, product_code: str):
        detail = original_fetch(self, product_code)
        if not detail:
            return detail
        rows = (self.client.table("콘텐츠성과")
                .select("콘텐츠성과ID,제품코드,활동ID,실행활동ID,플랫폼,채널명,콘텐츠명,게시일,URL,조회수,좋아요수,댓글수,공유수,저장수,클릭수,지표수집일,원천구분,비고,링크순서")
                .eq("제품코드", product_code)
                .order("링크순서")
                .order("생성일시")
                .execute()).data or []
        rows = _refresh_youtube_rows(self, rows)
        detail["콘텐츠성과"] = rows

        by_plan: dict[str, list[dict[str, Any]]] = {}
        by_exec: dict[str, list[dict[str, Any]]] = {}
        for row in rows:
            if row.get("원천구분") != "실행링크":
                continue
            if row.get("활동ID"):
                by_plan.setdefault(str(row["활동ID"]), []).append(row)
            if row.get("실행활동ID"):
                by_exec.setdefault(str(row["실행활동ID"]), []).append(row)

        for item in detail.get("마케팅활동") or []:
            links: list[dict[str, Any]] = []
            if item.get("활동ID"):
                links = by_plan.get(str(item["활동ID"]), [])
            if not links and item.get("실행활동ID"):
                links = by_exec.get(str(item["실행활동ID"]), [])
            item["콘텐츠링크"] = links
        return detail

    save_with_links._content_link_patched = True
    Database.save_execution_group = save_with_links
    Database.fetch_post_launch_performance = fetch_with_links
