from __future__ import annotations

import unittest

from app.channel_activity import build_bookstore_timeline_rows, build_social_viral_rows, classify_bookstore, classify_product_category
from app.backend import Backend
from tests.fakes import database_with


class ChannelActivityTests(unittest.TestCase):
    def test_social_dashboard_calculates_relative_scm_and_missing_future(self):
        activities = [{"활동ID":"A1","제품코드":"P1","활동분류":"SNS·바이럴","채널또는매체":"YouTube","활동명":"저자 출연"}]
        contents = [
            {"콘텐츠성과ID":"C1","활동ID":"A1","제품코드":"P1","콘텐츠명":"영상 1","게시일":"2026-08-10"},
            {"콘텐츠성과ID":"C2","활동ID":"A1","제품코드":"P1","콘텐츠명":"영상 2","게시일":"2026-08-13"},
        ]
        scm = []
        for day, quantity in (("2026-08-03",7),("2026-08-04",14),("2026-08-10",30),("2026-08-11",40),("2026-08-12",50)):
            scm.extend([
                {"제품코드":"P1","판매일":day,"거래처코드":"KYOBO","판매수량":quantity},
                {"제품코드":"P1","판매일":day,"거래처코드":"YES24","판매수량":1},
                {"제품코드":"P1","판매일":day,"거래처코드":"OTHER","판매수량":999},
            ])
        rows = build_social_viral_rows(contents, activities, [{"원본활동ID":"A1","실제비용":7000000}], {"P1":{"제품명":"테스트 도서","최종대분류":"03. 단행본"}}, {"P1":{"출간일":"2026-08-01"}}, scm, "2026-08-01", "2026-08-12")
        first = next(row for row in rows if row["콘텐츠성과ID"] == "C1")
        self.assertEqual(first["게시일실판매"], 31)
        self.assertAlmostEqual(first["게시전7일일평균"], 23 / 7)
        self.assertEqual(first["게시후7일누적"], 92)
        self.assertEqual(first["게시후집계일수"], 2)
        self.assertIsNone(first["판매포인트"][-1]["sales"])
        self.assertEqual(first["동기간SNS게시일"], ["2026-08-13"])
        self.assertEqual(first["실제집행비용"], 7000000)
        self.assertEqual(first["도서명"], "테스트 도서")

    def test_social_dashboard_query_batches_contents_instead_of_n_plus_one(self):
        db = database_with({
            "콘텐츠성과":[
                {"콘텐츠성과ID":"C1","제품코드":"P1","활동ID":"A1","게시일":"2026-08-10"},
                {"콘텐츠성과ID":"C2","제품코드":"P1","활동ID":"A1","게시일":"2026-08-11"},
            ],
            "마케팅활동":[{"활동ID":"A1","제품코드":"P1","활동분류":"SNS·바이럴","시작일":"2026-08-10"}],
            "마케팅실행활동":[],
            "제품인덱스":[{"제품코드":"P1","제품명":"도서"}],
            "마케팅대상제품":[{"제품코드":"P1","출간일":"2026-08-01"}],
            "SCM일별실판매":[{"제품코드":"P1","판매일":"2026-08-10","거래처코드":"YES24","판매수량":3}],
        })
        result = db.fetch_social_viral_dashboard_data()
        self.assertEqual(len(result["contents"]), 2)
        scm_selects = [call for call in db.client.calls if call[0] == "SCM일별실판매" and call[1] == "select"]
        self.assertEqual(len(scm_selects), 3)  # one product batch + global min/max

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
                    {"A":{"제품코드":"A","제품명":"테스트 도서","최종대분류":"03. 단행본","최종중분류":"경제"}},
                )

        backend = Backend()
        backend.db = FakeDatabase()
        backend.product_index = [{"제품코드":"A","제품명":"테스트 도서","최종대분류":"03. 단행본","최종중분류":"경제"}]
        result = backend.get_major_bookstore_marketing_activities()
        self.assertTrue(result["ok"])
        self.assertEqual(result["bookstores"]["YES24"][0]["실판매부수"], 8)
        self.assertEqual(result["bookstores"]["YES24"][0]["실제집행비용"], 350000)
        self.assertEqual(result["products"], [{"제품코드":"A","제품명":"테스트 도서"}])

    def test_multiple_products_use_authoritative_product_index_names(self):
        activities = [
            {"활동ID":"1","제품코드":"A","채널또는매체":"교보","활동명":"광고"},
            {"활동ID":"2","제품코드":"B","채널또는매체":"YES24","활동명":"강연"},
            {"활동ID":"3","제품코드":"C","채널또는매체":"알라딘","활동명":"배너"},
        ]
        products = {
            "A":{"제품코드":"A","제품명":"아동 도서","최종대분류":"01. 아동"},
            "B":{"제품코드":"B","제품명":"만화 도서","최종대분류":"02. 만화"},
            "C":{"제품코드":"C","제품명":"단행본 도서","최종대분류":"03. 단행본"},
        }
        rows = build_bookstore_timeline_rows(activities, products, {})
        names = {row["제품코드"]:row["도서명"] for store_rows in rows.values() for row in store_rows}
        self.assertEqual(names, {"A":"아동 도서","B":"만화 도서","C":"단행본 도서"})
        missing = build_bookstore_timeline_rows([{"활동ID":"4","제품코드":"73706001","채널또는매체":"교보"}], {}, {})["교보문고"][0]
        self.assertEqual(missing["도서명"], "제품명 미확인")
        self.assertNotEqual(missing["도서명"], missing["제품코드"])

    def test_channel_query_reads_product_names_directly_from_product_index(self):
        db = database_with({
            "마케팅활동":[{"활동ID":"1","제품코드":"A","채널또는매체":"교보","활동명":"광고"}],
            "마케팅대상제품":[{"제품코드":"A","출간일":"2026-08-01"}],
            "제품인덱스":[{"제품코드":"A","제품명":"직접 조회 도서","최종대분류":"03. 단행본","최종중분류":"경제"}],
            "SCM일별실판매":[],"마케팅실행활동":[],
        })
        _, _, _, _, products = db.fetch_channel_marketing_activities()
        self.assertEqual(products["A"]["제품명"], "직접 조회 도서")
        product_calls = [call for call in db.client.calls if call[0] == "제품인덱스" and call[1] == "select"]
        self.assertEqual(len(product_calls), 1)

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
