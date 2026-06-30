from __future__ import annotations

import re
from datetime import UTC, date, datetime
from typing import Any

WINDOWS_PATH_RE = re.compile(r"[A-Za-z]:\\")
ALLOWED_DECISIONS = {"Prepare", "Review", "Hold", "Reject"}


def build_empty_decision_memo(notice_id: str) -> dict[str, Any]:
    summary = (
        f"Decision memo unavailable for notice {notice_id}. "
        "Review Board or Inbox data was not found."
    )
    return {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "source": "empty",
        "status": "not_found",
        "notice_id": str(notice_id),
        "notice": {
            "title": "",
            "agency": "",
            "budget": None,
            "deadline": "",
            "source_url": "",
        },
        "review_context": {
            "review_status": "new",
            "deadline_status": "unknown",
            "risk_level": "unknown",
            "match_score": 0,
        },
        "manual_decision": _empty_manual_decision(),
        "yonlab_fit_summary": {
            "score": 0,
            "grade": "unknown",
            "fit_reasons": [],
            "concern_reasons": [],
        },
        "risk_summary": {
            "eligibility_risks": [],
            "document_risks": [],
            "schedule_risks": [],
            "commercial_risks": [],
        },
        "deadline_next_action": {
            "deadline": "",
            "days_remaining": None,
            "urgency": "unknown",
            "next_action": "Select a known local notice from Review Board or Opportunity Inbox.",
        },
        "recommended_decision": {
            "value": "Hold",
            "rationale": "No local-safe notice data is available yet for this notice id.",
        },
        "preparation_actions": [],
        "required_documents": [],
        "export_blocks": {
            "markdown": _build_export_markdown(
                title="Decision Memo Unavailable",
                decision="Hold",
                lines=[summary],
            ),
            "short_summary": summary,
        },
        "safety": {
            "real_api_call_attempted": False,
            "source_data_mode": "empty",
        },
        "service_key_exposed": False,
    }


def build_decision_memo(
    detail: dict[str, Any] | None,
    *,
    notice_id: str,
    manual_decision: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not detail:
        payload = build_empty_decision_memo(notice_id)
        manual_decision = _normalize_manual_decision(manual_decision)
        if manual_decision["persisted"] and manual_decision["decision"]:
            rationale = manual_decision["note"] or payload["recommended_decision"]["rationale"]
            summary = (
                f"{manual_decision['decision']} - Decision memo unavailable for notice {notice_id}."
            )
            payload["recommended_decision"] = {
                "value": manual_decision["decision"],
                "rationale": rationale,
            }
            payload["export_blocks"] = {
                "markdown": _build_export_markdown(
                    title="Decision Memo Unavailable",
                    decision=manual_decision["decision"],
                    lines=[summary],
                ),
                "short_summary": summary,
            }
        payload["manual_decision"] = manual_decision
        return payload

    source_mode = _safe_text(detail.get("source_type")) or "unknown"
    review_status = _safe_text(detail.get("review_status")) or "new"
    deadline = _safe_text(detail.get("deadline"))
    deadline_status = _deadline_status(deadline)
    score = int(detail.get("score") or 0)
    risk_level = (_safe_text(detail.get("risk_level")) or "unknown").casefold()
    manual_decision = _normalize_manual_decision(manual_decision)
    fit_reasons = _fit_reasons(detail)
    concern_reasons = _concern_reasons(detail)
    required_documents = _required_documents(detail)
    recommended_decision = _recommended_decision(
        detail,
        score=score,
        risk_level=risk_level,
        manual_decision=manual_decision,
    )
    deadline_next_action = _deadline_next_action(
        detail,
        deadline=deadline,
        deadline_status=deadline_status,
    )
    risk_summary = _risk_summary(
        detail,
        deadline_status=deadline_status,
        required_documents=required_documents,
    )
    preparation_actions = _preparation_actions(detail, required_documents=required_documents)

    memo_lines = [
        f"Decision: {recommended_decision['value']}",
        "YOnLab fit: "
        f"{_safe_text(detail.get('fit_summary')) or 'Review fit factors from saved notice data.'}",
        f"Main risk: {_main_risk_line(risk_summary)}",
        "Deadline: "
        f"{deadline_next_action['deadline'] or 'unknown'} "
        f"({deadline_next_action['urgency']})",
        f"Next action: {deadline_next_action['next_action']}",
    ]
    short_summary = (
        f"{recommended_decision['value']} - {_safe_text(detail.get('title')) or notice_id} "
        f"/ {_safe_text(detail.get('bid_priority')) or 'unknown'} "
        f"/ {deadline_next_action['urgency']}"
    )

    return {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "source": source_mode,
        "status": "demo" if source_mode == "demo" else "success",
        "notice_id": _safe_text(detail.get("notice_id")) or str(notice_id),
        "notice": {
            "title": _safe_text(detail.get("title")),
            "agency": _safe_text(detail.get("agency")),
            "budget": detail.get("budget"),
            "deadline": deadline,
            "source_url": _safe_url(detail.get("detail_url")),
        },
        "review_context": {
            "review_status": review_status,
            "deadline_status": deadline_status,
            "risk_level": risk_level,
            "match_score": score,
        },
        "manual_decision": manual_decision,
        "yonlab_fit_summary": {
            "score": score,
            "grade": (
                _safe_text(detail.get("decision_label"))
                or _safe_text(detail.get("grade"))
                or "unknown"
            ),
            "fit_reasons": fit_reasons,
            "concern_reasons": concern_reasons,
        },
        "risk_summary": risk_summary,
        "deadline_next_action": deadline_next_action,
        "recommended_decision": recommended_decision,
        "preparation_actions": preparation_actions,
        "required_documents": required_documents,
        "export_blocks": {
            "markdown": _build_export_markdown(
                title=_safe_text(detail.get("title")) or str(notice_id),
                decision=recommended_decision["value"],
                lines=memo_lines,
            ),
            "short_summary": short_summary,
        },
        "safety": {
            "real_api_call_attempted": False,
            "source_data_mode": source_mode,
        },
        "service_key_exposed": False,
    }


def _fit_reasons(detail: dict[str, Any]) -> list[str]:
    reasons = [
        _safe_text(value)
        for value in (detail.get("decision_reasons") or detail.get("reasons") or [])
    ]
    reasons = [value for value in reasons if value]
    if reasons:
        return reasons[:4]
    fit_summary = _safe_text(detail.get("fit_summary"))
    return [fit_summary] if fit_summary else []


def _concern_reasons(detail: dict[str, Any]) -> list[str]:
    concerns = [_safe_text(value) for value in (detail.get("risks") or [])]
    if concerns and concerns != ["[empty-risk-summary]"]:
        return [value for value in concerns if value][:4]
    categories = detail.get("risk_categories") or []
    messages = [
        _safe_text(entry.get("message"))
        for entry in categories
        if isinstance(entry, dict)
        and str(entry.get("level") or "").casefold() in {"high", "medium"}
    ]
    return [value for value in messages if value][:4]


def _risk_summary(
    detail: dict[str, Any],
    *,
    deadline_status: str,
    required_documents: list[dict[str, Any]],
) -> dict[str, list[str]]:
    categories = detail.get("risk_categories") or []
    grouped = {
        "eligibility_risks": [],
        "document_risks": [],
        "schedule_risks": [],
        "commercial_risks": [],
    }
    for entry in categories:
        if not isinstance(entry, dict):
            continue
        message = _safe_text(entry.get("message"))
        category = _safe_text(entry.get("category"))
        if not message:
            continue
        if category in {"eligibility_risk", "evidence_risk"}:
            grouped["eligibility_risks"].append(message)
        elif category == "deadline_risk":
            grouped["schedule_risks"].append(message)
        elif category in {"scope_risk", "budget_risk", "consortium_risk"}:
            grouped["commercial_risks"].append(message)
        else:
            grouped["commercial_risks"].append(message)

    for document in required_documents:
        if str(document.get("status") or "").casefold() in {"check", "optional"}:
            grouped["document_risks"].append(
                "Check document readiness: "
                f"{_safe_text(document.get('name')) or 'unknown document'}."
            )

    if deadline_status in {"overdue", "due_soon"}:
        grouped["schedule_risks"].append(
            f"Deadline status is {deadline_status}; same-day operator review may be required."
        )

    existing_risks = [_safe_text(value) for value in (detail.get("risks") or [])]
    for risk in existing_risks:
        if risk and risk != "[empty-risk-summary]":
            grouped["commercial_risks"].append(risk)

    return {key: _dedupe(values) for key, values in grouped.items()}


def _deadline_next_action(
    detail: dict[str, Any],
    *,
    deadline: str,
    deadline_status: str,
) -> dict[str, Any]:
    days_remaining = _days_remaining(deadline)
    next_action = _safe_text(detail.get("next_action"))
    if not next_action:
        action_plan = detail.get("action_plan") or {}
        next_action = (
            _safe_text(action_plan.get("today_action"))
            or _safe_text(detail.get("recommended_action"))
            or "Confirm eligibility, documents, and bid timing."
        )
    return {
        "deadline": deadline,
        "days_remaining": days_remaining,
        "urgency": deadline_status,
        "next_action": next_action,
    }


def _recommended_decision(
    detail: dict[str, Any],
    *,
    score: int,
    risk_level: str,
    manual_decision: dict[str, Any],
) -> dict[str, str]:
    generated = _generated_recommended_decision(detail, score=score, risk_level=risk_level)
    if manual_decision["persisted"] and manual_decision["decision"]:
        rationale = manual_decision["note"] or generated["rationale"]
        return {
            "value": manual_decision["decision"],
            "rationale": rationale,
        }


    return generated


def _generated_recommended_decision(
    detail: dict[str, Any],
    *,
    score: int,
    risk_level: str,
) -> dict[str, str]:
    review_status = _safe_text(detail.get("review_status")).casefold()
    decision_label = _safe_text(detail.get("decision_label")).casefold()
    go_no_go = _safe_text(detail.get("go_no_go_recommendation"))
    priority = _safe_text(detail.get("bid_priority"))

    if review_status == "no_go" or go_no_go == "No-Go" or decision_label == "not_recommended":
        value = "Reject"
        rationale = (
            "Current local-safe evidence indicates a low-fit "
            "or structurally blocked notice."
        )
    elif review_status == "hold" or go_no_go == "Hold" or priority == "Hold":
        value = "Hold"
        rationale = (
            "This notice should stay visible, but it is not ready "
            "for immediate proposal effort."
        )
    elif review_status == "go" or go_no_go == "Go" or (
        decision_label == "strong_recommend" and score >= 80 and risk_level != "high"
    ):
        value = "Prepare"
        rationale = (
            "Fit is strong enough to begin preparation from the "
            "current saved notice evidence."
        )
    else:
        value = "Review"
        rationale = (
            "The notice looks promising, but operator review is still "
            "needed before commitment."
        )

    if value not in ALLOWED_DECISIONS:
        value = "Review"
    return {"value": value, "rationale": rationale}


def _empty_manual_decision() -> dict[str, Any]:
    return {
        "decision": "",
        "note": "",
        "updated_at": "",
        "persisted": False,
    }


def _normalize_manual_decision(manual_decision: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(manual_decision, dict):
        return _empty_manual_decision()

    decision = _safe_text(manual_decision.get("decision"))
    if decision not in ALLOWED_DECISIONS:
        decision = ""
    note = _safe_text(manual_decision.get("note"))
    updated_at = _safe_text(manual_decision.get("updated_at"))
    persisted = bool(manual_decision.get("persisted") or decision or note or updated_at)
    return {
        "decision": decision,
        "note": note,
        "updated_at": updated_at,
        "persisted": persisted,
    }


def _preparation_actions(
    detail: dict[str, Any],
    *,
    required_documents: list[dict[str, Any]],
) -> list[dict[str, str]]:
    owner = _safe_text(detail.get("owner")) or "unassigned"
    action_plan = detail.get("action_plan") or {}
    actions = [
        {
            "action": (
                _safe_text(action_plan.get("today_action"))
                or "Review current notice scope and urgency."
            ),
            "owner": owner,
            "priority": "high",
            "evidence": _safe_text(detail.get("why_now")) or "Derived from current notice timing.",
        },
        {
            "action": (
                _safe_text(action_plan.get("document_action"))
                or "Check eligibility and required documents."
            ),
            "owner": owner,
            "priority": "high",
            "evidence": ", ".join(
                _safe_text(document.get("name")) for document in required_documents[:3]
            ) or "Required document metadata.",
        },
        {
            "action": (
                _safe_text(action_plan.get("business_action"))
                or "Align YOnLab fit and proposal strategy."
            ),
            "owner": owner,
            "priority": "medium",
            "evidence": (
                _safe_text(detail.get("bid_strategy"))
                or _safe_text(detail.get("fit_summary"))
            ),
        },
    ]
    return [entry for entry in actions if entry["action"]]


def _required_documents(detail: dict[str, Any]) -> list[dict[str, str]]:
    documents = detail.get("required_documents")
    if not isinstance(documents, list):
        return []
    normalized = []
    for document in documents:
        if isinstance(document, dict):
            normalized.append(
                {
                    "name": _safe_text(document.get("name")),
                    "status": _safe_text(document.get("status")) or "required",
                    "reason": _safe_text(document.get("reason")),
                }
            )
        else:
            normalized.append({"name": _safe_text(document), "status": "required", "reason": ""})
    return [entry for entry in normalized if entry["name"]]


def _main_risk_line(risk_summary: dict[str, list[str]]) -> str:
    for key in ("eligibility_risks", "schedule_risks", "document_risks", "commercial_risks"):
        values = risk_summary.get(key) or []
        if values:
            return values[0]
    return "No material risk was identified from the current local-safe metadata."


def _build_export_markdown(*, title: str, decision: str, lines: list[str]) -> str:
    body = "\n".join(f"- {line}" for line in lines if line)
    return "\n".join(
        [
            "# YOnLab Decision Memo",
            "",
            f"## {title}",
            "",
            f"- Decision: {decision}",
            body,
            "",
        ]
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


def _days_remaining(value: Any) -> int | None:
    parsed = _parse_deadline(value)
    if parsed is None:
        return None
    return (parsed - date.today()).days


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


def _safe_url(value: Any) -> str:
    text = _safe_text(value)
    return text if text.startswith(("http://", "https://", "/")) else ""


def _dedupe(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        if value and value not in result:
            result.append(value)
    return result


def _safe_text(value: Any) -> str:
    text = "" if value is None else str(value)
    if not text.strip():
        return ""
    text = WINDOWS_PATH_RE.sub("[local-path-redacted]", text)
    text = text.replace("serviceKey", "[redacted-key-field]")
    text = text.replace("SERVICE_KEY", "[redacted-key-field]")
    text = text.replace(".env", "[env-redacted]")
    return text
