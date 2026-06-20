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
