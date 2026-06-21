from pathlib import Path
import json
import re
from typing import Any

from pydantic import BaseModel

SAFE_FILENAME_PATTERN = re.compile(r"[^0-9A-Za-z가-힣._-]+")


def ensure_report_run_dir(report_dir: str | Path, run_id: str) -> Path:
    run_dir = Path(report_dir) / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def write_markdown_report(
    *,
    report_dir: str | Path,
    run_id: str,
    rank: int,
    notice_id: str,
    markdown: str,
) -> str:
    run_dir = ensure_report_run_dir(report_dir, run_id)
    path = run_dir / f"{rank:02d}_{safe_filename(notice_id)}.md"
    path.write_text(markdown, encoding="utf-8")
    return path.as_posix()


def write_raw_recommendation_json(
    *,
    report_dir: str | Path,
    run_id: str,
    rank: int,
    notice_id: str,
    payload: Any,
) -> str:
    run_dir = ensure_report_run_dir(report_dir, run_id)
    path = run_dir / f"{rank:02d}_{safe_filename(notice_id)}.json"
    path.write_text(
        json.dumps(_jsonable(payload), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path.as_posix()


def safe_filename(value: str) -> str:
    cleaned = SAFE_FILENAME_PATTERN.sub("_", value.strip())
    cleaned = cleaned.strip("._")
    return cleaned[:80] or "notice"


def _jsonable(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    return value
