from __future__ import annotations

import unittest

from app.channel_activity import build_bookstore_timeline_rows, classify_bookstore, classify_product_category
from app.backend import Backend
from tests.fakes import database_with


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

    def test_backend_adds_store_specific_scm_units_for_activity_period(self):
        class FakeDatabase:
            def fetch_channel_marketing_activities(self):
                return (
                    [{"활동ID":"1","제품코드":"A","채널또는매체":"YES24","활동명":"광고","시작일":"2026-08-01","종료일":"2026-08-03"}],
                    {"A":{"출간일":"2026-07-30"}},
                    [
                        {"제품코드":"A","판매일":"2026-08-01","거래처코드":"YES24","판매수량":3},
                        {"제품코드":"A","판매일":"2026-08-02","거래처코드":"YES24","판매수량":5},
                        {"제품코드":"A","판매일":"2026-08-02","거래처코드":"KYOBO","판매수량":100},
                        {"제품코드":"A","판매일":"2026-08-04","거래처코드":"YES24","판매수량":200},
                    ],
                    [{"원본활동ID":"1","제품코드":"A","실제비용":350000}],
                )

        backend = Backend()
        backend.db = FakeDatabase()
        backend.product_index = [{"제품코드":"A","제품명":"테스트 도서","최종대분류":"03. 단행본","최종중분류":"경제"}]
        result = backend.get_major_bookstore_marketing_activities()
        self.assertTrue(result["ok"])
        self.assertEqual(result["bookstores"]["YES24"][0]["실판매부수"], 8)
        self.assertEqual(result["bookstores"]["YES24"][0]["실제집행비용"], 350000)
        self.assertEqual(result["products"], [{"제품코드":"A","제품명":"테스트 도서"}])

    def test_activity_update_keeps_one_source_row_and_upserts_actual_cost(self):
        db = database_with({"마케팅활동":[{
            "활동ID":"activity-1","제품코드":"A","활동분류":"서점 마케팅","채널또는매체":"YES24",
            "활동명":"강연","시작일":"2026-08-20","종료일":"2026-08-20","비용":100000,"정렬순서":10,
        }],"마케팅실행활동":[]})
        client = db.client
        payload = {"activity_category":"서점 마케팅","channel_or_media":"YES24","activity_name":"ZOOM 강연","start_date":"2026-08-21","end_date":"2026-08-21","cost":100000,"actual_cost":3850000,"schedule_note":"저녁 7시","note":"온라인 강연"}
        db.update_marketing_activity("activity-1", payload)
        payload["actual_cost"] = 3840000
        db.update_marketing_activity("activity-1", payload)
        self.assertEqual(len(client.tables["마케팅활동"]), 1)
        self.assertEqual(client.tables["마케팅활동"][0]["활동ID"], "activity-1")
        self.assertEqual(client.tables["마케팅활동"][0]["활동명"], "ZOOM 강연")
        self.assertEqual(len(client.tables["마케팅실행활동"]), 1)
        self.assertEqual(client.tables["마케팅실행활동"][0]["원본활동ID"], "activity-1")
        self.assertEqual(client.tables["마케팅실행활동"][0]["실제비용"], 3840000)
