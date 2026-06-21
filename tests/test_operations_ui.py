import json
from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient

import app.api.routes as routes
from app.core.config import Settings
from app.integrations.g2b.fixtures import load_sample_g2b_notices
from app.main import app
from app.storage.models import StoredReport
from app.storage.repository import OperationsRepository

client = TestClient(app)
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DUPLICATED_KOREAN_FRAGMENTS = (
    "\uc11c\uc11c\uc6b8\uc6b8",
    "\ubd80\ubd80\uc0b0\uc0b0",
    "\uc9c0\uc9c0\uc5ed\uc5ed",
    "\uc2dc\uc2dc\uc2a4\uc2a4\ud15c\ud15c",
    "\ubd80\ubd80\ud569\ud569\ud569\ub2c8\ub2c8\ub2e4\ub2e4",
)


def test_ui_dashboard_returns_html_without_service_key(monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.setattr(routes, "get_settings", lambda: Settings(g2b_api_service_key="SECRET"))

    response = client.get("/ui")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "YOnLab G2B Agent" in response.text
    assert "Run recommendation" in response.text
    assert "Recommendation Quality Summary" in response.text
    assert "Total Reports" in response.text
    assert "Real Runs" in response.text
    assert "Latest Error" in response.text
    assert "Real mode uses live G2B API quota. Use only when necessary." in response.text
    assert "SECRET" not in response.text


def test_root_redirects_to_ui() -> None:
    response = client.get("/", follow_redirects=False)

    assert response.status_code in {302, 307}
    assert response.headers["location"] == "/ui"


def test_ui_static_assets_are_available() -> None:
    css_response = client.get("/ui/static/dashboard.css")
    js_response = client.get("/ui/static/dashboard.js")

    assert css_response.status_code == 200
    assert ".topbar" in css_response.text
    assert js_response.status_code == 200
    assert "runRecommendation" in js_response.text


def test_report_content_endpoint_returns_saved_markdown(
    tmp_path: Path,
    monkeypatch,
) -> None:  # noqa: ANN001
    settings = _tmp_settings(tmp_path)
    monkeypatch.setattr(routes, "get_settings", lambda: settings)

    run_response = client.post(
        "/ops/run-recommendations",
        json={"mode": "fixture", "keyword": "AI", "num_rows": 2, "include_reports": True},
    )
    run_id = run_response.json()["run_id"]
    reports = client.get(f"/ops/reports/{run_id}").json()["reports"]

    assert reports
    report_response = client.get(f"/ops/report-content/{run_id}/{reports[0]['notice_id']}")

    assert report_response.status_code == 200
    payload = report_response.json()
    assert payload["run_id"] == run_id
    assert payload["notice_id"] == reports[0]["notice_id"]
    assert "와이온랩 맞춤 추천 공고" in payload["markdown"]
    assert "serviceKey" not in str(payload)


def test_report_content_endpoint_blocks_path_traversal(
    tmp_path: Path,
    monkeypatch,
) -> None:  # noqa: ANN001
    settings = _tmp_settings(tmp_path)
    monkeypatch.setattr(routes, "get_settings", lambda: settings)
    outside_file = tmp_path / "outside.md"
    outside_file.write_text("outside", encoding="utf-8")
    repository = OperationsRepository(settings.yonlab_storage_db_path)
    repository.save_report(
        StoredReport(
            run_id="run_unsafe",
            notice_id="NOTICE-UNSAFE",
            title="Unsafe",
            report_path=str(outside_file),
            created_at=datetime.now(UTC).isoformat(),
        )
    )

    response = client.get("/ops/report-content/run_unsafe/NOTICE-UNSAFE")

    assert response.status_code == 404


def test_ops_recommendations_can_filter_by_run_id(
    tmp_path: Path,
    monkeypatch,
) -> None:  # noqa: ANN001
    settings = _tmp_settings(tmp_path)
    monkeypatch.setattr(routes, "get_settings", lambda: settings)

    first = client.post(
        "/ops/run-recommendations",
        json={"mode": "fixture", "keyword": "AI", "num_rows": 1, "include_reports": True},
    ).json()
    second = client.post(
        "/ops/run-recommendations",
        json={"mode": "fixture", "keyword": "AI", "num_rows": 2, "include_reports": True},
    ).json()

    first_payload = client.get(
        "/ops/recommendations",
        params={"run_id": first["run_id"], "limit": 10},
    ).json()
    second_payload = client.get(
        "/ops/recommendations",
        params={"run_id": second["run_id"], "limit": 10},
    ).json()

    assert first_payload["recommendations"]
    assert second_payload["recommendations"]
    assert {item["run_id"] for item in first_payload["recommendations"]} == {first["run_id"]}
    assert {item["run_id"] for item in second_payload["recommendations"]} == {second["run_id"]}


def test_ui_smoke_scripts_exist_and_validate_local_references_them() -> None:
    assert (PROJECT_ROOT / "scripts" / "smoke_ui_health.ps1").is_file()
    assert (PROJECT_ROOT / "scripts" / "smoke_ops_ui_flow.ps1").is_file()
    assert (PROJECT_ROOT / "scripts" / "reset_local_ops_data.ps1").is_file()

    validate_local = (PROJECT_ROOT / "scripts" / "validate_local.ps1").read_text(
        encoding="utf-8"
    )
    assert "smoke_ui_health.ps1" in validate_local
    assert "smoke_ops_ui_flow.ps1" in validate_local
    assert "smoke_ops_quality_summary.ps1" in validate_local
    assert "smoke_ops_report_index.ps1" in validate_local


def test_ui_javascript_blocks_unconfirmed_real_mode_and_sets_row_defaults() -> None:
    js_text = (PROJECT_ROOT / "app" / "ui" / "static" / "dashboard.js").read_text(
        encoding="utf-8"
    )

    assert 'payload.mode === "real" && !payload.confirm_real_api_call' in js_text
    assert "Real mode uses live G2B API quota" in js_text
    assert 'rowsInput.value = "3"' in js_text
    assert 'rowsInput.value = "5"' in js_text
    assert 'apiJson("/ops/quality-summary")' in js_text
    assert "quality-summary-status" in js_text
    assert "quality-real-runs" in js_text
    assert "quality-latest-error" in js_text


def test_duplicated_korean_fragments_absent_from_fixture_and_fresh_ops_output(
    tmp_path: Path,
    monkeypatch,
) -> None:  # noqa: ANN001
    settings = _tmp_settings(tmp_path)
    monkeypatch.setattr(routes, "get_settings", lambda: settings)

    fixture_text = json.dumps(load_sample_g2b_notices(), ensure_ascii=False)
    run = client.post(
        "/ops/run-recommendations",
        json={"mode": "fixture", "keyword": "AI", "num_rows": 3, "include_reports": True},
    ).json()
    detail = client.get(f"/ops/runs/{run['run_id']}").json()
    recommendations = client.get(
        "/ops/recommendations",
        params={"run_id": run["run_id"], "limit": 10},
    ).json()
    output_text = json.dumps(
        {"fixture": fixture_text, "detail": detail, "recommendations": recommendations},
        ensure_ascii=False,
    )

    for fragment in DUPLICATED_KOREAN_FRAGMENTS:
        assert fragment not in output_text


def _tmp_settings(tmp_path: Path) -> Settings:
    return Settings(
        yonlab_storage_db_path=str(tmp_path / "ops" / "yonlab.sqlite3"),
        yonlab_report_dir=str(tmp_path / "reports"),
        yonlab_default_run_mode="fixture",
        yonlab_default_keyword="AI",
        yonlab_default_num_rows=3,
    )
