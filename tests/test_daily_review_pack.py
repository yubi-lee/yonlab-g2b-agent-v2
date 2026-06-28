import csv
import io
import json
from pathlib import Path

from fastapi.testclient import TestClient

import app.api.routes as routes
from app.core.config import Settings
from app.main import app
from app.services.daily_review_pack import (
    PRIORITY_LEGEND,
    build_daily_review_csv,
    build_daily_review_csv_rows,
    build_daily_review_markdown,
    build_daily_review_pack,
    build_document_action_summary,
    build_risk_summary,
    build_today_action_summary,
    group_opportunities_by_priority,
)
from app.services.safe_daily_status import build_safe_daily_status

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

    assert markdown.startswith("# 오늘의 입찰 검토 패키지")
    assert "Generated At" in markdown
    assert "Source Run" in markdown
    assert "## 0. 한눈에 보는 요약" in markdown
    assert "## 1. 오늘의 우선 검토 공고" in markdown
    assert "## 2. 공고별 판단 요약" in markdown
    assert "## 3. 오늘 할 일" in markdown
    assert "## 4. 서류 준비" in markdown
    assert "## 5. 리스크 요약" in markdown
    assert "## 6. 권장 대응" in markdown
    assert "P1-HIGHER-SCORE" in markdown
    assert "LOCAL_ONLY_SECRET" not in markdown
    assert "D:\\Deploy" not in markdown
    assert "raw_source" not in markdown


def test_daily_review_pack_includes_executive_summary_and_priority_legend() -> None:
    pack = build_daily_review_pack(_sample_items())

    assert pack["executive_summary"]["total_items"] == 5
    assert pack["executive_summary"]["today_priority_count"] == 3
    assert pack["executive_summary"]["p1_count"] == 2
    assert pack["executive_summary"]["p2_count"] == 1
    assert pack["executive_summary"]["hold_count"] == 1
    assert len(pack["executive_summary"]["lines"]) >= 3
    assert pack["priority_legend"] == PRIORITY_LEGEND
    assert pack["priority_legend"]["P1"].startswith("same-day")
    assert "saved" in pack["source_mode_message"]


def test_daily_review_pack_groups_required_documents() -> None:
    pack = build_daily_review_pack(_sample_items())
    item = pack["review_items"][0]
    action = pack["document_actions"][0]

    assert "required_documents_grouped" in item
    assert "required_documents_grouped" in action
    assert "기본 회사 서류" in action["required_documents_grouped"]
    assert "SW/직접생산 확인" in action["required_documents_grouped"]
    assert action["required_documents_grouped"]["기본 회사 서류"]


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
        "review_status",
        "review_status_ko",
        "owner",
        "decision_label_ko",
        "bid_priority",
        "go_no_go_recommendation_ko",
        "risk_summary",
        "next_action",
        "note_preview",
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
    assert pack["empty_state_next_actions"]
    assert "controlled real run" in " ".join(pack["empty_state_next_actions"])
    assert "No opportunity data" in pack["markdown_report"]
    assert "saved notices" in pack["source_mode_message"]
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
    assert payload["executive_summary"]
    assert payload["priority_legend"]["P1"].startswith("same-day")
    assert payload["source_mode_message"]
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
    assert "# 오늘의 입찰 검토 패키지" in markdown_response.text
    assert "## 0. 한눈에 보는 요약" in markdown_response.text
    assert "serviceKey" not in markdown_response.text
    assert "D:\\Deploy" not in markdown_response.text

    assert csv_response.status_code == 200
    assert csv_response.headers["content-type"].startswith("text/csv")
    csv_body = csv_response.text.lstrip("\ufeff")
    assert "notice_id,title,agency,budget,deadline,score,review_status" in csv_body
    assert "serviceKey" not in csv_response.text
    assert "D:\\Deploy" not in csv_response.text


def test_dashboard_contains_daily_review_pack_ui_hooks() -> None:
    html = (PROJECT_ROOT / "app" / "ui" / "templates" / "dashboard.html").read_text(
        encoding="utf-8"
    )
    js = (PROJECT_ROOT / "app" / "ui" / "static" / "dashboard.js").read_text(
        encoding="utf-8"
    )

    assert "오늘의 입찰 검토 패키지" in html
    assert "source-mode-banner" in html
    assert "priority-legend" in html
    assert "safe-daily-status" in html
    assert "daily-review-executive-summary" in html
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
    assert 'apiJson("/ops/safe-daily-status")' in js
    assert "renderSourceModeBanner" in js
    assert "renderSafeDailyStatus" in js
    assert "renderPriorityLegend" in js
    assert "No opportunity data" in js


def test_safe_daily_status_api_returns_safe_metadata_only(tmp_path: Path, monkeypatch) -> None:  # noqa: ANN001
    settings = _tmp_settings(tmp_path, g2b_api_service_key="LOCAL_ONLY_SECRET")
    monkeypatch.setattr(routes, "get_settings", lambda: settings)

    response = client.get("/ops/safe-daily-status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] in {"empty", "success", "unknown"}
    assert payload["real_api_call_attempted"] is False
    assert payload["service_key_exposed"] is False
    assert "latest_log_filename" in payload
    assert "scheduler_target_expected" in payload
    assert Path(payload["active_deployment_path"]).name != "data"
    assert Path(payload["active_deployment_path"]).name.startswith("yonlab-g2b-agent-v2")
    assert "LOCAL_ONLY_SECRET" not in json.dumps(payload, ensure_ascii=False)


def test_safe_daily_status_uses_explicit_dev_or_deploy_root(tmp_path: Path) -> None:
    dev_root = tmp_path / "yonlab-g2b-agent-v2"
    deploy_root = tmp_path / "yonlab-g2b-agent-v2-rc12"
    dev_root.mkdir()
    deploy_root.mkdir()

    dev_payload = build_safe_daily_status(deploy_path=dev_root)
    deploy_payload = build_safe_daily_status(deploy_path=deploy_root)

    assert Path(dev_payload["active_deployment_path"]).name == "yonlab-g2b-agent-v2"
    assert Path(deploy_payload["active_deployment_path"]).name == "yonlab-g2b-agent-v2-rc12"
    assert Path(dev_payload["active_deployment_path"]).name != "data"
    assert Path(deploy_payload["active_deployment_path"]).name != "data"
    assert dev_payload["real_api_call_attempted"] is False
    assert deploy_payload["real_api_call_attempted"] is False
    assert dev_payload["service_key_exposed"] is False
    assert deploy_payload["service_key_exposed"] is False


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
