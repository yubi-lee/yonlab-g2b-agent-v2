import json
from typing import Any

from app.core.config import Settings, get_settings
from app.integrations.g2b.readiness import build_real_readiness


def build_real_ops_readiness(settings: Settings) -> dict[str, Any]:
    real_readiness = build_real_readiness(settings)
    checks = {
        "real_search_ready": bool(real_readiness["ready"]),
        "real_ops_enabled": settings.yonlab_auto_run_real_api,
        "storage_db_path_configured": bool(settings.yonlab_storage_db_path),
        "report_dir_configured": bool(settings.yonlab_report_dir),
        "default_num_rows_limited": 1 <= settings.yonlab_default_num_rows <= 10,
    }
    missing = []
    if not checks["real_search_ready"]:
        missing.extend(real_readiness["missing"])
    if not checks["real_ops_enabled"]:
        missing.append("YONLAB_AUTO_RUN_REAL_API=true")
    if not checks["storage_db_path_configured"]:
        missing.append("YONLAB_STORAGE_DB_PATH")
    if not checks["report_dir_configured"]:
        missing.append("YONLAB_REPORT_DIR")
    if not checks["default_num_rows_limited"]:
        missing.append("YONLAB_DEFAULT_NUM_ROWS<=10")

    return {
        "ready": all(checks.values()),
        "mode": "real_operations",
        "checks": checks,
        "real_search": real_readiness,
        "missing": _dedupe(missing),
        "next_steps": [
            "Run scripts/validate_g2b_real_readiness.ps1 first.",
            "Set YONLAB_AUTO_RUN_REAL_API=true only for a controlled manual real ops run.",
            "Keep YONLAB_DEFAULT_NUM_ROWS small, ideally 3 or less for first validation.",
            "Run one confirmed real operation from /ui or /ops/run-recommendations.",
            "Return YONLAB_AUTO_RUN_REAL_API=false after validation.",
        ],
        "will_call_real_api": False,
        "db_write_attempted": False,
        "service_key_exposed": False,
    }


def _dedupe(values: list[str]) -> list[str]:
    deduped = []
    for value in values:
        if value not in deduped:
            deduped.append(value)
    return deduped


def main() -> None:
    print(json.dumps(build_real_ops_readiness(get_settings()), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
