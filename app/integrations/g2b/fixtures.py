import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.domain.bid_notice import BidNotice
from app.integrations.g2b.normalizer import normalize_g2b_notice

FIXTURE_PATH = (
    Path(__file__).resolve().parents[3]
    / "data"
    / "fixtures"
    / "g2b"
    / "sample_notices.json"
)


@lru_cache
def load_sample_g2b_notices() -> list[dict[str, Any]]:
    with FIXTURE_PATH.open("r", encoding="utf-8") as fixture_file:
        notices = json.load(fixture_file)
    if not isinstance(notices, list):
        raise ValueError("G2B sample fixture must be a list of notices.")
    return notices


def load_normalized_sample_notices() -> list[BidNotice]:
    return [normalize_g2b_notice(notice) for notice in load_sample_g2b_notices()]


def search_sample_g2b_notices(
    keyword: str | None = None,
    region: str | None = None,
    business_type: str | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    notices = load_sample_g2b_notices()
    filtered = [
        notice
        for notice in notices
        if _matches_notice(notice, keyword=keyword, region=region, business_type=business_type)
    ]
    if limit is not None:
        return filtered[:limit]
    return filtered


def _matches_notice(
    raw_notice: dict[str, Any],
    keyword: str | None,
    region: str | None,
    business_type: str | None,
) -> bool:
    notice = normalize_g2b_notice(raw_notice)
    if keyword and keyword.casefold() not in _fixture_search_text(notice):
        return False
    if region and region.casefold() not in notice.region.casefold():
        return False
    if business_type and business_type.casefold() not in notice.business_type.casefold():
        return False
    return True


def _fixture_search_text(notice: BidNotice) -> str:
    values = [
        notice.title,
        notice.description,
        notice.qualification_text,
        *notice.keywords,
    ]
    return " ".join(value for value in values if value).casefold()
