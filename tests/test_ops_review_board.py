import json
from pathlib import Path

from fastapi.testclient import TestClient

import app.api.routes as routes
from app.core.config import Settings
from app.main import app

client = TestClient(app)


def test_ops_review_board_returns_deadline_first_active_cards(
    tmp_path: Path,
    monkeypatch,
) -> None:  # noqa: ANN001
    settings = _tmp_settings(tmp_path, g2b_api_service_key="LOCAL_ONLY_SECRET")
    monkeypatch.setattr(routes, "get_settings", lambda: settings)
    monkeypatch.setattr(
        routes,
        "build_opportunity_inbox",
        lambda **kwargs: {
            "status": "success",
            "source_mode": "saved",
            "items": _sample_items(),
            "service_key_exposed": False,
            "real_api_call_attempted": False,
        },
    )

    response = client.get("/ops/review-board")

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) >= {
        "generated_at",
        "source",
        "status",
        "total_count",
        "active_count",
        "deadline_first_actions",
        "status_counts",
        "filters",
        "cards",
        "service_key_exposed",
        "real_api_call_attempted",
    }
    assert payload["source"] == "saved"
    assert payload["status"] == "success"
    assert payload["total_count"] == 4
    assert payload["active_count"] == 4
    assert [item["notice_id"] for item in payload["deadline_first_actions"]] == [
        "REVIEWING-OVERDUE",
        "GO-SOON",
        "HOLD-NO-DEADLINE",
    ]
    assert [card["review_status"] for card in payload["cards"]] == [
        "go",
        "reviewing",
        "shortlisted",
        "hold",
    ]
    assert payload["cards"][0]["filter_payload"] == {
        "review_status": "go",
        "shortlisted_only": False,
        "hide_archived_no_go": True,
        "sort": "score_desc",
    }
    first_item = payload["cards"][1]["items"][0]
    assert set(first_item) >= {
        "notice_id",
        "title",
        "agency",
        "deadline",
        "deadline_status",
        "review_status",
        "score",
        "risk_level",
        "next_action",
        "filter_payload",
    }
    assert first_item["deadline_status"] == "overdue"
    assert payload["service_key_exposed"] is False
    assert payload["real_api_call_attempted"] is False
    assert "LOCAL_ONLY_SECRET" not in json.dumps(payload, ensure_ascii=False)
    assert "D:\\Deploy" not in json.dumps(payload, ensure_ascii=False)


def test_ops_review_board_returns_safe_empty_state_when_source_missing(
    tmp_path: Path,
    monkeypatch,
) -> None:  # noqa: ANN001
    settings = _tmp_settings(tmp_path)
    monkeypatch.setattr(routes, "get_settings", lambda: settings)
    monkeypatch.setattr(
        routes,
        "build_opportunity_inbox",
        lambda **kwargs: {
            "status": "empty",
            "source_mode": "empty",
            "items": [],
            "service_key_exposed": False,
            "real_api_call_attempted": False,
        },
    )

    response = client.get("/ops/review-board")

    assert response.status_code == 200
    payload = response.json()
    assert payload["source"] == "empty"
    assert payload["status"] == "empty"
    assert payload["total_count"] == 0
    assert payload["active_count"] == 0
    assert payload["deadline_first_actions"] == []
    assert payload["filters"]["hide_archived_no_go"] is True
    assert payload["status_counts"] == {
        "new": 0,
        "shortlisted": 0,
        "reviewing": 0,
        "go": 0,
        "hold": 0,
        "no_go": 0,
        "submitted": 0,
        "archived": 0,
    }
    assert [card["count"] for card in payload["cards"]] == [0, 0, 0, 0]
    assert payload["service_key_exposed"] is False
    assert payload["real_api_call_attempted"] is False


def test_ops_review_board_never_calls_real_g2b_api(
    tmp_path: Path,
    monkeypatch,
) -> None:  # noqa: ANN001
    class FailingClient:
        def __init__(self, *args, **kwargs):  # noqa: ANN002, ANN003
            raise AssertionError("Review board endpoint must not call real G2B API.")

    settings = _tmp_settings(tmp_path, g2b_api_service_key="LOCAL_ONLY_SECRET")
    monkeypatch.setattr(routes, "get_settings", lambda: settings)
    monkeypatch.setattr(routes, "G2BClient", FailingClient)
    monkeypatch.setattr(
        routes,
        "build_opportunity_inbox",
        lambda **kwargs: {
            "status": "demo",
            "source_mode": "demo",
            "items": _sample_items()[:1],
            "service_key_exposed": False,
            "real_api_call_attempted": False,
        },
    )

    response = client.get("/ops/review-board")

    assert response.status_code == 200
    payload = response.json()
    assert payload["source"] == "demo"
    assert payload["service_key_exposed"] is False
    assert payload["real_api_call_attempted"] is False
    assert "LOCAL_ONLY_SECRET" not in json.dumps(payload, ensure_ascii=False)


def _sample_items() -> list[dict]:
    return [
        {
            "notice_id": "GO-SOON",
            "title": "AI support service",
            "agency": "Agency A",
            "deadline": "2099-01-02",
            "review_status": "go",
            "review_status_ko": "go",
            "score": 91,
            "risk_level": "low",
            "next_action": "Prepare final review note",
            "note": "private note should not leak",
        },
        {
            "notice_id": "REVIEWING-OVERDUE",
            "title": "Device Farm verification",
            "agency": "Agency B",
            "deadline": "2000-01-01",
            "review_status": "reviewing",
            "review_status_ko": "reviewing",
            "score": 85,
            "risk_level": "medium",
            "next_action": "Confirm overdue eligibility",
            "note": "LOCAL_ONLY_SECRET and D:\\Deploy\\private.txt",
        },
        {
            "notice_id": "SHORTLISTED-NO-ACTION",
            "title": "Cloud AI system",
            "agency": "Agency C",
            "deadline": "2099-01-10",
            "review_status": "shortlisted",
            "review_status_ko": "shortlisted",
            "score": 80,
            "risk_level": "low",
            "next_action": "",
        },
        {
            "notice_id": "HOLD-NO-DEADLINE",
            "title": "General software operation",
            "agency": "Agency D",
            "deadline": "",
            "review_status": "hold",
            "review_status_ko": "hold",
            "score": 70,
            "risk_level": "high",
            "next_action": "Monitor next amendment",
        },
    ]


def _tmp_settings(tmp_path: Path, **overrides) -> Settings:  # noqa: ANN001
    values = {
        "yonlab_storage_db_path": str(tmp_path / "ops" / "yonlab.sqlite3"),
        "yonlab_report_dir": str(tmp_path / "reports"),
        "yonlab_default_run_mode": "fixture",
        "yonlab_default_keyword": "AI",
        "yonlab_default_num_rows": 3,
    }
    values.update(overrides)
    return Settings(**values)
