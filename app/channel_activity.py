from __future__ import annotations

from typing import Any


BOOKSTORE_ORDER = ("교보문고", "영풍문고", "YES24", "알라딘")
CATEGORY_ORDER = ("아동", "만화", "단행본")


def classify_bookstore(channel: Any) -> str | None:
    """Classify for display without changing the original channel value."""
    value = str(channel or "").strip()
    lowered = value.casefold()
    if "교보" in value:
        return "교보문고"
    if "영풍" in value:
        return "영풍문고"
    if "예스" in value or "yes24" in lowered:
        return "YES24"
    if "알라딘" in value:
        return "알라딘"
    return None


def classify_product_category(main_category: Any, middle_category: Any) -> str:
    value = f"{main_category or ''} {middle_category or ''}".casefold()
    if "만화" in value:
        return "만화"
    if any(token in value for token in ("아동", "어린이", "아이세움", "01.")):
        return "아동"
    return "단행본"


def build_bookstore_timeline_rows(
    activities: list[dict[str, Any]],
    products: dict[str, dict[str, Any]],
    marketing_products: dict[str, dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    result = {name: [] for name in BOOKSTORE_ORDER}
    for activity in activities:
        bookstore = classify_bookstore(activity.get("채널또는매체"))
        if not bookstore:
            continue
        code = str(activity.get("제품코드") or "")
        product = products.get(code, {})
        marketing = marketing_products.get(code, {})
        row = {
            **activity,
            "서점": bookstore,
            "도서명": product.get("제품명") or code or "제품 미연결",
            "분류": classify_product_category(product.get("최종대분류"), product.get("최종중분류")),
            "출간일": marketing.get("출간일"),
        }
        result[bookstore].append(row)
    for rows in result.values():
        rows.sort(key=lambda row: (
            CATEGORY_ORDER.index(row["분류"]),
            "" if row.get("출간일") else "1",
            _descending_date_key(row.get("출간일")),
            str(row.get("도서명") or ""),
            str(row.get("시작일") or "9999-12-31"),
            str(row.get("활동명") or ""),
        ))
    return result


def _descending_date_key(value: Any) -> int:
    digits = "".join(ch for ch in str(value or "") if ch.isdigit())
    return -int(digits[:8]) if len(digits) >= 8 else 0
