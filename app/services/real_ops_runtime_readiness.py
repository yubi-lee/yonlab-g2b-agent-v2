import argparse
import json
from pathlib import Path
from typing import Any

from app.core.config import Settings, get_settings
from app.integrations.g2b.presets import resolve_endpoint_path

EXPECTED_PROJECT_NAME = "yonlab-g2b-agent-v2"


def build_real_ops_runtime_readiness(
    settings: Settings,
    *,
    project_root: str | Path | None = None,
    confirm_controlled_real_call_intent: bool = False,
) -> dict[str, Any]:
    root = Path(project_root or Path.cwd()).resolve()
    endpoint_path, endpoint_path_source = resolve_endpoint_path(settings)
    checks = {
        "project_path_ok": root.name == EXPECTED_PROJECT_NAME,
        "env_file_present": (root / ".env").is_file(),
        "real_api_master_flag_configured": settings.g2b_enable_real_api,
        "ops_runtime_gate_configured": settings.yonlab_auto_run_real_api,
        "service_key_present": bool(settings.g2b_api_service_key),
        "api_base_url_configured": bool(settings.g2b_api_base_url),
        "endpoint_path_configured": bool(endpoint_path),
        "request_timeout_configured": settings.g2b_request_timeout_seconds > 0,
        "default_rows_limited": 1 <= settings.yonlab_default_num_rows <= 10,
        "storage_db_path_configured": bool(settings.yonlab_storage_db_path),
        "report_dir_configured": bool(settings.yonlab_report_dir),
        "confirm_required": True,
        "confirm_flag_present": confirm_controlled_real_call_intent,
    }
    blocking_reasons = _blocking_reasons(checks)
    return {
        "project_path": str(root),
        "project_path_ok": checks["project_path_ok"],
        "env_file_present": checks["env_file_present"],
        "real_api_master_flag_configured": checks["real_api_master_flag_configured"],
        "ops_runtime_gate_configured": checks["ops_runtime_gate_configured"],
        "service_key_present": checks["service_key_present"],
        "api_base_url_configured": checks["api_base_url_configured"],
        "endpoint_path_configured": checks["endpoint_path_configured"],
        "endpoint_path_source": endpoint_path_source,
        "request_timeout_configured": checks["request_timeout_configured"],
        "default_rows_limited": checks["default_rows_limited"],
        "storage_db_path_configured": checks["storage_db_path_configured"],
        "report_dir_configured": checks["report_dir_configured"],
        "confirm_required": checks["confirm_required"],
        "confirm_flag_present": checks["confirm_flag_present"],
        "ready_for_controlled_real_call": not blocking_reasons,
        "blocking_reasons": blocking_reasons,
        "real_network_call_attempted": False,
        "db_write_attempted": False,
        "service_key_exposed": False,
        "safe_next_action": _safe_next_action(blocking_reasons),
    }


def _blocking_reasons(checks: dict[str, bool]) -> list[str]:
    required_fields = {
        "project_path_ok": "Run from D:\\Views\\yonlab-g2b-agent-v2.",
        "env_file_present": "Create local .env from .env.example without committing it.",
        "real_api_master_flag_configured": (
            "Set G2B_ENABLE_REAL_API=true for controlled real calls."
        ),
        "ops_runtime_gate_configured": (
            "Set YONLAB_AUTO_RUN_REAL_API=true only for the controlled real ops window."
        ),
        "service_key_present": "Set G2B_API_SERVICE_KEY in local .env.",
        "api_base_url_configured": "Configure G2B_API_BASE_URL.",
        "endpoint_path_configured": (
            "Configure G2B_LIST_ENDPOINT_PATH or a supported G2B_ENDPOINT_PRESET."
        ),
        "request_timeout_configured": "Set G2B_REQUEST_TIMEOUT_SECONDS to a positive value.",
        "default_rows_limited": "Keep YONLAB_DEFAULT_NUM_ROWS between 1 and 10.",
        "storage_db_path_configured": "Configure YONLAB_STORAGE_DB_PATH.",
        "report_dir_configured": "Configure YONLAB_REPORT_DIR.",
        "confirm_flag_present": (
            "Pass an explicit controlled-call intent flag before the real call step."
        ),
    }
    return [message for key, message in required_fields.items() if not checks[key]]


def _safe_next_action(blocking_reasons: list[str]) -> str:
    if not blocking_reasons:
        return (
            "Ready for one controlled validation command; run only the approved "
            "confirmed command when an operator is watching."
        )
    if any("YONLAB_AUTO_RUN_REAL_API" in reason for reason in blocking_reasons):
        return "Enable the operations runtime gate only for a short controlled validation window."
    if any("G2B_API_SERVICE_KEY" in reason for reason in blocking_reasons):
        return "Add the service key to local .env only; do not paste or commit the value."
    if any("intent flag" in reason for reason in blocking_reasons):
        return (
            "Use this diagnostic to verify settings, then add the intent flag only for "
            "readiness review."
        )
    return "Resolve blocking_reasons, then rerun scripts/check_real_ops_readiness.ps1."


def main() -> None:
    parser = argparse.ArgumentParser(description="Safe real ops readiness diagnostic.")
    parser.add_argument(
        "--confirm-controlled-real-call-intent",
        action="store_true",
        help="Model operator intent for readiness only. This does not call the real API.",
    )
    args = parser.parse_args()
    payload = build_real_ops_runtime_readiness(
        get_settings(),
        confirm_controlled_real_call_intent=args.confirm_controlled_real_call_intent,
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
