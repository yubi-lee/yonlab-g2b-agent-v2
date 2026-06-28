from __future__ import annotations

import csv
import io
import re
from datetime import UTC, date, datetime
from typing import Any

EMPTY_STATE_MESSAGE = (
    "No opportunity data available. Run a fixture-safe job or review Opportunity Inbox first."
)
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
        "service_key_exposed": False,
        "real_api_call_attempted": False,
    }
    pack["markdown_report"] = build_daily_review_markdown(pack)
    return pack


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
                "# YOnLab Daily Bid Review Pack",
                "",
                f"- Generated At: {pack.get('generated_at') or ''}",
                "- Status: empty",
                f"- Source Run: {pack.get('latest_run_id') or 'none'}",
                "",
                "No opportunity data available.",
            ]
        )

    lines = [
        "# YOnLab Daily Bid Review Pack",
        "",
        f"- Generated At: {pack.get('generated_at') or ''}",
        f"- Source Mode: {pack.get('source_mode') or 'unknown'}",
        f"- Source Run: {pack.get('latest_run_id') or 'none'}",
        f"- Total Items: {pack.get('total_items') or 0}",
        f"- P1/P2/P3/Hold/No-Go: {pack.get('p1_count') or 0}/"
        f"{pack.get('p2_count') or 0}/{pack.get('p3_count') or 0}/"
        f"{pack.get('hold_count') or 0}/{pack.get('no_go_count') or 0}",
        "",
        "## 1. Today Top Opportunities",
    ]
    lines.extend(_markdown_item_lines(pack.get("top_items") or []))
    lines.extend(["", "## 2. Decision Summary By Notice"])
    lines.extend(_markdown_item_lines(pack.get("review_items") or []))
    lines.extend(["", "## 3. Today Actions"])
    for action in pack.get("today_actions") or []:
        lines.append(
            f"- {action.get('bid_priority')}: {action.get('notice_id')} - "
            f"{action.get('today_action')}"
        )
    lines.extend(["", "## 4. Required Documents"])
    for action in pack.get("document_actions") or []:
        docs = ", ".join(action.get("required_documents") or ["Check source notice"])
        lines.append(f"- {action.get('notice_id')}: {action.get('document_action')} ({docs})")
    lines.extend(["", "## 5. Risk Summary"])
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
            "## 6. Recommended Response",
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
