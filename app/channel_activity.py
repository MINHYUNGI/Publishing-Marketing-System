from __future__ import annotations

from datetime import date, timedelta
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
            "도서명": product.get("제품명") or "제품명 미확인",
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


def is_social_viral_activity(activity: dict[str, Any]) -> bool:
    value = f"{activity.get('활동분류') or ''} {activity.get('채널또는매체') or ''}".casefold()
    return any(token in value for token in ("sns", "바이럴", "유튜브", "youtube", "인스타", "instagram", "블로그", "카페"))


def build_social_viral_rows(
    contents: list[dict[str, Any]],
    activities: list[dict[str, Any]],
    executions: list[dict[str, Any]],
    products: dict[str, dict[str, Any]],
    marketing_products: dict[str, dict[str, Any]],
    scm_rows: list[dict[str, Any]],
    scm_date_min: str,
    scm_date_max: str,
) -> list[dict[str, Any]]:
    """Join content and activity IDs, then calculate D-7..D+7 SCM response in memory."""
    social_activities = {str(row.get("활동ID")): row for row in activities if row.get("활동ID") and is_social_viral_activity(row)}
    execution_by_id = {str(row.get("실행활동ID")): row for row in executions if row.get("실행활동ID")}
    actual_cost_by_activity = {
        str(row.get("원본활동ID")): int(row.get("실제비용") or 0)
        for row in executions if row.get("원본활동ID")
    }
    sales: dict[tuple[str, str], int] = {}
    for row in scm_rows:
        code, sale_day = str(row.get("제품코드") or ""), str(row.get("판매일") or "")[:10]
        if code and sale_day and str(row.get("거래처코드") or "") in {"KYOBO", "YPBOOKS", "YES24", "ALADIN"}:
            sales[(code, sale_day)] = sales.get((code, sale_day), 0) + int(row.get("판매수량") or 0)

    prepared: list[tuple[dict[str, Any], dict[str, Any], str, str]] = []
    seen_content_ids: set[str] = set()
    for content in contents:
        content_id = str(content.get("콘텐츠성과ID") or "")
        if content_id and content_id in seen_content_ids:
            continue
        if content_id:
            seen_content_ids.add(content_id)
        execution = execution_by_id.get(str(content.get("실행활동ID") or ""), {})
        activity_id = str(content.get("활동ID") or execution.get("원본활동ID") or "")
        activity = social_activities.get(activity_id)
        code = str(content.get("제품코드") or execution.get("제품코드") or (activity or {}).get("제품코드") or "")
        post_day = str(content.get("게시일") or "")[:10]
        if code and post_day and (activity or content.get("활동ID") or content.get("실행활동ID")):
            prepared.append((content, activity or {}, code, post_day))

    post_days_by_product: dict[str, list[str]] = {}
    for _content, _activity, code, post_day in prepared:
        post_days_by_product.setdefault(code, []).append(post_day)

    result: list[dict[str, Any]] = []
    for content, activity, code, post_day in prepared:
        center = date.fromisoformat(post_day)
        points = []
        for offset in range(-7, 8):
            day = (center + timedelta(days=offset)).isoformat()
            available = bool(scm_date_min and scm_date_max and scm_date_min <= day <= scm_date_max)
            points.append({"offset": offset, "date": day, "sales": sales.get((code, day), 0) if available else None})
        before = [point["sales"] for point in points if -7 <= point["offset"] <= -1 and point["sales"] is not None]
        after = [point["sales"] for point in points if 1 <= point["offset"] <= 7 and point["sales"] is not None]
        product = products.get(code, {})
        nearby = sorted({day for day in post_days_by_product.get(code, []) if day != post_day and abs((date.fromisoformat(day) - center).days) <= 7})
        result.append({
            **content,
            "활동ID": activity.get("활동ID") or content.get("활동ID"),
            "활동분류": activity.get("활동분류"),
            "활동명": activity.get("활동명"),
            "채널또는매체": activity.get("채널또는매체"),
            "시작일": activity.get("시작일"),
            "종료일": activity.get("종료일"),
            "일정비고": activity.get("일정비고"),
            "비고": activity.get("비고"),
            "비용": activity.get("비용") or 0,
            "실제집행비용": actual_cost_by_activity.get(str(activity.get("활동ID") or ""), 0),
            "제품코드": code,
            "도서명": product.get("제품명") or "제품명 미확인",
            "분류": classify_product_category(product.get("최종대분류"), product.get("최종중분류")),
            "출간일": marketing_products.get(code, {}).get("출간일"),
            "판매포인트": points,
            "게시일실판매": next((point["sales"] for point in points if point["offset"] == 0), None),
            "게시전7일일평균": sum(before) / len(before) if before else None,
            "게시전집계일수": len(before),
            "게시후7일누적": sum(after),
            "게시후집계일수": len(after),
            "동기간SNS게시일": nearby,
        })
    result.sort(key=lambda row: (CATEGORY_ORDER.index(row["분류"]), _descending_date_key(row.get("출간일")), str(row.get("도서명") or ""), str(row.get("게시일") or "")))
    return result
