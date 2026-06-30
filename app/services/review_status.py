from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

ReviewStatusValue = Literal[
    "new",
    "shortlisted",
    "reviewing",
    "go",
    "hold",
    "no_go",
    "submitted",
    "archived",
]
ManualDecisionValue = Literal["Prepare", "Review", "Hold", "Reject"]

REVIEW_STATUS_LABELS_KO: dict[str, str] = {
    "new": "신규",
    "shortlisted": "관심 공고",
    "reviewing": "검토 중",
    "go": "대응",
    "hold": "보류",
    "no_go": "비추천",
    "submitted": "제출 완료",
    "archived": "보관",
}
SHORTLIST_STATUSES = {"shortlisted", "reviewing", "go"}
HIDDEN_STATUSES = {"archived", "no_go"}


class ReviewStatusUpdate(BaseModel):
    review_status: ReviewStatusValue = "new"
    owner: str = Field(default="", max_length=80)
    note: str = Field(default="", max_length=1200)
    next_action: str = Field(default="", max_length=300)
    source_run_id: str = Field(default="", max_length=120)


class ManualDecisionUpdate(BaseModel):
    decision: ManualDecisionValue
    note: str = Field(default="", max_length=1200)


def review_status_storage_path(db_path: str | Path) -> Path:
    return Path(db_path).with_name("review_status.json")


def build_default_review_status(notice_id: str) -> dict[str, Any]:
    return {
        "notice_id": str(notice_id),
        "source_run_id": "",
        "review_status": "new",
        "review_status_ko": REVIEW_STATUS_LABELS_KO["new"],
        "owner": "",
        "note": "",
        "note_preview": "",
        "next_action": "",
        "updated_at": "",
        "manual_decision": "",
        "manual_decision_note": "",
        "manual_decision_updated_at": "",
        "manual_decision_persisted": False,
        "persisted": False,
        "service_key_exposed": False,
        "real_api_call_attempted": False,
    }


def normalize_manual_decision_state(source: dict[str, Any] | None) -> dict[str, Any]:
    if source is None:
        return {
            "decision": "",
            "note": "",
            "updated_at": "",
            "persisted": False,
        }

    decision = _sanitize_local_text(source.get("manual_decision"))
    if decision not in {"Prepare", "Review", "Hold", "Reject"}:
        decision = ""
    note = _sanitize_local_text(source.get("manual_decision_note"))
    updated_at = _sanitize_local_text(source.get("manual_decision_updated_at"))
    persisted = bool(
        source.get("manual_decision_persisted") or decision or note or updated_at
    )
    return {
        "decision": decision,
        "note": note,
        "updated_at": updated_at,
        "persisted": persisted,
    }


def list_review_statuses(db_path: str | Path) -> list[dict[str, Any]]:
    records = _load_records(review_status_storage_path(db_path))
    return [
        _record_response(notice_id, record, persisted=True)
        for notice_id, record in sorted(records.items())
    ]


def get_review_status(db_path: str | Path, notice_id: str) -> dict[str, Any]:
    records = _load_records(review_status_storage_path(db_path))
    record = records.get(str(notice_id))
    if record is None:
        return build_default_review_status(str(notice_id))
    return _record_response(str(notice_id), record, persisted=True)


def save_review_status(
    db_path: str | Path,
    notice_id: str,
    payload: ReviewStatusUpdate,
) -> dict[str, Any]:
    path = review_status_storage_path(db_path)
    records = _load_records(path)
    existing = records.get(str(notice_id), {})
    records[str(notice_id)] = {
        "notice_id": str(notice_id),
        "source_run_id": payload.source_run_id.strip(),
        "review_status": payload.review_status,
        "owner": payload.owner.strip(),
        "note": payload.note.strip(),
        "next_action": payload.next_action.strip(),
        "updated_at": _iso_timestamp(),
        "manual_decision": existing.get("manual_decision", ""),
        "manual_decision_note": existing.get("manual_decision_note", ""),
        "manual_decision_updated_at": existing.get("manual_decision_updated_at", ""),
    }
    _save_records(path, records)
    return _record_response(str(notice_id), records[str(notice_id)], persisted=True)


def save_manual_decision(
    db_path: str | Path,
    notice_id: str,
    payload: ManualDecisionUpdate,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    path = review_status_storage_path(db_path)
    records = _load_records(path)
    record = dict(records.get(str(notice_id), {}))
    record["notice_id"] = str(notice_id)
    record["manual_decision"] = payload.decision
    record["manual_decision_note"] = _sanitize_local_text(payload.note.strip())
    record["manual_decision_updated_at"] = _iso_timestamp(now)
    records[str(notice_id)] = record
    _save_records(path, records)
    return _record_response(str(notice_id), record, persisted=True)


def delete_review_status(db_path: str | Path, notice_id: str) -> dict[str, Any]:
    path = review_status_storage_path(db_path)
    records = _load_records(path)
    deleted = str(notice_id) in records
    records.pop(str(notice_id), None)
    if deleted:
        _save_records(path, records)
    response = build_default_review_status(str(notice_id))
    response["deleted"] = deleted
    return response


def merge_review_statuses(
    items: list[dict[str, Any]],
    *,
    db_path: str | Path,
    review_status: str | None = None,
    shortlisted_only: bool = False,
    hide_archived_no_go: bool = False,
) -> list[dict[str, Any]]:
    records = _load_records(review_status_storage_path(db_path))
    merged = [_merge_item(item, records.get(str(item.get("notice_id") or ""))) for item in items]
    if review_status:
        merged = [
            item
            for item in merged
            if str(item.get("review_status") or "new") == review_status
        ]
    if shortlisted_only:
        merged = [
            item
            for item in merged
            if str(item.get("review_status") or "new") in SHORTLIST_STATUSES
        ]
    if hide_archived_no_go:
        merged = [
            item
            for item in merged
            if str(item.get("review_status") or "new") not in HIDDEN_STATUSES
        ]
    return merged


def _merge_item(item: dict[str, Any], record: dict[str, Any] | None) -> dict[str, Any]:
    notice_id = str(item.get("notice_id") or "")
    status = _record_response(notice_id, record, persisted=record is not None)
    merged = dict(item)
    merged.update(
        {
            "review_status": status["review_status"],
            "review_status_ko": status["review_status_ko"],
            "owner": status["owner"],
            "note": status["note"],
            "note_preview": status["note_preview"],
            "next_action": status["next_action"],
            "updated_at": status["updated_at"],
            "review_status_persisted": status["persisted"],
            "manual_decision": status["manual_decision"],
            "manual_decision_note": status["manual_decision_note"],
            "manual_decision_updated_at": status["manual_decision_updated_at"],
            "manual_decision_persisted": status["manual_decision_persisted"],
        }
    )
    return merged


def _record_response(
    notice_id: str,
    record: dict[str, Any] | None,
    *,
    persisted: bool,
) -> dict[str, Any]:
    if record is None:
        return build_default_review_status(notice_id)
    status = str(record.get("review_status") or "new")
    if status not in REVIEW_STATUS_LABELS_KO:
        status = "new"
    note = _sanitize_local_text(record.get("note"))
    manual_decision_state = normalize_manual_decision_state(record)
    return {
        "notice_id": notice_id,
        "source_run_id": _sanitize_local_text(record.get("source_run_id")),
        "review_status": status,
        "review_status_ko": REVIEW_STATUS_LABELS_KO[status],
        "owner": _sanitize_local_text(record.get("owner")),
        "note": note,
        "note_preview": _note_preview(note),
        "next_action": _sanitize_local_text(record.get("next_action")),
        "updated_at": _sanitize_local_text(record.get("updated_at")),
        "manual_decision": manual_decision_state["decision"],
        "manual_decision_note": manual_decision_state["note"],
        "manual_decision_updated_at": manual_decision_state["updated_at"],
        "manual_decision_persisted": manual_decision_state["persisted"],
        "persisted": persisted,
        "service_key_exposed": False,
        "real_api_call_attempted": False,
    }


def _load_records(path: Path) -> dict[str, dict[str, Any]]:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    if not isinstance(payload, dict):
        return {}
    records = payload.get("items", payload)
    if not isinstance(records, dict):
        return {}
    return {
        str(notice_id): record
        for notice_id, record in records.items()
        if isinstance(record, dict)
    }


def _save_records(path: Path, records: dict[str, dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema": "yonlab.review_status.v1",
                "updated_at": _iso_timestamp(),
                "items": records,
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )


def _note_preview(value: str) -> str:
    text = _sanitize_local_text(value)
    if len(text) <= 160:
        return text
    return f"{text[:157]}..."


def _sanitize_local_text(value: Any) -> str:
    text = "" if value is None else str(value)
    text = text.replace("serviceKey", "[redacted-key-field]")
    text = text.replace("SERVICE_KEY", "[redacted-key-field]")
    text = text.replace(".env", "[env-redacted]")
    return text


def _iso_timestamp(now: datetime | None = None) -> str:
    timestamp = datetime.now(UTC) if now is None else now
    return timestamp.isoformat(timespec="seconds")
