import json
from pathlib import Path

from fastapi.testclient import TestClient

import app.api.routes as routes
from app.core.config import Settings
from app.main import app

client = TestClient(app)


def test_review_status_create_update_delete_api_is_local_only(
    tmp_path: Path,
    monkeypatch,
) -> None:  # noqa: ANN001
    class FailingClient:
        def __init__(self, *args, **kwargs):  # noqa: ANN002, ANN003
            raise AssertionError("Review status API must not call real G2B API.")

    settings = _tmp_settings(tmp_path, g2b_api_service_key="LOCAL_ONLY_SECRET")
    status_path = _status_path(settings)
    monkeypatch.setattr(routes, "get_settings", lambda: settings)
    monkeypatch.setattr(routes, "G2BClient", FailingClient)

    missing = client.get("/ops/review-status/NOTICE-1")

    assert missing.status_code == 200
    assert missing.json()["review_status"] == "new"
    assert missing.json()["persisted"] is False
    assert not status_path.exists()

    created = client.post(
        "/ops/review-status/NOTICE-1",
        json={
            "review_status": "shortlisted",
            "owner": "YOnLab",
            "note": "Local private memo only.",
            "next_action": "Review proposal fit today.",
            "source_run_id": "run_fixture",
        },
    )

    assert created.status_code == 200
    payload = created.json()
    assert payload["notice_id"] == "NOTICE-1"
    assert payload["review_status"] == "shortlisted"
    assert payload["review_status_ko"] == "관심 공고"
    assert payload["owner"] == "YOnLab"
    assert payload["note"] == "Local private memo only."
    assert payload["next_action"] == "Review proposal fit today."
    assert payload["service_key_exposed"] is False
    assert payload["real_api_call_attempted"] is False
    assert "LOCAL_ONLY_SECRET" not in json.dumps(payload, ensure_ascii=False)
    assert status_path.is_file()

    listed = client.get("/ops/review-status").json()
    assert listed["total_items"] == 1
    assert listed["items"][0]["notice_id"] == "NOTICE-1"

    deleted = client.delete("/ops/review-status/NOTICE-1")

    assert deleted.status_code == 200
    assert deleted.json()["deleted"] is True
    assert client.get("/ops/review-status/NOTICE-1").json()["review_status"] == "new"


def test_review_status_rejects_invalid_status_and_overlong_fields(
    tmp_path: Path,
    monkeypatch,
) -> None:  # noqa: ANN001
    settings = _tmp_settings(tmp_path)
    monkeypatch.setattr(routes, "get_settings", lambda: settings)

    invalid_status = client.post(
        "/ops/review-status/NOTICE-1",
        json={"review_status": "maybe"},
    )
    overlong_note = client.post(
        "/ops/review-status/NOTICE-1",
        json={"review_status": "hold", "note": "x" * 1201},
    )

    assert invalid_status.status_code == 422
    assert overlong_note.status_code == 422
    assert not _status_path(settings).exists()


def test_opportunity_inbox_merges_and_filters_review_status(
    tmp_path: Path,
    monkeypatch,
) -> None:  # noqa: ANN001
    settings = _tmp_settings(tmp_path)
    monkeypatch.setattr(routes, "get_settings", lambda: settings)
    run = client.post(
        "/ops/run-recommendations",
        json={"mode": "fixture", "keyword": "AI", "num_rows": 3, "include_reports": True},
    ).json()
    inbox = client.get("/ops/opportunity-inbox").json()
    notice_id = inbox["items"][0]["notice_id"]

    client.post(
        f"/ops/review-status/{notice_id}",
        json={
            "review_status": "reviewing",
            "owner": "ops",
            "next_action": "Confirm eligibility documents.",
            "note": "Private memo should stay preview-only in lists.",
            "source_run_id": run["run_id"],
        },
    )

    filtered = client.get(
        "/ops/opportunity-inbox",
        params={"review_status": "reviewing"},
    ).json()
    shortlisted = client.get(
        "/ops/opportunity-inbox",
        params={"shortlisted_only": "true"},
    ).json()

    assert filtered["items"]
    assert {item["notice_id"] for item in filtered["items"]} == {notice_id}
    item = filtered["items"][0]
    assert item["review_status"] == "reviewing"
    assert item["review_status_ko"] == "검토 중"
    assert item["owner"] == "ops"
    assert item["next_action"] == "Confirm eligibility documents."
    assert item["note_preview"] == "Private memo should stay preview-only in lists."
    assert item["note"] == "Private memo should stay preview-only in lists."
    assert shortlisted["items"]
    assert {value["notice_id"] for value in shortlisted["items"]} == {notice_id}
    assert filtered["real_api_call_attempted"] is False


def test_daily_review_pack_reflects_review_status_and_exports_safe_note_preview(
    tmp_path: Path,
    monkeypatch,
) -> None:  # noqa: ANN001
    settings = _tmp_settings(tmp_path, g2b_api_service_key="LOCAL_ONLY_SECRET")
    monkeypatch.setattr(routes, "get_settings", lambda: settings)
    client.post(
        "/ops/run-recommendations",
        json={"mode": "fixture", "keyword": "AI", "num_rows": 3, "include_reports": True},
    )
    notice_id = client.get("/ops/opportunity-inbox").json()["items"][0]["notice_id"]
    client.post(
        f"/ops/review-status/{notice_id}",
        json={
            "review_status": "go",
            "owner": "YOnLab",
            "note": "Sensitive local memo with LOCAL_ONLY_SECRET and D:\\Deploy\\path",
            "next_action": "Prepare bid/no-bid decision.",
        },
    )

    pack = client.get("/ops/daily-review-pack").json()
    markdown = client.get("/ops/daily-review-pack/markdown").text
    csv_text = client.get("/ops/daily-review-pack/csv").text

    assert pack["shortlisted_items"]
    assert pack["shortlisted_items"][0]["notice_id"] == notice_id
    assert pack["shortlisted_count"] >= 1
    assert any(action["notice_id"] == notice_id for action in pack["today_actions"])
    assert "Review Status" in markdown
    assert "Prepare bid/no-bid decision." in markdown
    assert "review_status" in csv_text
    assert "next_action" in csv_text
    assert "LOCAL_ONLY_SECRET" not in markdown
    assert "LOCAL_ONLY_SECRET" not in csv_text
    assert "D:\\Deploy" not in markdown
    assert "D:\\Deploy" not in csv_text
    assert "Sensitive local memo" not in markdown
    assert "Sensitive local memo" not in csv_text


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


def _status_path(settings: Settings) -> Path:
    return Path(settings.yonlab_storage_db_path).with_name("review_status.json")
