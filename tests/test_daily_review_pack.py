import csv
import io
import json
from pathlib import Path

from fastapi.testclient import TestClient

import app.api.routes as routes
from app.core.config import Settings
from app.main import app
from app.services.daily_review_pack import (
    build_daily_review_csv,
    build_daily_review_csv_rows,
    build_daily_review_markdown,
    build_daily_review_pack,
    build_document_action_summary,
    build_risk_summary,
    build_today_action_summary,
    group_opportunities_by_priority,
)

client = TestClient(app)
PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_daily_review_pack_groups_priorities_and_sorts_top_items() -> None:
    pack = build_daily_review_pack(_sample_items())

    assert pack["status"] == "success"
    assert pack["total_items"] == 5
    assert pack["p1_count"] == 2
    assert pack["p2_count"] == 1
    assert pack["p3_count"] == 1
    assert pack["hold_count"] == 1
    assert pack["no_go_count"] == 1
    assert [item["notice_id"] for item in pack["top_items"]] == [
        "P1-HIGHER-SCORE",
        "P1-LOWER-SCORE",
        "P2-ITEM",
    ]
    assert [item["notice_id"] for item in pack["review_items"]] == [
        "P1-HIGHER-SCORE",
        "P1-LOWER-SCORE",
        "P2-ITEM",
        "P3-ITEM",
    ]
    assert [item["notice_id"] for item in pack["hold_items"]] == ["HOLD-ITEM"]
    assert [item["notice_id"] for item in pack["no_go_items"]] == ["HOLD-ITEM"]
    assert pack["service_key_exposed"] is False
    assert pack["real_api_call_attempted"] is False


def test_daily_review_helpers_build_actions_documents_and_risk_summary() -> None:
    items = _sample_items()

    groups = group_opportunities_by_priority(items)
    today_actions = build_today_action_summary(items)
    document_actions = build_document_action_summary(items)
    risk_summary = build_risk_summary(items)

    assert len(groups["P1"]) == 2
    assert today_actions[0]["notice_id"] == "P1-HIGHER-SCORE"
    assert "today_action" in today_actions[0]
    assert document_actions
    assert "document_action" in document_actions[0]
    assert risk_summary["total_risk_categories"] >= 1
    assert risk_summary["high_risk_count"] >= 1
    assert risk_summary["by_category"]["deadline_risk"] >= 1


def test_daily_review_markdown_contains_required_sections() -> None:
    pack = build_daily_review_pack(_sample_items())
    markdown = build_daily_review_markdown(pack)

    assert markdown.startswith("# YOnLab Daily Bid Review Pack")
    assert "Generated At" in markdown
    assert "Source Run" in markdown
    assert "## 1. Today Top Opportunities" in markdown
    assert "## 2. Decision Summary By Notice" in markdown
    assert "## 3. Today Actions" in markdown
    assert "## 4. Required Documents" in markdown
    assert "## 5. Risk Summary" in markdown
    assert "## 6. Recommended Response" in markdown
    assert "P1-HIGHER-SCORE" in markdown
    assert "LOCAL_ONLY_SECRET" not in markdown
    assert "D:\\Deploy" not in markdown
    assert "raw_source" not in markdown


def test_daily_review_csv_contains_safe_fields_and_escapes_formulas() -> None:
    pack = build_daily_review_pack(_sample_items())
    rows = build_daily_review_csv_rows(pack)
    csv_text = build_daily_review_csv(pack)

    assert rows
    assert set(rows[0]) == {
        "notice_id",
        "title",
        "agency",
        "budget",
        "deadline",
        "score",
        "decision_label_ko",
        "bid_priority",
        "go_no_go_recommendation_ko",
        "risk_summary",
        "today_action",
        "detail_url",
    }
    assert "'=Formula Title" in csv_text
    assert "'+Agency" in csv_text
    assert "D:\\Deploy" not in csv_text
    assert "report_path" not in csv_text
    assert "raw_json_path" not in csv_text
    assert "LOCAL_ONLY_SECRET" not in csv_text

    parsed = list(csv.DictReader(io.StringIO(csv_text.lstrip("\ufeff"))))
    assert parsed[0]["notice_id"] == "P1-HIGHER-SCORE"


def test_empty_daily_review_pack_has_explicit_empty_state() -> None:
    pack = build_daily_review_pack([])

    assert pack["status"] == "empty"
    assert pack["total_items"] == 0
    assert pack["top_items"] == []
    assert pack["empty_state_message"]
    assert "No opportunity data" in pack["markdown_report"]
    assert pack["service_key_exposed"] is False
    assert pack["real_api_call_attempted"] is False


def test_daily_review_pack_api_is_safe_and_uses_existing_opportunity_data(
    tmp_path: Path,
    monkeypatch,
) -> None:  # noqa: ANN001
    class FailingClient:
        def __init__(self, *args, **kwargs):  # noqa: ANN002, ANN003
            raise AssertionError("Daily Review Pack must not call real G2B API.")

    settings = _tmp_settings(tmp_path, g2b_api_service_key="LOCAL_ONLY_SECRET")
    monkeypatch.setattr(routes, "get_settings", lambda: settings)
    monkeypatch.setattr(routes, "G2BClient", FailingClient)

    response = client.get("/ops/daily-review-pack")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] in {"success", "demo"}
    assert payload["total_items"] >= 1
    assert payload["markdown_report"]
    assert payload["service_key_exposed"] is False
    assert payload["real_api_call_attempted"] is False
    assert "LOCAL_ONLY_SECRET" not in json.dumps(payload, ensure_ascii=False)
    assert "D:\\Deploy" not in json.dumps(payload, ensure_ascii=False)
    assert "raw_source" not in json.dumps(payload, ensure_ascii=False)


def test_daily_review_pack_export_endpoints_return_markdown_and_csv(
    tmp_path: Path,
    monkeypatch,
) -> None:  # noqa: ANN001
    settings = _tmp_settings(tmp_path)
    monkeypatch.setattr(routes, "get_settings", lambda: settings)

    markdown_response = client.get("/ops/daily-review-pack/markdown")
    csv_response = client.get("/ops/daily-review-pack/csv")

    assert markdown_response.status_code == 200
    assert markdown_response.headers["content-type"].startswith("text/markdown")
    assert "# YOnLab Daily Bid Review Pack" in markdown_response.text
    assert "serviceKey" not in markdown_response.text
    assert "D:\\Deploy" not in markdown_response.text

    assert csv_response.status_code == 200
    assert csv_response.headers["content-type"].startswith("text/csv")
    assert "notice_id,title,agency,budget,deadline,score" in csv_response.text.lstrip("\ufeff")
    assert "serviceKey" not in csv_response.text
    assert "D:\\Deploy" not in csv_response.text


def test_dashboard_contains_daily_review_pack_ui_hooks() -> None:
    html = (PROJECT_ROOT / "app" / "ui" / "templates" / "dashboard.html").read_text(
        encoding="utf-8"
    )
    js = (PROJECT_ROOT / "app" / "ui" / "static" / "dashboard.js").read_text(
        encoding="utf-8"
    )

    assert "Daily Review Pack" in html
    assert "daily-review-status" in html
    assert "daily-review-top-items" in html
    assert "daily-review-markdown" in html
    assert "download-daily-review-markdown" in html
    assert "download-daily-review-csv" in html
    assert "loadDailyReviewPack" in js
    assert 'apiJson("/ops/daily-review-pack")' in js
    assert "renderDailyReviewPack" in js
    assert "downloadDailyReviewMarkdown" in js
    assert "downloadDailyReviewCsv" in js
    assert "No opportunity data" in js


def _sample_items() -> list[dict]:
    return [
        _item(
            notice_id="P1-HIGHER-SCORE",
            title="=Formula Title",
            agency="+Agency",
            priority="P1",
            score=92,
            deadline="2026-07-01",
            risk_level="low",
            run_id="run_daily",
        ),
        _item(
            notice_id="P1-LOWER-SCORE",
            title="AI validation platform",
            priority="P1",
            score=88,
            deadline="2026-06-30",
            risk_level="low",
            run_id="run_daily",
        ),
        _item(
            notice_id="P2-ITEM",
            title="Cloud software service",
            priority="P2",
            score=77,
            deadline="2026-07-03",
            risk_level="medium",
            run_id="run_daily",
        ),
        _item(
            notice_id="P3-ITEM",
            title="Document review item",
            priority="P3",
            score=64,
            deadline="2026-07-02",
            risk_level="medium",
            run_id="run_daily",
        ),
        _item(
            notice_id="HOLD-ITEM",
            title="@Hold item",
            priority="Hold",
            score=40,
            deadline="2026-07-04",
            risk_level="high",
            go_no_go="No-Go",
            run_id="run_daily",
        ),
    ]


def _item(
    *,
    notice_id: str,
    title: str,
    priority: str,
    score: int,
    deadline: str,
    risk_level: str,
    run_id: str,
    agency: str = "YOnLab test agency",
    go_no_go: str = "Go",
) -> dict:
    return {
        "notice_id": notice_id,
        "title": title,
        "agency": agency,
        "budget": 100000000,
        "deadline": deadline,
        "score": score,
        "decision_label_ko": "review",
        "bid_priority": priority,
        "go_no_go_recommendation": go_no_go,
        "go_no_go_recommendation_ko": "review",
        "risk_level": risk_level,
        "source_run_id": run_id,
        "source_mode": "saved",
        "detail_url": "https://example.test/notice",
        "report_path": "D:\\Deploy\\secret\\report.md",
        "raw_json_path": "D:\\Deploy\\secret\\raw.json",
        "raw_source": {"serviceKey": "LOCAL_ONLY_SECRET"},
        "action_plan": {
            "today_action": f"Review {notice_id} today",
            "document_action": f"Prepare documents for {notice_id}",
            "business_action": f"Assess proposal strategy for {notice_id}",
            "go_no_go_action": f"Decide go/no-go for {notice_id}",
        },
        "required_documents": [
            {"name": "Software business certificate", "status": "required"},
            {"name": "Small business confirmation", "status": "check"},
        ],
        "risk_categories": [
            {
                "category": "deadline_risk",
                "category_ko": "deadline",
                "level": risk_level,
                "message": f"{risk_level} deadline risk",
            }
        ],
        "risks": [f"{risk_level} risk summary"],
    }


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
