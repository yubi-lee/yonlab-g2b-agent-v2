from pathlib import Path

from fastapi.testclient import TestClient

import app.api.routes as routes
from app.core.config import Settings
from app.main import app
from app.services.local_ops_package import build_local_ops_package_info

client = TestClient(app)
PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_local_ops_package_info_is_safe_without_db_write(tmp_path: Path, monkeypatch) -> None:  # noqa: ANN001
    db_path = tmp_path / "ops" / "should_not_exist.sqlite3"
    report_dir = tmp_path / "reports"
    settings = Settings(
        g2b_api_service_key="SECRET-KEY",
        yonlab_storage_db_path=str(db_path),
        yonlab_report_dir=str(report_dir),
    )
    monkeypatch.setattr(routes, "get_settings", lambda: settings)

    response = client.get("/ops/package-info")

    assert response.status_code == 200
    payload = response.json()
    assert payload["package_version"] == "1.0"
    assert payload["app_version"] == "1.0.0-local"
    assert payload["runtime_mode"] == "local_operations"
    assert payload["service_key_configured"] is True
    assert payload["service_key_exposed"] is False
    assert payload["safety"]["secrets_returned"] is False
    assert "/ui" in payload["routes"]
    assert "/ops/run-recommendations" in payload["routes"]
    assert "/ops/daily-review-pack" in payload["routes"]
    assert "scripts/start_local_ops.ps1" in payload["scripts"]
    assert "scripts/check_deploy_readiness.ps1" in payload["scripts"]
    assert "scripts/check_real_ops_readiness.ps1" in payload["scripts"]
    assert "SECRET-KEY" not in str(payload)
    assert db_path.exists() is False
    assert report_dir.exists() is False


def test_local_ops_package_builder_sanitizes_non_default_paths(tmp_path: Path) -> None:
    settings = Settings(
        yonlab_storage_db_path=str(tmp_path / "private" / "ops.sqlite3"),
        yonlab_report_dir=str(tmp_path / "private" / "reports"),
    )

    payload = build_local_ops_package_info(settings)

    assert payload["storage"]["db_path"] == "configured"
    assert payload["storage"]["report_dir"] == "configured"


def test_dashboard_surfaces_local_ops_package_card() -> None:
    response = client.get("/ui")

    assert response.status_code == 200
    assert "Local Operations v1.0 Package" in response.text
    assert "package-summary" in response.text
    assert "SECRET-KEY" not in response.text


def test_local_ops_package_scripts_and_docs_exist() -> None:
    expected_files = [
        "scripts/start_local_ops.ps1",
        "scripts/validate_ops_package.ps1",
        "scripts/smoke_ops_package_info.ps1",
        "docs/07_LOCAL_OPERATIONS_V1.md",
        "docs/07_DEPLOYMENT_HANDOFF.md",
    ]
    for relative_path in expected_files:
        assert (PROJECT_ROOT / relative_path).is_file()


def test_deployment_handoff_doc_is_safe_and_operator_ready() -> None:
    content = (PROJECT_ROOT / "docs" / "07_DEPLOYMENT_HANDOFF.md").read_text(encoding="utf-8")

    assert "Deployment Handoff" in content
    assert "/ops/review-board" in content
    assert "Review Board" in content
    assert "deadline-first" in content
    assert "no real G2B API" in content
    assert "validate_local.ps1" in content
    assert "check_deploy_readiness.ps1" in content
    assert "YONLAB_AUTO_RUN_REAL_API" in content
    assert "-ConfirmRealApiCall" in content
    assert "service keys" in content.lower()
    assert "SECRET-KEY" not in content
    assert "G2B_API_SERVICE_KEY=" not in content


def test_validate_local_references_package_smoke() -> None:
    content = (PROJECT_ROOT / "scripts" / "validate_local.ps1").read_text(encoding="utf-8")

    assert "smoke_ops_package_info.ps1" in content


def test_operator_docs_cover_review_board_workflow_and_no_real_safety() -> None:
    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    runbook = (PROJECT_ROOT / "docs" / "06_OPERATIONS_RUNBOOK.md").read_text(
        encoding="utf-8"
    )
    local_ops = (PROJECT_ROOT / "docs" / "07_LOCAL_OPERATIONS_V1.md").read_text(
        encoding="utf-8"
    )

    for content in (readme, runbook, local_ops):
        assert "Review Board" in content
        assert "/ops/review-board" in content
        assert "deadline-first" in content
        assert "active-state-first" in content
        assert "does not call the real G2B API" in content
