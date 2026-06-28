from __future__ import annotations

import csv
import io
import re
from datetime import UTC, date, datetime
from typing import Any

from app.services.opportunity_decision import group_required_documents

EMPTY_STATE_MESSAGE = (
    "No opportunity data available. No searchable saved notices exist yet."
)
EMPTY_STATE_NEXT_ACTIONS = [
    "Run a fixture-safe job to verify the local workflow.",
    "Run a controlled real run only from the approved script with explicit confirmation.",
    "Open Opportunity Inbox after a saved run exists.",
]
PRIORITY_LEGEND = {
    "P1": "same-day priority review",
    "P2": "next candidate review",
    "P3": "spare capacity check",
    "Hold": "monitor/exclude candidate",
}
SOURCE_MODE_MESSAGES = {
    "real": "Source mode real: based on a controlled real 나라장터 query result.",
    "saved": "Source mode saved: based on saved operations results.",
    "synthetic": "Source mode synthetic: demo/sample data may not be real notices.",
    "fixture": "Source mode fixture: local fixture data, not a real API call.",
    "demo": "Source mode demo: saved runs are empty, but demo/saved fallback is displayed.",
    "empty": "Source mode empty: no searchable saved notices yet.",
    "mixed": "Source mode mixed: review item-level source badges before action.",
}
CSV_FIELDS = [
    "notice_id",
    "title",
    "agency",
    "budget",
    "deadline",
    "score",
    "decision_label_ko",
    "bid_priority",
    "go_no_go_recommendation_ko",
    "risk_summary",
    "today_action",
    "detail_url",
]
PRIORITY_ORDER = {"P1": 0, "P2": 1, "P3": 2, "Hold": 3}
RISK_ORDER = {"low": 0, "medium": 1, "high": 2}
SAFE_URL_RE = re.compile(r"^(https?://|/)")
WINDOWS_PATH_RE = re.compile(r"[A-Za-z]:\\")


def build_daily_review_pack(items: list[dict[str, Any]] | None) -> dict[str, Any]:
    safe_items = sorted(
        (_safe_item(item) for item in (items or [])),
        key=_sort_key,
    )
    groups = group_opportunities_by_priority(safe_items)
    review_items = [*groups["P1"], *groups["P2"], *groups["P3"]]
    hold_items = groups["Hold"]
    no_go_items = [
        item
        for item in safe_items
        if str(item.get("go_no_go_recommendation") or "").casefold() == "no-go"
    ]
    pack = {
        "status": "success" if safe_items else "empty",
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "source_mode": _source_mode(safe_items),
        "latest_run_id": _latest_run_id(safe_items),
        "latest_run_created_at": _latest_run_created_at(safe_items),
        "total_items": len(safe_items),
        "p1_count": len(groups["P1"]),
        "p2_count": len(groups["P2"]),
        "p3_count": len(groups["P3"]),
        "hold_count": len(groups["Hold"]),
        "no_go_count": len(no_go_items),
        "top_items": review_items[:3],
        "review_items": review_items,
        "hold_items": hold_items,
        "no_go_items": no_go_items,
        "today_actions": build_today_action_summary(safe_items),
        "document_actions": build_document_action_summary(safe_items),
        "risk_summary": build_risk_summary(safe_items),
        "empty_state_message": "" if safe_items else EMPTY_STATE_MESSAGE,
        "empty_state_next_actions": [] if safe_items else list(EMPTY_STATE_NEXT_ACTIONS),
        "priority_legend": PRIORITY_LEGEND,
        "service_key_exposed": False,
        "real_api_call_attempted": False,
    }
    pack["source_mode_message"] = build_source_mode_message(
        str(pack["source_mode"]),
        has_items=bool(safe_items),
    )
    pack["executive_summary"] = build_executive_summary(pack)
    pack["markdown_report"] = build_daily_review_markdown(pack)
    return pack


def build_source_mode_message(source_mode: str, *, has_items: bool = True) -> str:
    mode = source_mode if source_mode in SOURCE_MODE_MESSAGES else "empty"
    if not has_items:
        mode = "empty"
    return SOURCE_MODE_MESSAGES[mode]


def build_executive_summary(pack: dict[str, Any]) -> dict[str, Any]:
    total_items = int(pack.get("total_items") or 0)
    p1_count = int(pack.get("p1_count") or 0)
    p2_count = int(pack.get("p2_count") or 0)
    hold_count = int(pack.get("hold_count") or 0)
    risk_summary = pack.get("risk_summary") or {}
    high_risk_count = int(risk_summary.get("high_risk_count") or 0)
    top_risks = risk_summary.get("top_risks") or []
    main_risk = (
        f"High-risk notices: {high_risk_count}"
        if high_risk_count
        else "No major high-risk signal in the current pack"
    )
    recommended_response = (
        "Review P1 notices today and confirm documents before proposal drafting."
        if p1_count
        else "Create a saved run first, then review priority candidates."
    )
    lines = [
        f"총 {total_items}개 공고 중 오늘 우선 검토 대상은 {p1_count + p2_count}개입니다.",
        f"P1 {p1_count}개, P2 {p2_count}개, Hold {hold_count}개로 분류되었습니다.",
        f"주요 리스크: {main_risk}.",
        f"오늘 권장 대응: {recommended_response}",
    ]
    if top_risks:
        first = top_risks[0]
        lines.append(
            f"가장 먼저 확인할 리스크 공고: {first.get('notice_id') or 'unknown'}."
        )
    return {
        "total_items": total_items,
        "today_priority_count": p1_count + p2_count,
        "p1_count": p1_count,
        "p2_count": p2_count,
        "hold_count": hold_count,
        "main_risk": main_risk,
        "today_recommended_response": recommended_response,
        "lines": lines[:5],
    }


def group_opportunities_by_priority(
    items: list[dict[str, Any]] | None,
) -> dict[str, list[dict[str, Any]]]:
    groups = {"P1": [], "P2": [], "P3": [], "Hold": []}
    for item in sorted((_safe_item(value) for value in (items or [])), key=_sort_key):
        priority = _priority(item)
        groups.setdefault(priority, []).append(item)
    return groups


def build_today_action_summary(items: list[dict[str, Any]] | None) -> list[dict[str, str]]:
    actions = []
    for item in sorted((_safe_item(value) for value in (items or [])), key=_sort_key):
        action_plan = item.get("action_plan") or {}
        actions.append(
            {
                "notice_id": str(item.get("notice_id") or ""),
                "title": str(item.get("title") or ""),
                "bid_priority": _priority(item),
                "today_action": str(
                    item.get("today_action")
                    or action_plan.get("today_action")
                    or item.get("recommended_action")
                    or "Review fit, documents, deadline, and go/no-go decision."
                ),
                "detail_url": _safe_url(item.get("detail_url")),
            }
        )
    return actions


def build_document_action_summary(items: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    actions = []
    for item in sorted((_safe_item(value) for value in (items or [])), key=_sort_key):
        action_plan = item.get("action_plan") or {}
        documents = item.get("required_documents")
        if not isinstance(documents, list):
            documents = []
        actions.append(
            {
                "notice_id": str(item.get("notice_id") or ""),
                "title": str(item.get("title") or ""),
                "document_action": str(
                    item.get("document_action")
                    or action_plan.get("document_action")
                    or "Check eligibility certificates and proposal documents."
                ),
                "required_documents": [
                    str(doc.get("name") or doc)
                    for doc in documents
                    if doc
                ],
                "required_documents_grouped": group_required_documents(documents),
            }
        )
    return actions


def build_risk_summary(items: list[dict[str, Any]] | None) -> dict[str, Any]:
    by_category: dict[str, int] = {}
    high_risk_count = 0
    medium_risk_count = 0
    low_risk_count = 0
    top_risks = []
    for item in sorted((_safe_item(value) for value in (items or [])), key=_sort_key):
        risk_level = str(item.get("risk_level") or "medium").casefold()
        if risk_level == "high":
            high_risk_count += 1
        elif risk_level == "low":
            low_risk_count += 1
        else:
            medium_risk_count += 1
        categories = item.get("risk_categories")
        if not isinstance(categories, list):
            categories = []
        for category in categories:
            name = str(category.get("category") or "general_risk")
            by_category[name] = by_category.get(name, 0) + 1
        risk_text = _risk_text(item)
        if risk_text:
            top_risks.append(
                {
                    "notice_id": str(item.get("notice_id") or ""),
                    "title": str(item.get("title") or ""),
                    "risk_level": risk_level,
                    "risk_summary": risk_text,
                }
            )
    return {
        "total_risk_categories": len(by_category),
        "high_risk_count": high_risk_count,
        "medium_risk_count": medium_risk_count,
        "low_risk_count": low_risk_count,
        "by_category": by_category,
        "top_risks": top_risks[:5],
    }


def build_daily_review_markdown(pack: dict[str, Any]) -> str:
    if int(pack.get("total_items") or 0) == 0:
        return "\n".join(
            [
                "# 오늘의 입찰 검토 패키지",
                "",
                f"- Generated At: {pack.get('generated_at') or ''}",
                "- Status: empty",
                f"- Source Run: {pack.get('latest_run_id') or 'none'}",
                f"- Source Mode: {pack.get('source_mode') or 'empty'}",
                (
                    "- Source Message: "
                    f"{pack.get('source_mode_message') or SOURCE_MODE_MESSAGES['empty']}"
                ),
                "",
                "No opportunity data available.",
                "",
                "## 다음 액션",
                *[f"- {action}" for action in (pack.get("empty_state_next_actions") or [])],
            ]
        )

    lines = [
        "# 오늘의 입찰 검토 패키지",
        "",
        f"- Generated At: {pack.get('generated_at') or ''}",
        f"- Source Mode: {pack.get('source_mode') or 'unknown'}",
        f"- Source Message: {pack.get('source_mode_message') or ''}",
        f"- Source Run: {pack.get('latest_run_id') or 'none'}",
        f"- Total Items: {pack.get('total_items') or 0}",
        f"- P1/P2/P3/Hold/No-Go: {pack.get('p1_count') or 0}/"
        f"{pack.get('p2_count') or 0}/{pack.get('p3_count') or 0}/"
        f"{pack.get('hold_count') or 0}/{pack.get('no_go_count') or 0}",
        "",
        "## 0. 한눈에 보는 요약",
    ]
    executive = pack.get("executive_summary") or {}
    for line in executive.get("lines") or []:
        lines.append(f"- {line}")
    lines.extend(["", "## Priority Legend"])
    for priority, description in (pack.get("priority_legend") or PRIORITY_LEGEND).items():
        lines.append(f"- {priority}: {description}")
    lines.extend(["", "## 1. 오늘의 우선 검토 공고"])
    lines.extend(_markdown_item_lines(pack.get("top_items") or []))
    lines.extend(["", "## 2. 공고별 판단 요약"])
    lines.extend(_markdown_item_lines(pack.get("review_items") or []))
    lines.extend(["", "## 3. 오늘 할 일"])
    for action in pack.get("today_actions") or []:
        lines.append(
            f"- {action.get('bid_priority')}: {action.get('notice_id')} - "
            f"{action.get('today_action')}"
        )
    lines.extend(["", "## 4. 서류 준비"])
    for action in pack.get("document_actions") or []:
        docs = ", ".join(action.get("required_documents") or ["Check source notice"])
        lines.append(f"- {action.get('notice_id')}: {action.get('document_action')} ({docs})")
        grouped = action.get("required_documents_grouped") or {}
        for group_name, documents in grouped.items():
            if documents:
                lines.append(f"  - {group_name}: {', '.join(documents)}")
    lines.extend(["", "## 5. 리스크 요약"])
    risk_summary = pack.get("risk_summary") or {}
    lines.append(f"- High risk items: {risk_summary.get('high_risk_count') or 0}")
    lines.append(f"- Medium risk items: {risk_summary.get('medium_risk_count') or 0}")
    lines.append(f"- Low risk items: {risk_summary.get('low_risk_count') or 0}")
    for risk in risk_summary.get("top_risks") or []:
        lines.append(
            f"- {risk.get('notice_id')}: {risk.get('risk_level')} - {risk.get('risk_summary')}"
        )
    lines.extend(
        [
            "",
            "## 6. 권장 대응",
            "- Review P1 items first for same-day go/no-go.",
            "- Prepare required documents before detailed proposal drafting.",
            "- Keep Hold and No-Go items visible for monitoring, not immediate pursuit.",
        ]
    )
    return "\n".join(_sanitize_export_text(line) for line in lines)


def build_daily_review_csv_rows(pack: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for item in _unique_pack_items(pack):
        action_plan = item.get("action_plan") or {}
        rows.append(
            {
                "notice_id": _csv_cell(item.get("notice_id")),
                "title": _csv_cell(item.get("title")),
                "agency": _csv_cell(item.get("agency")),
                "budget": _csv_cell(item.get("budget")),
                "deadline": _csv_cell(item.get("deadline")),
                "score": _csv_cell(item.get("score")),
                "decision_label_ko": _csv_cell(item.get("decision_label_ko")),
                "bid_priority": _csv_cell(_priority(item)),
                "go_no_go_recommendation_ko": _csv_cell(
                    item.get("go_no_go_recommendation_ko")
                ),
                "risk_summary": _csv_cell(_risk_text(item)),
                "today_action": _csv_cell(
                    item.get("today_action")
                    or action_plan.get("today_action")
                    or item.get("recommended_action")
                ),
                "detail_url": _csv_cell(_safe_url(item.get("detail_url"))),
            }
        )
    return rows


def build_daily_review_csv(pack: dict[str, Any]) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=CSV_FIELDS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(build_daily_review_csv_rows(pack))
    return "\ufeff" + output.getvalue()


def _safe_item(item: dict[str, Any]) -> dict[str, Any]:
    action_plan = item.get("action_plan") if isinstance(item.get("action_plan"), dict) else {}
    required_documents = item.get("required_documents")
    risk_categories = item.get("risk_categories")
    risks = item.get("risks")
    return {
        "notice_id": _sanitize_export_text(item.get("notice_id")),
        "title": _sanitize_export_text(item.get("title")),
        "agency": _sanitize_export_text(item.get("agency")),
        "budget": item.get("budget"),
        "deadline": _sanitize_export_text(item.get("deadline")),
        "score": int(item.get("score") or 0),
        "grade": _sanitize_export_text(item.get("grade")),
        "decision_label_ko": _sanitize_export_text(item.get("decision_label_ko")),
        "bid_priority": _priority(item),
        "go_no_go_recommendation": _sanitize_export_text(item.get("go_no_go_recommendation")),
        "go_no_go_recommendation_ko": _sanitize_export_text(
            item.get("go_no_go_recommendation_ko")
        ),
        "risk_level": _sanitize_export_text(item.get("risk_level")),
        "source_run_id": _sanitize_export_text(item.get("source_run_id")),
        "created_at": _sanitize_export_text(item.get("created_at")),
        "source_mode": _sanitize_export_text(item.get("source_mode") or item.get("source_type")),
        "detail_url": _safe_url(item.get("detail_url")),
        "recommended_action": _sanitize_export_text(item.get("recommended_action")),
        "today_action": _sanitize_export_text(item.get("today_action")),
        "document_action": _sanitize_export_text(item.get("document_action")),
        "action_plan": {
            key: _sanitize_export_text(value)
            for key, value in action_plan.items()
            if key in {"today_action", "document_action", "business_action", "go_no_go_action"}
        },
        "required_documents": required_documents if isinstance(required_documents, list) else [],
        "required_documents_grouped": group_required_documents(
            required_documents if isinstance(required_documents, list) else []
        ),
        "risk_categories": risk_categories if isinstance(risk_categories, list) else [],
        "risks": risks if isinstance(risks, list) else [],
    }


def _unique_pack_items(pack: dict[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    seen = set()
    for group in ("review_items", "hold_items", "no_go_items"):
        for item in pack.get(group) or []:
            safe = _safe_item(item)
            notice_id = safe.get("notice_id")
            if notice_id in seen:
                continue
            seen.add(notice_id)
            items.append(safe)
    return sorted(items, key=_sort_key)


def _markdown_item_lines(items: list[dict[str, Any]]) -> list[str]:
    if not items:
        return ["- No opportunity data available."]
    return [_markdown_item_line(item) for item in items]


def _markdown_item_line(item: dict[str, Any]) -> str:
    decision = (
        item.get("go_no_go_recommendation_ko")
        or item.get("go_no_go_recommendation")
        or "review"
    )
    return (
        "- "
        f"{item.get('notice_id')}: {item.get('title')} / {item.get('agency')} / "
        f"score {item.get('score')} / {item.get('bid_priority')} / {decision}"
    )


def _sort_key(item: dict[str, Any]) -> tuple[int, int, date, int, str]:
    return (
        PRIORITY_ORDER.get(_priority(item), 99),
        -int(item.get("score") or 0),
        _parse_deadline(item.get("deadline")) or date.max,
        RISK_ORDER.get(str(item.get("risk_level") or "").casefold(), 99),
        str(item.get("notice_id") or ""),
    )


def _priority(item: dict[str, Any]) -> str:
    value = str(item.get("bid_priority") or item.get("priority") or "Hold")
    return value if value in PRIORITY_ORDER else "Hold"


def _parse_deadline(value: Any) -> date | None:
    if isinstance(value, date):
        return value
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%Y%m%d"):
        try:
            return datetime.strptime(str(value)[:10], fmt).date()
        except ValueError:
            continue
    return None


def _source_mode(items: list[dict[str, Any]]) -> str:
    modes = {str(item.get("source_mode") or "unknown") for item in items}
    if not modes:
        return "empty"
    if len(modes) == 1:
        return next(iter(modes))
    return "mixed"


def _latest_run_id(items: list[dict[str, Any]]) -> str | None:
    for item in items:
        run_id = str(item.get("source_run_id") or "")
        if run_id:
            return run_id
    return None


def _latest_run_created_at(items: list[dict[str, Any]]) -> str | None:
    values = sorted(
        (
            str(item.get("created_at") or "")
            for item in items
            if str(item.get("created_at") or "")
        ),
        reverse=True,
    )
    return values[0] if values else None


def _risk_text(item: dict[str, Any]) -> str:
    risks = item.get("risks")
    if isinstance(risks, list) and risks:
        return "; ".join(_sanitize_export_text(value) for value in risks[:3])
    categories = item.get("risk_categories")
    if isinstance(categories, list) and categories:
        return "; ".join(
            _sanitize_export_text(category.get("message") or category.get("category"))
            for category in categories[:3]
            if category
        )
    return str(item.get("risk_level") or "medium")


def _safe_url(value: Any) -> str:
    text = _sanitize_export_text(value)
    if not text or WINDOWS_PATH_RE.search(text):
        return ""
    return text if SAFE_URL_RE.match(text) else ""


def _sanitize_export_text(value: Any) -> str:
    text = "" if value is None else str(value)
    text = WINDOWS_PATH_RE.sub("[local-path-redacted]", text)
    text = text.replace("serviceKey", "[redacted-key-field]")
    text = text.replace("SERVICE_KEY", "[redacted-key-field]")
    text = text.replace(".env", "[env-redacted]")
    return text


def _csv_cell(value: Any) -> str:
    text = _sanitize_export_text(value)
    if text.startswith(("=", "+", "-", "@")):
        return "'" + text
    return text
