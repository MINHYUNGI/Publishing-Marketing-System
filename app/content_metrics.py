from __future__ import annotations

import json
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import Request, urlopen

from .security import get_youtube_api_key


def platform_from_url(url: str) -> str:
    host = (urlparse(url).netloc or "").lower().replace("www.", "")
    if "youtube.com" in host or "youtu.be" in host:
        return "YouTube"
    if "instagram.com" in host:
        return "Instagram"
    if host in {"x.com", "twitter.com"} or host.endswith((".x.com", ".twitter.com")):
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


def youtube_video_id(url: str) -> str | None:
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
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) >= 2 and parts[0] in {"shorts", "embed", "live"}:
        return parts[1]
    return None


def youtube_statistics(url: str, prompt_if_missing: bool = False) -> dict[str, Any] | None:
    video_id = youtube_video_id(url)
    if not video_id:
        return None
    key = get_youtube_api_key(prompt_if_missing=prompt_if_missing)
    if not key:
        return None
    query = urlencode({"part": "statistics,snippet", "id": video_id, "key": key})
    request = Request(
        "https://www.googleapis.com/youtube/v3/videos?" + query,
        headers={"User-Agent": "MiraeN-Publishing-Marketing-System/1.0"},
    )
    with urlopen(request, timeout=12) as response:
        payload = json.loads(response.read().decode("utf-8"))
    items = payload.get("items") or []
    if not items:
        return None
    video = items[0]
    stats = video.get("statistics") or {}
    snippet = video.get("snippet") or {}
    return {
        "조회수": int(stats["viewCount"]) if stats.get("viewCount") is not None else None,
        "좋아요수": int(stats["likeCount"]) if stats.get("likeCount") is not None else None,
        "댓글수": int(stats["commentCount"]) if stats.get("commentCount") is not None else None,
        "채널명": str(snippet.get("channelTitle") or "").strip() or None,
        "콘텐츠명": str(snippet.get("title") or "").strip() or None,
    }
