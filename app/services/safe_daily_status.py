from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

WINDOWS_PATH_RE = re.compile(r"[A-Za-z]:\\")


def build_safe_daily_status(*, deploy_path: str | Path) -> dict[str, Any]:
    root = Path(deploy_path).resolve()
    latest_log = _latest_safe_daily_log(root)
    latest_result = "none"
    real_api_call_attempted = False
    service_key_exposed = False
    latest_created_at = None
    latest_filename = None

    if latest_log is not None:
        latest_filename = latest_log.name
        latest_created_at = datetime.fromtimestamp(
            latest_log.stat().st_mtime,
            tz=UTC,
        ).isoformat(timespec="seconds")
        parsed = _parse_log_status(latest_log)
        latest_result = str(parsed.get("result") or parsed.get("status") or "unknown")
        real_api_call_attempted = bool(parsed.get("real_api_call_attempted", False))
        service_key_exposed = bool(parsed.get("service_key_exposed", False))

    status = "success" if latest_result == "success" else "empty"
    if latest_log is not None and latest_result not in {"success", "none"}:
        status = "unknown"

    return {
        "status": status,
        "latest_log_filename": latest_filename,
        "latest_log_created_at": latest_created_at,
        "latest_result": latest_result,
        "real_api_call_attempted": real_api_call_attempted,
        "service_key_exposed": service_key_exposed,
        "scheduler_target_expected": "scripts/run_ops_safe_daily.ps1",
        "active_deployment_path": str(root),
        "note": (
            "Last safe check uses local validation only. Scheduler target verification "
            "is documented in the operator runbook."
        ),
    }


def _latest_safe_daily_log(root: Path) -> Path | None:
    candidates = []
    for logs_dir in (root / "logs", root / "data" / "logs"):
        if logs_dir.is_dir():
            candidates.extend(logs_dir.rglob("*safe_daily*.log"))
            candidates.extend(logs_dir.rglob("*ops_safe*.log"))
    if not candidates:
        return None
    return max(candidates, key=lambda path: path.stat().st_mtime)


def _parse_log_status(log_path: Path) -> dict[str, Any]:
    text = _sanitize_text(log_path.read_text(encoding="utf-8", errors="replace"))
    parsed = _parse_json_object(text)
    if parsed:
        return parsed
    return {
        "status": "success" if "success" in text.casefold() else "unknown",
        "real_api_call_attempted": '"real_api_call_attempted": true' in text.casefold(),
        "service_key_exposed": '"service_key_exposed": true' in text.casefold(),
    }


def _parse_json_object(text: str) -> dict[str, Any]:
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        return {}
    try:
        payload = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _sanitize_text(value: str) -> str:
    return WINDOWS_PATH_RE.sub("[local-path-redacted]", value).replace("serviceKey", "redacted")
