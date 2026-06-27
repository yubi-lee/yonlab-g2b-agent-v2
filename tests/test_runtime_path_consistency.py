from pathlib import Path

from app.core.config import Settings
from app.services.runtime_path_consistency import build_runtime_path_consistency


def test_runtime_path_consistency_detects_stale_absolute_storage_path(
    tmp_path: Path,
) -> None:
    rc3 = tmp_path / "yonlab-g2b-agent-v2-rc3"
    rc4 = tmp_path / "yonlab-g2b-agent-v2-rc4"
    rc3.mkdir()
    rc4.mkdir()
    settings = Settings(
        yonlab_storage_db_path=str(rc3 / "data" / "ops" / "yonlab.sqlite3"),
        yonlab_report_dir=str(rc3 / "data" / "reports" / "g2b"),
    )

    payload = build_runtime_path_consistency(settings, project_root=rc4)

    assert payload["storage_path_consistent"] is False
    assert payload["report_path_consistent"] is False
    assert payload["path_blocking_reasons"]
    assert payload["real_network_call_attempted"] is False
    assert payload["service_key_exposed"] is False


def test_runtime_path_consistency_accepts_current_deploy_absolute_paths(
    tmp_path: Path,
) -> None:
    root = tmp_path / "yonlab-g2b-agent-v2-rc5"
    root.mkdir()
    settings = Settings(
        yonlab_storage_db_path=str(root / "data" / "ops" / "yonlab.sqlite3"),
        yonlab_report_dir=str(root / "data" / "reports" / "g2b"),
    )

    payload = build_runtime_path_consistency(settings, project_root=root)

    assert payload["storage_path_consistent"] is True
    assert payload["report_path_consistent"] is True
    assert payload["path_blocking_reasons"] == []


def test_runtime_path_consistency_accepts_relative_paths(tmp_path: Path) -> None:
    root = tmp_path / "yonlab-g2b-agent-v2-rc5"
    root.mkdir()
    settings = Settings(
        yonlab_storage_db_path="data/ops/yonlab.sqlite3",
        yonlab_report_dir="data/reports/g2b",
    )

    payload = build_runtime_path_consistency(settings, project_root=root)

    assert payload["storage_path_consistent"] is True
    assert payload["report_path_consistent"] is True
    assert payload["storage_path_absolute"] is False
    assert payload["report_path_absolute"] is False
