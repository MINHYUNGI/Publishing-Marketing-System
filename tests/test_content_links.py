from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from app.content_metrics import platform_from_url, youtube_statistics, youtube_video_id

from tests.fakes import database_with


class _UrlResponse:
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return json.dumps(
            {
                "items": [
                    {
                        "statistics": {"viewCount": "123", "likeCount": "45", "commentCount": "6"},
                        "snippet": {"channelTitle": "채널", "title": "영상"},
                    }
                ]
            }
        ).encode()


class ContentLinkTests(unittest.TestCase):
    def test_platform_and_youtube_id_parsing(self):
        self.assertEqual(platform_from_url("https://youtu.be/abc123"), "YouTube")
        self.assertEqual(platform_from_url("https://www.instagram.com/p/1"), "Instagram")
        self.assertEqual(youtube_video_id("https://youtube.com/watch?v=abc123"), "abc123")
        self.assertEqual(youtube_video_id("https://youtube.com/shorts/short1"), "short1")
        self.assertIsNone(youtube_video_id("https://example.com/watch?v=abc123"))

    @patch("app.content_metrics.get_youtube_api_key", return_value="test-key")
    @patch("app.content_metrics.urlopen", return_value=_UrlResponse())
    def test_youtube_statistics_parsing(self, _urlopen, _key):
        result = youtube_statistics("https://youtu.be/abc123")
        self.assertEqual(result["조회수"], 123)
        self.assertEqual(result["좋아요수"], 45)
        self.assertEqual(result["댓글수"], 6)
        self.assertEqual(result["채널명"], "채널")
        self.assertEqual(result["콘텐츠명"], "영상")

    @patch("app.database.youtube_statistics", return_value={"조회수": 10, "좋아요수": 2})
    def test_execution_save_persists_order_and_content_links(self, _statistics):
        database = database_with({"마케팅실행활동": [], "콘텐츠성과": []})
        result = database.save_execution_group(
            "P1",
            "SNS·바이럴",
            [
                {
                    "original_activity_id": "activity-1",
                    "activity_name": "영상 공개",
                    "channel_or_media": "유튜브",
                    "actual_start_date": "2026-08-20",
                    "actual_cost": 500000,
                    "execution_type": "실행확인",
                    "sort_order": 30,
                    "links": ["youtu.be/abc123"],
                }
            ],
            "user-1",
        )
        self.assertEqual(result["saved"], 1)
        self.assertEqual(result["youtube_collected"], 1)
        execution = database.client.tables["마케팅실행활동"][0]
        self.assertEqual(execution["정렬순서"], 30)
        content = database.client.tables["콘텐츠성과"][0]
        self.assertEqual(content["URL"], "https://youtu.be/abc123")
        self.assertEqual(content["실행활동ID"], execution["실행활동ID"])
        self.assertEqual(content["조회수"], 10)

    def test_execution_save_updates_existing_activity(self):
        database = database_with(
            {
                "마케팅실행활동": [
                    {
                        "실행활동ID": "execution-1",
                        "원본활동ID": "activity-1",
                        "제품코드": "P1",
                        "활동분류": "SNS·바이럴",
                        "활동명": "기존 이름",
                        "실제비용": 100,
                        "생성일시": "2026-08-01",
                    }
                ],
                "콘텐츠성과": [],
            }
        )
        result = database.save_execution_group(
            "P1",
            "SNS·바이럴",
            [
                {
                    "execution_activity_id": "execution-1",
                    "original_activity_id": "activity-1",
                    "activity_name": "수정된 이름",
                    "actual_cost": 250000,
                    "sort_order": 40,
                    "links": [],
                }
            ],
        )
        self.assertEqual(result["saved"], 1)
        self.assertEqual(len(database.client.tables["마케팅실행활동"]), 1)
        row = database.client.tables["마케팅실행활동"][0]
        self.assertEqual(row["활동명"], "수정된 이름")
        self.assertEqual(row["실제비용"], 250000)
        self.assertEqual(row["정렬순서"], 40)


if __name__ == "__main__":
    unittest.main()
