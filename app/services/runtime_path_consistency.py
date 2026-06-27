import argparse
import json
from pathlib import Path
from typing import Any

from app.core.config import Settings, get_settings


def build_runtime_path_consistency(
    settings: Settings,
    *,
    project_root: str | Path | None = None,
) -> dict[str, Any]:
    root = Path(project_root or Path.cwd()).resolve()
    storage_raw = Path(settings.yonlab_storage_db_path) if settings.yonlab_storage_db_path else None
    report_raw = Path(settings.yonlab_report_dir) if settings.yonlab_report_dir else None
    storage_path = _resolve_under_root(root, storage_raw)
    report_path = _resolve_under_root(root, report_raw)
    storage_consistent = storage_path is not None and _is_relative_to(storage_path, root)
    report_consistent = report_path is not None and _is_relative_to(report_path, root)

    blocking_reasons = []
    if storage_raw is None:
        blocking_reasons.append("Configure YONLAB_STORAGE_DB_PATH.")
    elif not storage_consistent:
        blocking_reasons.append(
            "YONLAB_STORAGE_DB_PATH must resolve under the current deploy folder."
        )
    if report_raw is None:
        blocking_reasons.append("Configure YONLAB_REPORT_DIR.")
    elif not report_consistent:
        blocking_reasons.append("YONLAB_REPORT_DIR must resolve under the current deploy folder.")

    return {
        "current_deploy_folder": str(root),
        "storage_path_configured": storage_raw is not None,
        "report_path_configured": report_raw is not None,
        "storage_path_absolute": bool(storage_raw and storage_raw.is_absolute()),
        "report_path_absolute": bool(report_raw and report_raw.is_absolute()),
        "storage_path_consistent": storage_consistent,
        "report_path_consistent": report_consistent,
        "runtime_data_root": str(root),
        "effective_ops_storage_root": str(storage_path.parent) if storage_path else "",
        "effective_report_root": str(report_path) if report_path else "",
        "storage_basename": storage_path.name if storage_path else "",
        "report_basename": report_path.name if report_path else "",
        "path_blocking_reasons": blocking_reasons,
        "real_network_call_attempted": False,
        "service_key_exposed": False,
    }


def _resolve_under_root(root: Path, path: Path | None) -> Path | None:
    if path is None:
        return None
    if path.is_absolute():
        return path.resolve()
    return (root / path).resolve()


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Safe runtime path consistency diagnostic.")
    parser.add_argument("--project-root", default="", help="Repository root to validate.")
    args = parser.parse_args()
    payload = build_runtime_path_consistency(
        get_settings(),
        project_root=args.project_root or None,
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
