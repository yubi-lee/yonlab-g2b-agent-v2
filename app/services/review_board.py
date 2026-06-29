from __future__ import annotations

import re
from datetime import UTC, date, datetime
from typing import Any

from app.services.review_status import REVIEW_STATUS_LABELS_KO

ACTIVE_CARD_STATUSES = ("go", "reviewing", "shortlisted", "hold")
ALL_REVIEW_STATUSES = (
    "new",
    "shortlisted",
    "reviewing",
    "go",
    "hold",
    "no_go",
    "submitted",
    "archived",
)
STATUS_PRIORITY = {status: index for index, status in enumerate(ACTIVE_CARD_STATUSES)}
WINDOWS_PATH_RE = re.compile(r"[A-Za-z]:\\")


def build_review_board(
    items: list[dict[str, Any]] | None,
    *,
    source: str = "empty",
) -> dict[str, Any]:
    safe_items = [_safe_board_item(item) for item in (items or [])]
    status_counts = build_review_status_counts(safe_items)
    cards = _build_review_cards(safe_items)
    board_source = source or "empty"
    board_status = "empty"
    if safe_items:
        board_status = "demo" if board_source == "demo" else "success"
    return {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "source": board_source,
        "status": board_status,
        "total_count": len(safe_items),
        "active_count": sum(status_counts.get(status, 0) for status in ACTIVE_CARD_STATUSES),
        "deadline_first_actions": build_next_action_board(safe_items),
        "status_counts": status_counts,
        "filters": _default_filters(),
        "cards": cards,
        "service_key_exposed": False,
        "real_api_call_attempted": False,
    }


def build_review_status_counts(items: list[dict[str, Any]] | None) -> dict[str, int]:
    counts = {status: 0 for status in ALL_REVIEW_STATUSES}
    for item in items or []:
        status = _normalized_status(item.get("review_status"))
        counts[status] += 1
    return counts


def group_by_review_status(items: list[dict[str, Any]] | None) -> dict[str, list[dict[str, Any]]]:
    grouped = {status: [] for status in ALL_REVIEW_STATUSES}
    for item in items or []:
        grouped[_normalized_status(item.get("review_status"))].append(item)
    for status, values in grouped.items():
        grouped[status] = sorted(values, key=_review_board_sort_key)
    return grouped


def build_next_action_board(items: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    actionable = [
        item for item in (items or []) if str(item.get("next_action") or "").strip()
    ]
    return sorted(actionable, key=_next_action_sort_key)


def _build_review_cards(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped = group_by_review_status(items)
    cards = []
    for status in ACTIVE_CARD_STATUSES:
        cards.append(
            {
                "review_status": status,
                "review_status_ko": REVIEW_STATUS_LABELS_KO.get(status, status),
                "count": len(grouped[status]),
                "items": grouped[status][:3],
                "filter_payload": _filter_payload(status),
            }
        )
    return cards


def _safe_board_item(item: dict[str, Any]) -> dict[str, Any]:
    review_status = _normalized_status(item.get("review_status"))
    deadline = _safe_text(item.get("deadline"))
    return {
        "notice_id": _safe_text(item.get("notice_id")),
        "title": _safe_text(item.get("title")),
        "agency": _safe_text(item.get("agency")),
        "deadline": deadline,
        "deadline_status": _deadline_status(deadline),
        "review_status": review_status,
        "review_status_ko": _safe_text(item.get("review_status_ko"))
        or REVIEW_STATUS_LABELS_KO.get(review_status, review_status),
        "score": int(item.get("score") or 0),
        "risk_level": _safe_text(item.get("risk_level")) or "unknown",
        "next_action": _safe_text(item.get("next_action")),
        "filter_payload": _filter_payload(review_status),
    }


def _default_filters() -> dict[str, Any]:
    return {
        "review_status": None,
        "shortlisted_only": False,
        "hide_archived_no_go": True,
        "sort": "score_desc",
    }


def _filter_payload(review_status: str) -> dict[str, Any]:
    return {
        "review_status": review_status,
        "shortlisted_only": False,
        "hide_archived_no_go": True,
        "sort": "score_desc",
    }


def _review_board_sort_key(item: dict[str, Any]) -> tuple[date, int, str]:
    return (
        _deadline_for_sort(item.get("deadline")),
        -int(item.get("score") or 0),
        str(item.get("notice_id") or ""),
    )


def _next_action_sort_key(item: dict[str, Any]) -> tuple[date, int, int, str]:
    return (
        _deadline_for_sort(item.get("deadline")),
        STATUS_PRIORITY.get(_normalized_status(item.get("review_status")), 99),
        -int(item.get("score") or 0),
        str(item.get("notice_id") or ""),
    )


def _deadline_status(value: Any) -> str:
    parsed = _parse_deadline(value)
    if parsed is None:
        return "unknown"
    if parsed < date.today():
        return "overdue"
    if (parsed - date.today()).days <= 7:
        return "due_soon"
    return "upcoming"


def _deadline_for_sort(value: Any) -> date:
    return _parse_deadline(value) or date.max


def _parse_deadline(value: Any) -> date | None:
    text = _safe_text(value).replace(".", "-").replace("/", "-").strip()
    if not text:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(text[: len("2026-06-20 12:00:00")], fmt).date()
        except ValueError:
            continue
    return None


def _normalized_status(value: Any) -> str:
    status = _safe_text(value) or "new"
    return status if status in ALL_REVIEW_STATUSES else "new"


def _safe_text(value: Any) -> str:
    text = "" if value is None else str(value)
    text = WINDOWS_PATH_RE.sub("[local-path-redacted]", text)
    text = text.replace("serviceKey", "[redacted-key-field]")
    text = text.replace("SERVICE_KEY", "[redacted-key-field]")
    text = text.replace(".env", "[env-redacted]")
    return text
