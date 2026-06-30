import json
from pathlib import Path

from fastapi.testclient import TestClient

import app.api.routes as routes
from app.core.config import Settings
from app.main import app
from app.services.decision_memo import build_decision_memo

client = TestClient(app)


def test_ops_decision_memo_returns_safe_payload_for_known_local_notice(
    tmp_path: Path,
    monkeypatch,
) -> None:  # noqa: ANN001
    settings = _tmp_settings(tmp_path, g2b_api_service_key="LOCAL_ONLY_SECRET")
    monkeypatch.setattr(routes, "get_settings", lambda: settings)
    client.post(
        "/ops/run-recommendations",
        json={"mode": "fixture", "keyword": "AI", "num_rows": 3, "include_reports": True},
    )
    inbox = client.get("/ops/opportunity-inbox").json()
    notice_id = inbox["items"][0]["notice_id"]

    response = client.get(f"/ops/decision-memo/{notice_id}")

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) >= {
        "generated_at",
        "source",
        "status",
        "notice_id",
        "notice",
        "review_context",
        "manual_decision",
        "yonlab_fit_summary",
        "risk_summary",
        "deadline_next_action",
        "recommended_decision",
        "preparation_actions",
        "required_documents",
        "export_blocks",
        "safety",
        "service_key_exposed",
    }
    assert payload["status"] == "success"
    assert payload["notice_id"] == notice_id
    assert payload["source"] == inbox["items"][0]["source_type"]
    assert set(payload["notice"]) >= {"title", "agency", "budget", "deadline", "source_url"}
    assert payload["notice"]["title"]
    assert set(payload["review_context"]) >= {
        "review_status",
        "deadline_status",
        "risk_level",
        "match_score",
    }
    assert payload["manual_decision"] == {
        "decision": "",
        "note": "",
        "updated_at": "",
        "persisted": False,
    }
    assert set(payload["yonlab_fit_summary"]) >= {
        "score",
        "grade",
        "fit_reasons",
        "concern_reasons",
    }
    assert payload["yonlab_fit_summary"]["fit_reasons"]
    assert set(payload["risk_summary"]) >= {
        "eligibility_risks",
        "document_risks",
        "schedule_risks",
        "commercial_risks",
    }
    assert set(payload["deadline_next_action"]) >= {
        "deadline",
        "days_remaining",
        "urgency",
        "next_action",
    }
    assert payload["recommended_decision"]["value"] in {
        "Prepare",
        "Review",
        "Hold",
        "Reject",
    }
    assert payload["recommended_decision"]["rationale"]
    assert payload["preparation_actions"]
    assert payload["required_documents"]
    assert payload["export_blocks"]["markdown"]
    assert payload["export_blocks"]["short_summary"]
    assert payload["safety"] == {
        "real_api_call_attempted": False,
        "source_data_mode": inbox["items"][0]["source_type"],
    }
    assert payload["service_key_exposed"] is False
    assert "LOCAL_ONLY_SECRET" not in json.dumps(payload, ensure_ascii=False)
    assert "D:\\Deploy" not in json.dumps(payload, ensure_ascii=False)


def test_ops_decision_memo_returns_safe_not_found_payload_for_unknown_notice(
    tmp_path: Path,
    monkeypatch,
) -> None:  # noqa: ANN001
    settings = _tmp_settings(tmp_path)
    monkeypatch.setattr(routes, "get_settings", lambda: settings)

    response = client.get("/ops/decision-memo/UNKNOWN-NOTICE-ID")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "not_found"
    assert payload["source"] == "empty"
    assert payload["notice_id"] == "UNKNOWN-NOTICE-ID"
    assert payload["notice"]["title"] == ""
    assert payload["manual_decision"] == {
        "decision": "",
        "note": "",
        "updated_at": "",
        "persisted": False,
    }
    assert payload["yonlab_fit_summary"]["fit_reasons"] == []
    assert payload["risk_summary"]["eligibility_risks"] == []
    assert payload["deadline_next_action"]["urgency"] == "unknown"
    assert payload["recommended_decision"]["value"] == "Hold"
    assert payload["preparation_actions"] == []
    assert payload["required_documents"] == []
    assert payload["export_blocks"]["short_summary"]
    assert payload["safety"]["real_api_call_attempted"] is False
    assert payload["safety"]["source_data_mode"] == "empty"
    assert payload["service_key_exposed"] is False


def test_build_decision_memo_aligns_not_found_payload_with_persisted_manual_override() -> None:
    payload = build_decision_memo(
        None,
        notice_id="UNKNOWN-NOTICE-ID",
        manual_decision={
            "decision": "Reject",
            "note": "Saved operator override for this missing notice.",
            "updated_at": "2026-06-30T10:00:00+00:00",
            "persisted": True,
        },
    )

    assert payload["status"] == "not_found"
    assert payload["source"] == "empty"
    assert payload["manual_decision"] == {
        "decision": "Reject",
        "note": "Saved operator override for this missing notice.",
        "updated_at": "2026-06-30T10:00:00+00:00",
        "persisted": True,
    }
    assert payload["recommended_decision"] == {
        "value": "Reject",
        "rationale": "Saved operator override for this missing notice.",
    }
    assert "- Decision: Reject" in payload["export_blocks"]["markdown"]
    assert payload["export_blocks"]["short_summary"].startswith("Reject - ")


def test_ops_decision_memo_never_constructs_real_g2b_client(
    tmp_path: Path,
    monkeypatch,
) -> None:  # noqa: ANN001
    class FailingClient:
        def __init__(self, *args, **kwargs):  # noqa: ANN002, ANN003
            raise AssertionError("Decision memo endpoint must not call real G2B API.")

    settings = _tmp_settings(
        tmp_path,
        g2b_enable_real_api=True,
        g2b_api_service_key="LOCAL_ONLY_SECRET",
    )
    monkeypatch.setattr(routes, "get_settings", lambda: settings)
    monkeypatch.setattr(routes, "G2BClient", FailingClient)

    notice_id = client.get("/ops/opportunity-inbox").json()["items"][0]["notice_id"]
    response = client.get(f"/ops/decision-memo/{notice_id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] in {"success", "demo"}
    assert payload["safety"]["real_api_call_attempted"] is False
    assert payload["service_key_exposed"] is False
    assert "LOCAL_ONLY_SECRET" not in json.dumps(payload, ensure_ascii=False)


def test_manual_decision_api_accepts_each_valid_value_for_known_notice(
    tmp_path: Path,
    monkeypatch,
) -> None:  # noqa: ANN001
    class FailingClient:
        def __init__(self, *args, **kwargs):  # noqa: ANN002, ANN003
            raise AssertionError("Manual decision save must not call real G2B API.")

    settings = _tmp_settings(tmp_path, g2b_api_service_key="LOCAL_ONLY_SECRET")
    monkeypatch.setattr(routes, "get_settings", lambda: settings)
    monkeypatch.setattr(routes, "G2BClient", FailingClient)
    notice_id = _known_notice_id()

    for decision in ("Prepare", "Review", "Hold", "Reject"):
        response = client.post(
            f"/ops/manual-decision/{notice_id}",
            json={"decision": decision, "note": f"{decision} note"},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "success"
        assert payload["notice_id"] == notice_id
        assert payload["manual_decision"] == {
            "decision": decision,
            "note": f"{decision} note",
            "persisted": True,
            "updated_at": payload["manual_decision"]["updated_at"],
        }
        assert payload["manual_decision"]["updated_at"]
        assert payload["service_key_exposed"] is False
        assert payload["real_api_call_attempted"] is False
        assert "LOCAL_ONLY_SECRET" not in json.dumps(payload, ensure_ascii=False)


def test_manual_decision_api_rejects_invalid_decision_with_422(
    tmp_path: Path,
    monkeypatch,
) -> None:  # noqa: ANN001
    settings = _tmp_settings(tmp_path)
    monkeypatch.setattr(routes, "get_settings", lambda: settings)
    notice_id = _known_notice_id()

    response = client.post(
        f"/ops/manual-decision/{notice_id}",
        json={"decision": "prepare", "note": "invalid lowercase alias"},
    )

    assert response.status_code == 422


def test_manual_decision_api_returns_safe_not_found_for_unknown_notice(
    tmp_path: Path,
    monkeypatch,
) -> None:  # noqa: ANN001
    settings = _tmp_settings(tmp_path)
    status_path = _status_path(settings)
    monkeypatch.setattr(routes, "get_settings", lambda: settings)

    response = client.post(
        "/ops/manual-decision/UNKNOWN-NOTICE-ID",
        json={"decision": "Hold", "note": "Wait for more evidence"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "not_found"
    assert payload["notice_id"] == "UNKNOWN-NOTICE-ID"
    assert payload["service_key_exposed"] is False
    assert payload["real_api_call_attempted"] is False
    assert not status_path.exists()


def test_manual_decision_save_then_decision_memo_read_reflects_override(
    tmp_path: Path,
    monkeypatch,
) -> None:  # noqa: ANN001
    settings = _tmp_settings(tmp_path)
    monkeypatch.setattr(routes, "get_settings", lambda: settings)
    notice_id = _known_notice_id()

    save_response = client.post(
        f"/ops/manual-decision/{notice_id}",
        json={
            "decision": "Hold",
            "note": "Wait for team capacity confirmation.",
        },
    )
    assert save_response.status_code == 200

    response = client.get(f"/ops/decision-memo/{notice_id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "success"
    assert payload["notice_id"] == notice_id
    assert payload["manual_decision"] == {
        "decision": "Hold",
        "note": "Wait for team capacity confirmation.",
        "updated_at": payload["manual_decision"]["updated_at"],
        "persisted": True,
    }
    assert payload["manual_decision"]["updated_at"]
    assert payload["recommended_decision"]["value"] == "Hold"
    assert payload["recommended_decision"]["rationale"] == "Wait for team capacity confirmation."
    assert "- Decision: Hold" in payload["export_blocks"]["markdown"]
    assert "Decision: Hold" in payload["export_blocks"]["markdown"]
    assert payload["export_blocks"]["short_summary"].startswith("Hold - ")
    assert payload["safety"]["real_api_call_attempted"] is False
    assert payload["service_key_exposed"] is False


def test_decision_memo_exposes_manual_decision_block(
    tmp_path: Path,
    monkeypatch,
) -> None:  # noqa: ANN001
    settings = _tmp_settings(tmp_path)
    monkeypatch.setattr(routes, "get_settings", lambda: settings)
    notice_id = _known_notice_id()

    response = client.get(f"/ops/decision-memo/{notice_id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["manual_decision"] == {
        "decision": "",
        "note": "",
        "updated_at": "",
        "persisted": False,
    }


def test_decision_memo_recommended_decision_uses_persisted_manual_value(
    tmp_path: Path,
    monkeypatch,
) -> None:  # noqa: ANN001
    settings = _tmp_settings(tmp_path)
    monkeypatch.setattr(routes, "get_settings", lambda: settings)
    notice_id = _known_notice_id()

    save_response = client.post(
        f"/ops/manual-decision/{notice_id}",
        json={
            "decision": "Reject",
            "note": "Legal review blocked this bid.",
        },
    )
    assert save_response.status_code == 200

    response = client.get(f"/ops/decision-memo/{notice_id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["manual_decision"] == {
        "decision": "Reject",
        "note": "Legal review blocked this bid.",
        "updated_at": payload["manual_decision"]["updated_at"],
        "persisted": True,
    }
    assert payload["manual_decision"]["updated_at"]
    assert payload["recommended_decision"] == {
        "value": "Reject",
        "rationale": "Legal review blocked this bid.",
    }
    assert "- Decision: Reject" in payload["export_blocks"]["markdown"]
    assert payload["export_blocks"]["short_summary"].startswith("Reject - ")


def test_decision_memo_uses_generated_rationale_when_persisted_manual_note_is_empty(
    tmp_path: Path,
    monkeypatch,
) -> None:  # noqa: ANN001
    settings = _tmp_settings(tmp_path)
    monkeypatch.setattr(routes, "get_settings", lambda: settings)
    notice_id = _known_notice_id()

    baseline_response = client.get(f"/ops/decision-memo/{notice_id}")
    assert baseline_response.status_code == 200
    baseline_payload = baseline_response.json()
    generated_rationale = baseline_payload["recommended_decision"]["rationale"]
    assert generated_rationale

    save_response = client.post(
        f"/ops/manual-decision/{notice_id}",
        json={
            "decision": "Hold",
            "note": "",
        },
    )
    assert save_response.status_code == 200

    response = client.get(f"/ops/decision-memo/{notice_id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["manual_decision"] == {
        "decision": "Hold",
        "note": "",
        "updated_at": payload["manual_decision"]["updated_at"],
        "persisted": True,
    }
    assert payload["manual_decision"]["updated_at"]
    assert payload["recommended_decision"]["value"] == "Hold"
    assert payload["recommended_decision"]["rationale"] == generated_rationale


def test_decision_memo_uses_generated_default_when_manual_decision_missing(
    tmp_path: Path,
    monkeypatch,
) -> None:  # noqa: ANN001
    settings = _tmp_settings(tmp_path)
    monkeypatch.setattr(routes, "get_settings", lambda: settings)
    notice_id = _known_notice_id()

    response = client.get(f"/ops/decision-memo/{notice_id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["manual_decision"]["persisted"] is False
    assert payload["recommended_decision"]["value"] in {
        "Prepare",
        "Review",
        "Hold",
        "Reject",
    }
    assert payload["recommended_decision"]["rationale"]
    assert payload["recommended_decision"]["rationale"] != ""
    assert payload["recommended_decision"]["rationale"] != (
        "Using the saved local manual decision override."
    )


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


def _known_notice_id() -> str:
    run = client.post(
        "/ops/run-recommendations",
        json={"mode": "fixture", "keyword": "AI", "num_rows": 3, "include_reports": True},
    )
    assert run.status_code == 200
    inbox = client.get("/ops/opportunity-inbox").json()
    return str(inbox["items"][0]["notice_id"])
