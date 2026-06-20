import json
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

import app.api.routes as routes
from app.core.config import Settings
from app.domain.bid_notice import BidNotice
from app.integrations.g2b.detail_queue import (
    build_detail_analysis_queue,
    build_detail_analysis_queue_item,
)
from app.integrations.g2b.normalizer import normalize_g2b_notice
from app.main import app

client = TestClient(app)
PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_detail_analysis_queue_extracts_detail_urls_attachments_and_risk_metadata() -> None:
    notices = [normalize_g2b_notice(item) for item in _load_real_service_search_items()]

    queue = build_detail_analysis_queue(notices)

    assert len(queue) == 3
    first = queue[0]
    assert first.notice_id == "R26BK01540922"
    assert first.analysis_status == "queued"
    assert first.download_attempted is False
    assert first.detail_url.endswith("bidPbancNo=R26BK01540922&bidPbancOrd=000")
    assert first.notice_url == first.detail_url
    assert [attachment.sequence for attachment in first.attachments] == [1, 2, 3]
    assert first.attachments[0].file_name == "notice_R26BK01540922.hwpx"
    assert first.attachments[0].download_attempted is False
    assert first.risk_metadata["industry_limited"] is True
    assert "industry_limited" in first.risk_metadata["risk_flags"]
    assert "high_technical_evaluation_weight" in first.risk_metadata["risk_flags"]
    assert "ServiceKey" not in str(first)


def test_detail_analysis_queue_flags_missing_deadline_without_downloading() -> None:
    notices = [normalize_g2b_notice(item) for item in _load_real_service_search_items()]

    queue = build_detail_analysis_queue(notices)

    second = queue[1]
    assert second.notice_id == "R26BK01553148"
    assert "missing_deadline" in second.risk_metadata["risk_flags"]
    assert len(second.attachments) == 2
    assert all(attachment.download_attempted is False for attachment in second.attachments)


def test_detail_analysis_queue_strips_secret_query_parameters() -> None:
    notice = BidNotice(
        notice_id="SAFE-001",
        title="Secret stripping fixture",
        raw_source={
            "bidNtceDtlUrl": "https://example.test/detail?service_key=placeholder&bidPbancNo=SAFE-001",
            "ntceSpecDocUrl1": "https://example.test/file?service_key=placeholder&fileSeq=1",
            "ntceSpecFileNm1": "safe.pdf",
        },
    )

    item = build_detail_analysis_queue_item(notice)

    assert "service_key" not in item.detail_url
    assert "service_key" not in item.attachments[0].url


def test_g2b_search_real_response_includes_detail_analysis_queue(monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.setattr(routes, "get_settings", _real_api_settings)
    monkeypatch.setattr(routes, "G2BClient", _FakeG2BClient)

    response = client.post(
        "/g2b/search",
        json={
            "mode": "real",
            "keyword": "AI",
            "start_date": "2026-06-01",
            "end_date": "2026-06-20",
            "active_only": False,
            "confirm_real_api_call": True,
        },
    )

    payload = response.json()
    assert payload["ok"] is True
    assert len(payload["detail_analysis_queue"]) == 3
    first = payload["detail_analysis_queue"][0]
    assert first["notice_id"] == "R26BK01540922"
    assert first["detail_url"].endswith("bidPbancNo=R26BK01540922&bidPbancOrd=000")
    assert len(first["attachments"]) == 3
    assert first["download_attempted"] is False
    assert first["attachments"][0]["download_attempted"] is False
    assert "SECRET-KEY" not in str(payload)
    assert "ServiceKey" not in str(payload)


def test_g2b_recommendations_real_response_carries_detail_analysis_queue(monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.setattr(routes, "get_settings", _real_api_settings)
    monkeypatch.setattr(routes, "G2BClient", _FakeG2BClient)

    response = client.post(
        "/g2b/recommendations",
        json={
            "mode": "real",
            "keyword": "AI",
            "start_date": "2026-06-01",
            "end_date": "2026-06-20",
            "include_reports": False,
            "active_only": False,
            "confirm_real_api_call": True,
        },
    )

    payload = response.json()
    assert payload["ok"] is True
    assert len(payload["recommendations"]) == 3
    assert len(payload["detail_analysis_queue"]) == 3
    assert payload["detail_analysis_queue"][0]["analysis_status"] == "queued"
    assert payload["detail_analysis_queue"][0]["risk_metadata"]["industry_limited"] is True
    assert "SECRET-KEY" not in str(payload)


def test_g2b_fixture_search_keeps_detail_analysis_queue_empty() -> None:
    response = client.post("/g2b/search", json={"mode": "fixture", "keyword": "AI"})

    payload = response.json()
    assert payload["ok"] is True
    assert payload["detail_analysis_queue"] == []


class _FakeG2BClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def search(self, request: Any) -> list[dict[str, Any]]:
        return _load_real_service_search_items()


def _real_api_settings() -> Settings:
    return Settings(
        g2b_enable_real_api=True,
        g2b_api_service_key="SECRET-KEY",
        g2b_list_endpoint_path="/1230000/ad/BidPublicInfoService/getBidPblancListInfoServcPPSSrch",
    )


def _load_real_service_search_items() -> list[dict[str, Any]]:
    payload = json.loads(
        (PROJECT_ROOT / "data" / "fixtures" / "g2b" / "real_servc_search_sample.json").read_text(
            encoding="utf-8"
        )
    )
    return payload["response"]["body"]["items"]
