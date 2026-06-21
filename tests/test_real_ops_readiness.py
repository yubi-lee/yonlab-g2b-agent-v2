from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import app.api.routes as routes
from app.core.config import Settings
from app.main import app
from app.services.real_ops_readiness import build_real_ops_readiness

client = TestClient(app)


def test_real_ops_readiness_default_is_safe_and_does_not_create_db(tmp_path: Path) -> None:
    db_path = tmp_path / "ops" / "should_not_exist.sqlite3"
    settings = Settings(
        g2b_enable_real_api=True,
        g2b_api_service_key="SECRET-KEY",
        g2b_list_endpoint_path="/1230000/ad/BidPublicInfoService/getBidPblancListInfoServcPPSSrch",
        yonlab_auto_run_real_api=False,
        yonlab_storage_db_path=str(db_path),
        yonlab_report_dir=str(tmp_path / "reports"),
    )

    readiness = build_real_ops_readiness(settings)

    assert readiness["ready"] is False
    assert readiness["checks"]["real_search_ready"] is True
    assert readiness["checks"]["real_ops_enabled"] is False
    assert "YONLAB_AUTO_RUN_REAL_API=true" in readiness["missing"]
    assert readiness["will_call_real_api"] is False
    assert readiness["db_write_attempted"] is False
    assert readiness["service_key_exposed"] is False
    assert "SECRET-KEY" not in str(readiness)
    assert db_path.exists() is False


def test_real_ops_readiness_can_be_ready_for_controlled_manual_run(tmp_path: Path) -> None:
    settings = Settings(
        g2b_enable_real_api=True,
        g2b_api_service_key="SECRET-KEY",
        g2b_list_endpoint_path="/1230000/ad/BidPublicInfoService/getBidPblancListInfoServcPPSSrch",
        yonlab_auto_run_real_api=True,
        yonlab_default_num_rows=3,
        yonlab_storage_db_path=str(tmp_path / "ops.sqlite3"),
        yonlab_report_dir=str(tmp_path / "reports"),
    )

    readiness = build_real_ops_readiness(settings)

    assert readiness["ready"] is True
    assert readiness["missing"] == []
    assert readiness["will_call_real_api"] is False
    assert readiness["db_write_attempted"] is False
    assert "SECRET-KEY" not in str(readiness)


def test_real_ops_readiness_api_is_safe(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    settings = Settings(
        g2b_enable_real_api=True,
        g2b_api_service_key="SECRET-KEY",
        g2b_list_endpoint_path="/1230000/ad/BidPublicInfoService/getBidPblancListInfoServcPPSSrch",
        yonlab_auto_run_real_api=False,
        yonlab_storage_db_path=str(tmp_path / "ops.sqlite3"),
        yonlab_report_dir=str(tmp_path / "reports"),
    )
    monkeypatch.setattr(routes, "get_settings", lambda: settings)

    response = client.get("/ops/real-readiness")

    payload = response.json()
    assert response.status_code == 200
    assert payload["ready"] is False
    assert payload["service_key_exposed"] is False
    assert payload["will_call_real_api"] is False
    assert payload["db_write_attempted"] is False
    assert "SECRET-KEY" not in str(payload)
