from pathlib import Path

from app.core.config import Settings
from app.services.real_ops_runtime_readiness import build_real_ops_runtime_readiness


def test_real_ops_runtime_readiness_blocks_when_everything_missing(tmp_path: Path) -> None:
    settings = Settings(
        g2b_enable_real_api=False,
        g2b_api_base_url="",
        g2b_api_service_key="",
        g2b_list_endpoint_path="",
        g2b_endpoint_preset="",
        g2b_request_timeout_seconds=0,
        yonlab_auto_run_real_api=False,
        yonlab_default_num_rows=99,
        yonlab_storage_db_path="",
        yonlab_report_dir="",
    )

    readiness = build_real_ops_runtime_readiness(settings, project_root=tmp_path)

    assert readiness["ready_for_controlled_real_call"] is False
    assert readiness["project_path_ok"] is False
    assert readiness["env_file_present"] is False
    assert readiness["real_api_master_flag_configured"] is False
    assert readiness["ops_runtime_gate_configured"] is False
    assert readiness["service_key_present"] is False
    assert readiness["api_base_url_configured"] is False
    assert readiness["confirm_flag_present"] is False
    assert readiness["blocking_reasons"]
    assert readiness["real_network_call_attempted"] is False
    assert readiness["db_write_attempted"] is False
    assert readiness["service_key_exposed"] is False


def test_real_ops_runtime_readiness_blocks_when_only_service_key_is_present(
    tmp_path: Path,
) -> None:
    project_root = _project_root(tmp_path, env_file=True)
    settings = Settings(
        g2b_enable_real_api=False,
        g2b_api_service_key="SECRET-KEY",
        g2b_list_endpoint_path="",
        yonlab_auto_run_real_api=False,
    )

    readiness = build_real_ops_runtime_readiness(settings, project_root=project_root)

    assert readiness["ready_for_controlled_real_call"] is False
    assert readiness["service_key_present"] is True
    assert readiness["real_api_master_flag_configured"] is False
    assert readiness["ops_runtime_gate_configured"] is False
    assert "SECRET-KEY" not in str(readiness)


def test_real_ops_runtime_readiness_blocks_when_only_confirm_intent_is_present(
    tmp_path: Path,
) -> None:
    settings = Settings(
        g2b_enable_real_api=False,
        g2b_api_service_key="",
        g2b_list_endpoint_path="",
        yonlab_auto_run_real_api=False,
    )

    readiness = build_real_ops_runtime_readiness(
        settings,
        project_root=tmp_path,
        confirm_controlled_real_call_intent=True,
    )

    assert readiness["ready_for_controlled_real_call"] is False
    assert readiness["confirm_required"] is True
    assert readiness["confirm_flag_present"] is True
    assert readiness["service_key_present"] is False
    assert readiness["real_network_call_attempted"] is False


def test_real_ops_runtime_readiness_identifies_missing_runtime_gate(tmp_path: Path) -> None:
    project_root = _project_root(tmp_path, env_file=True)
    settings = _ready_settings(tmp_path, yonlab_auto_run_real_api=False)

    readiness = build_real_ops_runtime_readiness(
        settings,
        project_root=project_root,
        confirm_controlled_real_call_intent=True,
    )

    assert readiness["ready_for_controlled_real_call"] is False
    assert readiness["real_api_master_flag_configured"] is True
    assert readiness["ops_runtime_gate_configured"] is False
    assert any("YONLAB_AUTO_RUN_REAL_API" in item for item in readiness["blocking_reasons"])
    assert readiness["safe_next_action"].startswith("Enable the operations runtime gate")


def test_real_ops_runtime_readiness_can_be_ready_without_calling_network(
    tmp_path: Path,
) -> None:
    project_root = _project_root(tmp_path, env_file=True)
    settings = _ready_settings(tmp_path, yonlab_auto_run_real_api=True)

    readiness = build_real_ops_runtime_readiness(
        settings,
        project_root=project_root,
        confirm_controlled_real_call_intent=True,
    )

    assert readiness["ready_for_controlled_real_call"] is True
    assert readiness["blocking_reasons"] == []
    assert readiness["project_path_ok"] is True
    assert readiness["env_file_present"] is True
    assert readiness["real_api_master_flag_configured"] is True
    assert readiness["ops_runtime_gate_configured"] is True
    assert readiness["service_key_present"] is True
    assert readiness["api_base_url_configured"] is True
    assert readiness["endpoint_path_configured"] is True
    assert readiness["confirm_flag_present"] is True
    assert readiness["real_network_call_attempted"] is False
    assert readiness["db_write_attempted"] is False
    assert readiness["service_key_exposed"] is False
    assert "SECRET-KEY" not in str(readiness)


def _project_root(tmp_path: Path, *, env_file: bool) -> Path:
    project_root = tmp_path / "yonlab-g2b-agent-v2"
    project_root.mkdir()
    if env_file:
        (project_root / ".env").write_text("", encoding="utf-8")
    return project_root


def _ready_settings(tmp_path: Path, *, yonlab_auto_run_real_api: bool) -> Settings:
    return Settings(
        g2b_enable_real_api=True,
        g2b_api_base_url="https://example.invalid",
        g2b_api_service_key="SECRET-KEY",
        g2b_list_endpoint_path="/1230000/ad/BidPublicInfoService/getBidPblancListInfoServcPPSSrch",
        g2b_request_timeout_seconds=15,
        yonlab_auto_run_real_api=yonlab_auto_run_real_api,
        yonlab_default_num_rows=3,
        yonlab_storage_db_path=str(tmp_path / "ops.sqlite3"),
        yonlab_report_dir=str(tmp_path / "reports"),
    )
