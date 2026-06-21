import sqlite3
from pathlib import Path

from fastapi.testclient import TestClient

import app.api.routes as routes
import app.services.operations_runner as operations_runner
from app.core.config import Settings
from app.main import app
from app.services.operations_runner import run_recommendation_job
from app.storage.database import initialize_database
from app.storage.repository import OperationsRepository

client = TestClient(app)


def test_operations_database_initializes_expected_tables(tmp_path: Path) -> None:
    db_path = tmp_path / "ops.sqlite3"

    initialize_database(db_path)

    with sqlite3.connect(db_path) as connection:
        table_names = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
    assert {"search_runs", "recommendations", "reports"}.issubset(table_names)


def test_fixture_operation_run_persists_records_and_reports(tmp_path: Path) -> None:
    settings = _tmp_settings(tmp_path, g2b_api_service_key="LOCAL_ONLY_SECRET")

    summary = run_recommendation_job(
        settings=settings,
        mode="fixture",
        keyword="AI",
        num_rows=3,
        include_reports=True,
    )

    repository = OperationsRepository(settings.yonlab_storage_db_path)
    run = repository.get_run(summary.run_id)
    recommendations = repository.list_recommendations(limit=10, run_id=summary.run_id)
    reports = repository.list_reports(summary.run_id)

    assert summary.status == "success"
    assert summary.source_count >= 1
    assert summary.recommendation_count >= 1
    assert summary.report_count == len(reports)
    assert run is not None
    assert run["mode"] == "fixture"
    assert run["service_key_exposed"] is False
    assert recommendations
    assert recommendations[0]["top_reasons"]
    assert Path(recommendations[0]["report_path"]).is_file()
    assert Path(recommendations[0]["raw_json_path"]).is_file()
    assert reports

    persisted_text = _read_generated_text(tmp_path)
    assert "LOCAL_ONLY_SECRET" not in persisted_text
    assert "serviceKey" not in persisted_text


def test_real_mode_operations_are_guarded_without_http_call(
    tmp_path: Path,
    monkeypatch,
) -> None:  # noqa: ANN001
    class FailingG2BClient:
        def __init__(self, settings):  # noqa: ANN001
            raise AssertionError("Real G2B client must not be constructed by default.")

    monkeypatch.setattr(operations_runner, "G2BClient", FailingG2BClient)
    settings = _tmp_settings(
        tmp_path,
        g2b_enable_real_api=True,
        g2b_api_service_key="LOCAL_ONLY_SECRET",
        g2b_list_endpoint_path="/1230000/ad/BidPublicInfoService/getBidPblancListInfoServcPPSSrch",
    )

    summary = run_recommendation_job(
        settings=settings,
        mode="real",
        keyword="AI",
        start_date="2026-06-01",
        end_date="2026-06-20",
        confirm_real_api_call=True,
    )

    assert summary.status == "error"
    assert summary.error_code == "real_ops_disabled"
    assert summary.recommendation_count == 0
    assert "LOCAL_ONLY_SECRET" not in summary.model_dump_json()


def test_ops_api_fixture_run_and_queries(tmp_path: Path, monkeypatch) -> None:  # noqa: ANN001
    settings = _tmp_settings(tmp_path)
    monkeypatch.setattr(routes, "get_settings", lambda: settings)

    run_response = client.post(
        "/ops/run-recommendations",
        json={"mode": "fixture", "keyword": "AI", "num_rows": 2, "include_reports": True},
    )

    assert run_response.status_code == 200
    summary = run_response.json()
    assert summary["status"] == "success"
    assert summary["service_key_exposed"] is False

    runs_payload = client.get("/ops/runs", params={"limit": 5}).json()
    detail_payload = client.get(f"/ops/runs/{summary['run_id']}").json()
    recommendations_payload = client.get(
        "/ops/recommendations",
        params={"limit": 5, "keyword": "AI"},
    ).json()
    reports_payload = client.get(f"/ops/reports/{summary['run_id']}").json()

    assert any(run["run_id"] == summary["run_id"] for run in runs_payload["runs"])
    assert detail_payload["run"]["run_id"] == summary["run_id"]
    assert detail_payload["recommendations"]
    assert recommendations_payload["recommendations"]
    assert reports_payload["reports"]
    assert "serviceKey" not in str(detail_payload)


def test_ops_quality_summary_returns_expected_fields_without_secrets(
    tmp_path: Path,
    monkeypatch,
) -> None:  # noqa: ANN001
    settings = _tmp_settings(tmp_path, g2b_api_service_key="LOCAL_ONLY_SECRET")
    monkeypatch.setattr(routes, "get_settings", lambda: settings)

    run_response = client.post(
        "/ops/run-recommendations",
        json={"mode": "fixture", "keyword": "AI", "num_rows": 3, "include_reports": True},
    )

    payload = client.get("/ops/quality-summary").json()

    assert run_response.status_code == 200
    expected_fields = {
        "total_runs",
        "total_reports",
        "real_report_count",
        "total_recommendations",
        "strong_recommend_count",
        "recommend_count",
        "consider_count",
        "not_recommended_count",
        "average_score",
        "summary_status",
        "latest_run_id",
        "latest_run_created_at",
        "latest_run",
        "successful_run_count",
        "failed_run_count",
        "warning_count",
        "error_count",
        "real_run_count",
        "fixture_run_count",
        "real_mode_executed",
        "real_mode_status",
        "quality_label_distribution",
        "service_key_exposed",
    }
    assert expected_fields.issubset(payload)
    assert payload["total_runs"] == 1
    assert payload["total_reports"] >= 1
    assert payload["real_report_count"] == 0
    assert payload["total_recommendations"] >= 1
    assert payload["summary_status"] == "success"
    assert payload["latest_run_id"] == run_response.json()["run_id"]
    assert payload["latest_run_created_at"]
    assert payload["latest_run"]["mode"] == "fixture"
    assert payload["fixture_run_count"] == 1
    assert payload["real_run_count"] == 0
    assert payload["real_mode_executed"] is False
    assert payload["quality_label_distribution"]
    assert payload["service_key_exposed"] is False
    assert "LOCAL_ONLY_SECRET" not in str(payload)


def test_ops_report_index_returns_safe_report_metadata_without_secrets(
    tmp_path: Path,
    monkeypatch,
) -> None:  # noqa: ANN001
    settings = _tmp_settings(tmp_path, g2b_api_service_key="LOCAL_ONLY_SECRET")
    monkeypatch.setattr(routes, "get_settings", lambda: settings)

    run_response = client.post(
        "/ops/run-recommendations",
        json={"mode": "fixture", "keyword": "AI", "num_rows": 2, "include_reports": True},
    )
    payload = client.get("/ops/report-index", params={"limit": 10}).json()

    assert run_response.status_code == 200
    assert payload["service_key_exposed"] is False
    assert payload["status"] == "success"
    assert payload["report_count"] >= 1
    assert payload["latest_run_id"] == run_response.json()["run_id"]
    assert payload["warning_count"] >= 0
    assert payload["error_count"] == 0
    assert payload["reports"]
    first_report = payload["reports"][0]
    assert {
        "run_id",
        "notice_id",
        "title",
        "report_path",
        "created_at",
        "mode",
        "source",
        "keyword",
        "query_label",
        "total_items",
        "recommendation_count",
        "recommended_count",
        "average_score",
        "score_min",
        "score_max",
        "matching_score",
        "recommendation_grade",
        "quality_label",
        "warning_count",
        "run_warning_count",
        "error_count",
        "report_metadata_reference",
        "report_content_url",
    }.issubset(first_report)
    assert first_report["mode"] == "fixture"
    assert first_report["source"] == "fixture"
    assert first_report["recommendation_count"] >= 1
    assert first_report["matching_score"] >= 0
    assert first_report["recommendation_grade"]
    assert first_report["run_warning_count"] >= first_report["warning_count"]
    assert first_report["quality_label"] in {
        "strong_fit",
        "recommended",
        "review",
        "low_fit",
        "empty",
        "failure",
    }
    assert first_report["report_metadata_reference"] == (
        f"{first_report['run_id']}:{first_report['notice_id']}"
    )
    assert first_report["report_content_url"].startswith("/ops/report-content/")
    assert Path(first_report["report_path"]).resolve().is_relative_to(
        Path(settings.yonlab_report_dir).resolve()
    )
    assert "LOCAL_ONLY_SECRET" not in str(payload)


def test_ops_quality_summary_and_report_index_do_not_create_db_file(
    tmp_path: Path,
    monkeypatch,
) -> None:  # noqa: ANN001
    settings = _tmp_settings(tmp_path)
    db_path = Path(settings.yonlab_storage_db_path)
    monkeypatch.setattr(routes, "get_settings", lambda: settings)

    quality_payload = client.get("/ops/quality-summary").json()
    index_payload = client.get("/ops/report-index").json()

    assert quality_payload["summary_status"] == "empty"
    assert quality_payload["real_mode_status"] == "empty"
    assert index_payload["status"] == "empty"
    assert index_payload["reports"] == []
    assert not db_path.exists()


def test_ops_api_real_mode_is_blocked_by_default(tmp_path: Path, monkeypatch) -> None:  # noqa: ANN001
    settings = _tmp_settings(
        tmp_path,
        g2b_enable_real_api=True,
        g2b_api_service_key="LOCAL_ONLY_SECRET",
        g2b_list_endpoint_path="/1230000/ad/BidPublicInfoService/getBidPblancListInfoServcPPSSrch",
    )
    monkeypatch.setattr(routes, "get_settings", lambda: settings)

    response = client.post(
        "/ops/run-recommendations",
        json={
            "mode": "real",
            "keyword": "AI",
            "start_date": "2026-06-01",
            "end_date": "2026-06-20",
            "confirm_real_api_call": True,
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["status"] == "error"
    assert payload["error_code"] == "real_ops_disabled"
    assert payload["recommendation_count"] == 0
    assert "LOCAL_ONLY_SECRET" not in str(payload)


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


def _read_generated_text(tmp_path: Path) -> str:
    parts = []
    for path in tmp_path.rglob("*"):
        if path.is_file() and path.suffix in {".json", ".md", ".sqlite3"}:
            parts.append(path.read_bytes().decode("utf-8", errors="ignore"))
    return "\n".join(parts)
