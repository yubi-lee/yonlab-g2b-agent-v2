from pathlib import Path

from fastapi.testclient import TestClient

import app.api.routes as routes
import app.services.opportunity_inbox as opportunity_inbox
from app.core.config import Settings
from app.main import app

client = TestClient(app)
PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_opportunity_inbox_returns_demo_items_without_creating_database(
    tmp_path: Path,
    monkeypatch,
) -> None:  # noqa: ANN001
    settings = _tmp_settings(tmp_path, g2b_api_service_key="LOCAL_ONLY_SECRET")
    db_path = Path(settings.yonlab_storage_db_path)
    monkeypatch.setattr(routes, "get_settings", lambda: settings)

    response = client.get("/ops/opportunity-inbox")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "demo"
    assert payload["source_mode"] == "demo"
    assert payload["service_key_exposed"] is False
    assert payload["real_api_call_attempted"] is False
    assert payload["items"]
    assert payload["items"][0]["source_type"] == "demo"
    assert payload["empty_state_message"]
    assert not db_path.exists()
    assert "LOCAL_ONLY_SECRET" not in str(payload)
    assert "serviceKey" not in str(payload)


def test_opportunity_inbox_uses_saved_fixture_recommendations_and_filters(
    tmp_path: Path,
    monkeypatch,
) -> None:  # noqa: ANN001
    settings = _tmp_settings(tmp_path)
    monkeypatch.setattr(routes, "get_settings", lambda: settings)
    run = client.post(
        "/ops/run-recommendations",
        json={"mode": "fixture", "keyword": "AI", "num_rows": 3, "include_reports": True},
    ).json()

    payload = client.get(
        "/ops/opportunity-inbox",
        params={"source_type": "fixture", "sort": "score_desc"},
    ).json()

    assert payload["status"] == "success"
    assert payload["source_mode"] == "saved"
    assert payload["total_items"] >= 1
    assert payload["items"]
    assert {item["source_run_id"] for item in payload["items"]} == {run["run_id"]}
    assert {item["source_type"] for item in payload["items"]} == {"fixture"}
    scores = [item["score"] for item in payload["items"]]
    assert scores == sorted(scores, reverse=True)
    first = payload["items"][0]
    assert first["decision_label"]
    assert first["decision_label_ko"]
    assert first["bid_priority"]
    assert first["decision_reasons"]
    assert first["action_plan"]
    assert first["risk_categories"]
    assert first["go_no_go_recommendation"]
    assert first["go_no_go_recommendation_ko"]
    assert first["fit_summary"]
    assert first["why_now"]
    assert first["bid_strategy"]
    assert first["required_documents"]
    assert first["recommended_action"]
    assert first["report_url"].startswith("/ops/opportunity-report/")


def test_opportunity_detail_and_report_are_copy_ready_markdown(
    tmp_path: Path,
    monkeypatch,
) -> None:  # noqa: ANN001
    settings = _tmp_settings(tmp_path)
    monkeypatch.setattr(routes, "get_settings", lambda: settings)
    client.post(
        "/ops/run-recommendations",
        json={"mode": "fixture", "keyword": "AI", "num_rows": 2, "include_reports": True},
    )
    inbox = client.get("/ops/opportunity-inbox").json()
    notice_id = inbox["items"][0]["notice_id"]

    detail = client.get(f"/ops/opportunity-inbox/{notice_id}").json()
    report = client.get(f"/ops/opportunity-report/{notice_id}").json()

    assert detail["notice_id"] == notice_id
    assert detail["service_key_exposed"] is False
    assert report["notice_id"] == notice_id
    assert report["content_type"] == "text/markdown; charset=utf-8"
    assert "## YOnLab 맞춤 추천 공고:" in report["markdown"]
    assert "- 매칭 점수:" in report["markdown"]
    assert "- Priority:" in report["markdown"]
    assert "- Go/No-Go:" in report["markdown"]
    assert "- 추천 사유:" in report["markdown"]
    assert "- 오늘 액션:" in report["markdown"]
    assert "- 리스크 카테고리:" in report["markdown"]
    assert "- 권장 대응:" in report["markdown"]
    assert "serviceKey" not in report["markdown"]


def test_opportunity_endpoints_do_not_construct_real_client(
    tmp_path: Path,
    monkeypatch,
) -> None:  # noqa: ANN001
    class FailingClient:
        def __init__(self, *args, **kwargs):  # noqa: ANN002, ANN003
            raise AssertionError("Opportunity inbox must not call real G2B API.")

    settings = _tmp_settings(
        tmp_path,
        g2b_enable_real_api=True,
        g2b_api_service_key="LOCAL_ONLY_SECRET",
    )
    monkeypatch.setattr(routes, "get_settings", lambda: settings)
    monkeypatch.setattr(routes, "G2BClient", FailingClient)

    response = client.get("/ops/opportunity-inbox")

    assert response.status_code == 200
    payload = response.json()
    assert payload["real_api_call_attempted"] is False
    assert "LOCAL_ONLY_SECRET" not in str(payload)


def test_opportunity_report_builder_contains_commercial_decision_fields() -> None:
    item = opportunity_inbox.build_demo_opportunity_items(limit=1)[0]

    markdown = opportunity_inbox.build_yonlab_opportunity_report(item)

    assert item["fit_summary"]
    assert item["why_now"]
    assert item["bid_strategy"]
    assert item["required_documents"]
    assert item["risks"]
    assert item["recommended_action"]
    assert "- Action Plan:" in markdown
    assert "- Priority:" in markdown
    assert "- Go/No-Go:" in markdown
    assert "제출 필요 서류" in markdown
    assert "리스크 카테고리" in markdown


def test_dashboard_contains_opportunity_inbox_ui_hooks() -> None:
    html = (PROJECT_ROOT / "app" / "ui" / "templates" / "dashboard.html").read_text(
        encoding="utf-8"
    )
    js = (PROJECT_ROOT / "app" / "ui" / "static" / "dashboard.js").read_text(
        encoding="utf-8"
    )

    assert "Opportunity Inbox" in html
    assert "opportunity-body" in html
    assert "opportunity-detail" in html
    assert "opportunity-markdown" in html
    assert "download-opportunity-markdown" in html
    assert "opportunity-review-status" in html
    assert "opportunity-review-owner" in html
    assert "opportunity-review-next-action" in html
    assert "opportunity-review-note" in html
    assert "save-opportunity-review-status" in html
    assert "clear-opportunity-review-status" in html
    assert "opportunity-review-filter" in html
    assert "opportunity-shortlisted-only" in html
    assert "loadOpportunityInbox" in js
    assert 'apiJson("/ops/opportunity-inbox' in js
    assert "/ops/review-status" in js
    assert "renderOpportunityInbox" in js
    assert "saveOpportunityReviewStatus" in js
    assert "clearOpportunityReviewStatus" in js
    assert "downloadOpportunityMarkdown" in js
    assert "No opportunity data yet" in js
    assert "review_status_ko" in js
    assert "next_action" in js
    assert "decision_label_ko" in js
    assert "bid_priority" in js
    assert "go_no_go_recommendation_ko" in js
    assert "renderOpportunityDetail" in js


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
