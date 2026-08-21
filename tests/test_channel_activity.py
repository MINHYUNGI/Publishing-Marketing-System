from __future__ import annotations

import unittest

from app.channel_activity import build_bookstore_timeline_rows, classify_bookstore, classify_product_category


class ChannelActivityTests(unittest.TestCase):
    def test_bookstore_aliases_are_classified_without_changing_source(self):
        cases = {"교보문고 광화문점":"교보문고", "영풍 스타필드":"영풍문고", "예스24 온라인":"YES24", "yes24":"YES24", "Yes24":"YES24", "알라딘 강남점":"알라딘"}
        for source, expected in cases.items():
            self.assertEqual(classify_bookstore(source), expected)

    def test_category_order_and_publication_date_descending(self):
        activities = [
            {"활동ID":"1","제품코드":"A","채널또는매체":"교보","활동명":"old"},
            {"활동ID":"2","제품코드":"B","채널또는매체":"교보","활동명":"comic"},
            {"활동ID":"3","제품코드":"C","채널또는매체":"교보","활동명":"new"},
            {"활동ID":"4","제품코드":"C","채널또는매체":"교보","활동명":"second"},
        ]
        products = {"A":{"제품명":"A","최종대분류":"아동"}, "B":{"제품명":"B","최종대분류":"만화"}, "C":{"제품명":"C","최종대분류":"아동"}}
        marketing = {"A":{"출간일":"2026-01-01"},"B":{"출간일":"2026-03-01"},"C":{"출간일":"2026-08-20"}}
        rows = build_bookstore_timeline_rows(activities, products, marketing)["교보문고"]
        self.assertEqual([row["제품코드"] for row in rows], ["C", "C", "A", "B"])
        self.assertEqual(classify_product_category("03. 단행본", "경제"), "단행본")
