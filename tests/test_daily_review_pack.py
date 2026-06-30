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
    assert "## Review Board Summary" in markdown
    assert "## Deadline-first Next Actions" in markdown
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


def test_daily_review_pack_includes_review_board_summary_and_next_actions() -> None:
    pack = build_daily_review_pack(_sample_items())

    assert pack["review_board_summary"]["active_count"] == 4
    assert pack["review_board_summary"]["status_counts"]["go"] == 1
    assert pack["review_board_summary"]["status_counts"]["reviewing"] == 1
    assert pack["review_board_summary"]["status_counts"]["shortlisted"] == 1
    assert pack["review_board_summary"]["status_counts"]["hold"] == 1
    assert [item["notice_id"] for item in pack["deadline_first_next_actions"]] == [
        "P1-LOWER-SCORE",
        "P1-HIGHER-SCORE",
        "P2-ITEM",
        "HOLD-ITEM",
    ]
    assert pack["deadline_first_next_actions"][0]["next_action"]


def test_daily_review_pack_includes_decision_memo_summary_and_entries() -> None:
    pack = build_daily_review_pack(_decision_memo_items())

    summary = pack["decision_memo_summary"]
    assert summary["status"] == "success"
    assert summary["memo_count"] >= 1
    assert summary["candidate_count"] >= 1
    assert summary["decision_counts"]["Prepare"] >= 1
    assert summary["deadline_first_notice_ids"][0] == "G2B-SAMPLE-2026-001"
    memo = summary["memos"][0]
    assert memo["notice_id"] == "G2B-SAMPLE-2026-001"
    assert memo["title"] == "서울 AI 기반 행정지원 업무 자동화 시스템 구축"
    assert memo["agency"] == "서울특별시 산하기관"
    assert memo["deadline"] == "2099-07-15"
    assert memo["recommended_decision"] == "Prepare"
    assert memo["yonlab_fit_summary"]
    assert memo["deadline_next_action"]
    assert memo["risk_summary"]
    assert memo["preparation_actions"]
    assert memo["required_documents"]
    assert memo["copy_ready_summary"]
    assert memo["copy_ready_markdown"]
    assert summary["service_key_exposed"] is False
    assert summary["real_api_call_attempted"] is False


def test_daily_review_pack_uses_persisted_manual_decision_in_decision_memo() -> None:
    pack = build_daily_review_pack(
        _decision_memo_items(
            manual_decision="Reject",
            manual_decision_note="Operator overrode the generated recommendation.",
            manual_decision_updated_at="2026-06-30T08:30:00+00:00",
            manual_decision_persisted=True,
        )
    )

    memo = pack["decision_memo_summary"]["memos"][0]

    assert memo["recommended_decision"] == "Reject"
    assert memo["rationale"] == "Operator overrode the generated recommendation."
    assert pack["decision_memo_summary"]["decision_counts"]["Reject"] == 1


def test_daily_review_pack_markdown_shows_persisted_manual_decision_details() -> None:
    pack = build_daily_review_pack(
        _decision_memo_items(
            manual_decision="Hold",
            manual_decision_note="Wait for partner confirmation before bidding.",
            manual_decision_updated_at="2026-06-30T08:30:00+00:00",
            manual_decision_persisted=True,
        )
    )

    markdown = pack["markdown_report"]

    assert "## Decision Memo Summary" in markdown
    assert "## Decision Memo Details" in markdown
    assert "- Hold: 1" in markdown
    assert "/ Hold" in markdown
    assert "rationale: Wait for partner confirmation before bidding." in markdown


def test_daily_review_pack_preserves_generated_decision_without_manual_override() -> None:
    pack = build_daily_review_pack(
        _decision_memo_items(
            manual_decision="",
            manual_decision_note="",
            manual_decision_updated_at="",
            manual_decision_persisted=False,
        )
    )

    memo = pack["decision_memo_summary"]["memos"][0]

    assert memo["recommended_decision"] == "Prepare"
    assert pack["decision_memo_summary"]["decision_counts"]["Prepare"] == 1
    assert memo["rationale"] != ""


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
        "decision_memo_status",
        "decision_memo_decision",
        "decision_memo_rationale",
        "decision_memo_fit_summary",
        "decision_memo_risk_summary",
        "decision_memo_deadline_urgency",
        "decision_memo_next_action",
        "decision_memo_preparation_actions",
        "decision_memo_required_documents",
        "decision_memo_short_summary",
    }
    assert "'=Formula Title" in csv_text
    assert "'+Agency" in csv_text
    assert "D:\\Deploy" not in csv_text
    assert "report_path" not in csv_text
    assert "raw_json_path" not in csv_text
    assert "LOCAL_ONLY_SECRET" not in csv_text
    assert "decision_memo_decision" in csv_text

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
    assert pack["review_board_summary"]["active_count"] == 0
    assert pack["deadline_first_next_actions"] == []
    assert pack["decision_memo_summary"]["status"] == "empty"
    assert pack["decision_memo_summary"]["memos"] == []
    assert "No active review board items yet." in pack["markdown_report"]
    assert "## Decision Memo Summary" in pack["markdown_report"]
    assert "No decision memo candidates available yet." in pack["markdown_report"]
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
    assert payload["decision_memo_summary"]["status"] in {"success", "empty"}
    assert payload["decision_memo_summary"]["service_key_exposed"] is False
    assert payload["decision_memo_summary"]["real_api_call_attempted"] is False
    assert payload["review_board_summary"]["status_counts"]["go"] >= 0
    assert "deadline_first_next_actions" in payload
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
    assert "## Review Board Summary" in markdown_response.text
    assert "## Decision Memo Summary" in markdown_response.text
    assert "## Decision Memo Details" in markdown_response.text
    assert "## Deadline-first Next Actions" in markdown_response.text
    assert "serviceKey" not in markdown_response.text
    assert "D:\\Deploy" not in markdown_response.text

    assert csv_response.status_code == 200
    assert csv_response.headers["content-type"].startswith("text/csv")
    csv_body = csv_response.text.lstrip("\ufeff")
    assert "notice_id,title,agency,budget,deadline,score,review_status" in csv_body
    assert "decision_memo_decision" in csv_body
    assert "serviceKey" not in csv_response.text
    assert "D:\\Deploy" not in csv_response.text


def test_daily_review_pack_api_includes_known_safe_decision_memo_when_fixture_data_exists(
    tmp_path: Path,
    monkeypatch,
) -> None:  # noqa: ANN001
    settings = _tmp_settings(tmp_path)
    monkeypatch.setattr(routes, "get_settings", lambda: settings)

    client.post(
        "/ops/run-recommendations",
        json={"mode": "fixture", "keyword": "AI", "num_rows": 3, "include_reports": True},
    )

    response = client.get("/ops/daily-review-pack")

    assert response.status_code == 200
    payload = response.json()
    memo_ids = [item["notice_id"] for item in payload["decision_memo_summary"]["memos"]]
    assert "G2B-SAMPLE-2026-001" in memo_ids
    target = next(
        item
        for item in payload["decision_memo_summary"]["memos"]
        if item["notice_id"] == "G2B-SAMPLE-2026-001"
    )
    assert target["recommended_decision"] in {"Prepare", "Review", "Hold", "Reject"}
    assert target["copy_ready_summary"]
    assert target["copy_ready_markdown"]
    assert payload["decision_memo_summary"]["real_api_call_attempted"] is False
    assert payload["decision_memo_summary"]["service_key_exposed"] is False


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
            review_status="reviewing",
            next_action="Review P1-HIGHER-SCORE today",
        ),
        _item(
            notice_id="P1-LOWER-SCORE",
            title="AI validation platform",
            priority="P1",
            score=88,
            deadline="2026-06-30",
            risk_level="low",
            run_id="run_daily",
            review_status="go",
            next_action="Review P1-LOWER-SCORE today",
        ),
        _item(
            notice_id="P2-ITEM",
            title="Cloud software service",
            priority="P2",
            score=77,
            deadline="2026-07-03",
            risk_level="medium",
            run_id="run_daily",
            review_status="shortlisted",
            next_action="Review P2-ITEM today",
        ),
        _item(
            notice_id="P3-ITEM",
            title="Document review item",
            priority="P3",
            score=64,
            deadline="2026-07-02",
            risk_level="medium",
            run_id="run_daily",
            review_status="new",
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
            review_status="hold",
            next_action="Review HOLD-ITEM today",
        ),
    ]


def _decision_memo_items(
    *,
    manual_decision: str = "",
    manual_decision_note: str = "",
    manual_decision_updated_at: str = "",
    manual_decision_persisted: bool = False,
) -> list[dict]:
    return [
        _item(
            notice_id="G2B-SAMPLE-2026-001",
            title="서울 AI 기반 행정지원 업무 자동화 시스템 구축",
            agency="서울특별시 산하기관",
            priority="P1",
            score=96,
            deadline="2099-07-15",
            risk_level="low",
            run_id="run_decision_memo",
            review_status="go",
            next_action="제안 일정 확인",
            decision_label="strong_recommend",
            decision_label_ko="적극 추천",
            fit_summary="YOnLab의 AI/SW 및 클라우드 시스템 역량과 직접 부합합니다.",
            why_now="마감 전 제안 준비를 바로 시작할 수 있습니다.",
            bid_strategy="AI Agent와 Device Farm 검증 경험을 중심으로 제안 전략을 구성합니다.",
            go_no_go_ko="Go",
            decision_reasons=[
                "소프트웨어사업자 요구 조건이 와이온랩 핵심 자격과 부합합니다.",
                "AI/SW 시스템 구축 과업이 와이온랩의 핵심 역량과 부합합니다.",
            ],
            risks=["주요 리스크는 낮으며 제안 일정만 확인하면 됩니다."],
            manual_decision=manual_decision,
            manual_decision_note=manual_decision_note,
            manual_decision_updated_at=manual_decision_updated_at,
            manual_decision_persisted=manual_decision_persisted,
        )
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
    review_status: str = "new",
    next_action: str = "",
    decision_label: str = "recommend",
    decision_label_ko: str = "review",
    fit_summary: str = "YOnLab fit summary",
    why_now: str = "Review timing and proposal readiness.",
    bid_strategy: str = "Use the strongest YOnLab capability fit in the proposal.",
    go_no_go_ko: str = "review",
    decision_reasons: list[str] | None = None,
    risks: list[str] | None = None,
    manual_decision: str = "",
    manual_decision_note: str = "",
    manual_decision_updated_at: str = "",
    manual_decision_persisted: bool = False,
) -> dict:
    return {
        "notice_id": notice_id,
        "title": title,
        "agency": agency,
        "budget": 100000000,
        "deadline": deadline,
        "score": score,
        "decision_label": decision_label,
        "decision_label_ko": decision_label_ko,
        "bid_priority": priority,
        "review_status": review_status,
        "review_status_ko": review_status,
        "go_no_go_recommendation": go_no_go,
        "go_no_go_recommendation_ko": go_no_go_ko,
        "risk_level": risk_level,
        "source_run_id": run_id,
        "source_mode": "saved",
        "detail_url": "https://example.test/notice",
        "next_action": next_action,
        "fit_summary": fit_summary,
        "why_now": why_now,
        "bid_strategy": bid_strategy,
        "decision_reasons": decision_reasons
        or [
            f"{notice_id} fit reason one",
            f"{notice_id} fit reason two",
        ],
        "manual_decision": manual_decision,
        "manual_decision_note": manual_decision_note,
        "manual_decision_updated_at": manual_decision_updated_at,
        "manual_decision_persisted": manual_decision_persisted,
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
        "risks": risks or [f"{risk_level} risk summary"],
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
