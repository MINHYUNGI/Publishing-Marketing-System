from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any


@dataclass
class FakeResponse:
    data: list[dict[str, Any]]


class FakeQuery:
    def __init__(self, client: "FakeClient", table: str) -> None:
        self.client = client
        self.table_name = table
        self.operation = "select"
        self.payload: Any = None
        self.filters: list[tuple[str, str, Any]] = []
        self.orders: list[tuple[str, bool]] = []
        self.limit_count: int | None = None
        self.range_value: tuple[int, int] | None = None
        self.conflict: list[str] = []

    def select(self, *_args, **_kwargs):
        self.operation = "select"
        return self

    def insert(self, payload):
        self.operation, self.payload = "insert", payload
        return self

    def update(self, payload):
        self.operation, self.payload = "update", payload
        return self

    def upsert(self, payload, on_conflict: str | None = None):
        self.operation, self.payload = "upsert", payload
        self.conflict = [value.strip() for value in (on_conflict or "").split(",") if value.strip()]
        return self

    def delete(self):
        self.operation = "delete"
        return self

    def eq(self, key, value):
        self.filters.append(("eq", key, value))
        return self

    def neq(self, key, value):
        self.filters.append(("neq", key, value))
        return self

    def is_(self, key, value):
        self.filters.append(("is", key, value))
        return self

    def in_(self, key, values):
        self.filters.append(("in", key, set(values)))
        return self

    def order(self, key, desc: bool = False):
        self.orders.append((key, desc))
        return self

    def limit(self, count):
        self.limit_count = count
        return self

    def range(self, start, end):
        self.range_value = (start, end)
        return self

    def _matches(self, row):
        for operation, key, value in self.filters:
            current = row.get(key)
            if operation == "eq" and current != value:
                return False
            if operation == "neq" and current == value:
                return False
            if operation == "is" and value == "null" and current is not None:
                return False
            if operation == "in" and current not in value:
                return False
        return True

    def _selected(self):
        rows = [row for row in self.client.tables.setdefault(self.table_name, []) if self._matches(row)]
        for key, desc in reversed(self.orders):
            rows.sort(key=lambda row: (row.get(key) is None, row.get(key)), reverse=desc)
        if self.range_value:
            start, end = self.range_value
            rows = rows[start : end + 1]
        if self.limit_count is not None:
            rows = rows[: self.limit_count]
        return rows

    def _with_id(self, row):
        result = deepcopy(row)
        id_fields = {
            "마케팅실행활동": "실행활동ID",
            "마케팅참조파일": "파일ID",
            "콘텐츠성과": "콘텐츠성과ID",
            "문서": "문서ID",
            "마케팅활동": "활동ID",
        }
        field = id_fields.get(self.table_name)
        if field and not result.get(field):
            result[field] = f"{self.table_name}-{self.client.next_id()}"
        return result

    def execute(self):
        self.client.calls.append((self.table_name, self.operation, deepcopy(self.payload), list(self.filters)))
        table = self.client.tables.setdefault(self.table_name, [])
        if self.operation == "select":
            return FakeResponse(deepcopy(self._selected()))
        if self.operation == "insert":
            values = self.payload if isinstance(self.payload, list) else [self.payload]
            created = [self._with_id(value) for value in values]
            table.extend(created)
            return FakeResponse(deepcopy(created))
        if self.operation == "update":
            changed = []
            for row in table:
                if self._matches(row):
                    row.update(deepcopy(self.payload))
                    changed.append(row)
            return FakeResponse(deepcopy(changed))
        if self.operation == "delete":
            removed = [row for row in table if self._matches(row)]
            table[:] = [row for row in table if not self._matches(row)]
            return FakeResponse(deepcopy(removed))
        values = self.payload if isinstance(self.payload, list) else [self.payload]
        changed = []
        for value in values:
            existing = next(
                (
                    row
                    for row in table
                    if self.conflict
                    and all(row.get(key) == value.get(key) for key in self.conflict)
                ),
                None,
            )
            if existing:
                existing.update(deepcopy(value))
                changed.append(existing)
            else:
                created = self._with_id(value)
                table.append(created)
                changed.append(created)
        return FakeResponse(deepcopy(changed))


class FakeClient:
    def __init__(self, tables: dict[str, list[dict[str, Any]]] | None = None) -> None:
        self.tables = deepcopy(tables or {})
        self.calls: list[tuple[str, str, Any, list[tuple[str, str, Any]]]] = []
        self._sequence = 0

    def next_id(self):
        self._sequence += 1
        return self._sequence

    def table(self, name):
        return FakeQuery(self, name)


def database_with(tables: dict[str, list[dict[str, Any]]] | None = None):
    from app.database import Database

    database = object.__new__(Database)
    database.client = FakeClient(tables)
    return database


def performance_tables():
    return {
        "마케팅기획": [{"기획ID": "plan-1", "제품코드": "P1", "마케팅문구": "문구"}],
        "마케팅활동": [
            {
                "활동ID": "plan-activity-1",
                "제품코드": "P1",
                "활동분류": "SNS·바이럴",
                "채널또는매체": "채널",
                "활동명": "영상 공개",
                "시작일": "2026-08-01",
                "종료일": "2026-08-02",
                "비용": 100000,
                "계획실행구분": "계획",
                "생성일시": "2026-07-01",
                "정렬순서": 10,
            }
        ],
        "마케팅대상제품": [{"제품코드": "P1", "저자명": "저자", "출간일": "2026-08-10"}],
        "제품인덱스": [{"제품코드": "P1", "제품명": "테스트 도서", "정가": 20000}],
        "사업계획목표": [],
        "사업계획월별목표": [],
        "영업목표": [],
        "판매실적일별": [],
        "구매자반응": [],
        "마케팅성과평가": [],
        "마케팅실행활동": [
            {
                "실행활동ID": "execution-1",
                "원본활동ID": "plan-activity-1",
                "제품코드": "P1",
                "활동분류": "SNS·바이럴",
                "활동명": "영상 공개",
                "실제시작일": "2026-08-03",
                "실제종료일": "2026-08-04",
                "실제비용": 90000,
                "실행구분": "실행확인",
                "정렬순서": 20,
                "생성일시": "2026-08-03",
            }
        ],
        "콘텐츠성과": [
            {
                "콘텐츠성과ID": "content-1",
                "제품코드": "P1",
                "활동ID": "plan-activity-1",
                "실행활동ID": "execution-1",
                "플랫폼": "Instagram",
                "URL": "https://instagram.com/example",
                "원천구분": "실행링크",
                "링크순서": 10,
                "생성일시": "2026-08-03",
            }
        ],
        "마케팅참조파일": [
            {
                "파일ID": "cover-1",
                "제품코드": "P1",
                "파일분류": "도서표지",
                "파일형식": "jfif",
                "생성일시": "2026-08-01",
            }
        ],
        "ERP일별판매실적": [
            {
                "제품코드": "P1",
                "매출일자": "2026-08-11",
                "매출부수": 12,
                "매출금액": 240000,
                "출고부수": 14,
                "반품부수": 2,
            }
        ],
    }
