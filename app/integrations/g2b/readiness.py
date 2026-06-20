import json
from typing import Any

from app.core.config import Settings, get_settings
from app.integrations.g2b.presets import (
    ENDPOINT_PATH_SOURCE_UNKNOWN_PRESET,
    get_endpoint_preset,
    resolve_endpoint_path,
)


def build_real_readiness(settings: Settings) -> dict[str, Any]:
    endpoint_path, endpoint_path_source = resolve_endpoint_path(settings)
    preset = get_endpoint_preset(settings.g2b_endpoint_preset)
    endpoint_ready = (
        bool(endpoint_path) and endpoint_path_source != ENDPOINT_PATH_SOURCE_UNKNOWN_PRESET
    )

    checks = [
        {
            "name": "real_api_enabled",
            "ok": settings.g2b_enable_real_api,
            "required_for_confirmed_call": True,
            "guidance": (
                "Set G2B_ENABLE_REAL_API=true only when you are ready to run a confirmed "
                "real smoke."
            ),
        },
        {
            "name": "service_key_configured",
            "ok": bool(settings.g2b_api_service_key),
            "required_for_confirmed_call": True,
            "guidance": (
                "Store the service key in local .env only. Do not commit or paste it into "
                "scripts."
            ),
        },
        {
            "name": "endpoint_path_configured",
            "ok": endpoint_ready,
            "required_for_confirmed_call": True,
            "guidance": "Set G2B_LIST_ENDPOINT_PATH explicitly or use G2B_ENDPOINT_PRESET.",
        },
        {
            "name": "endpoint_preset_known",
            "ok": not settings.g2b_endpoint_preset or preset is not None,
            "required_for_confirmed_call": False,
            "guidance": "Use bid_notice_service for the first YOnLab AI/SW service smoke.",
        },
        {
            "name": "capture_directory_ignored",
            "ok": settings.g2b_capture_dir.startswith("data/captured/"),
            "required_for_confirmed_call": False,
            "guidance": (
                "Captured responses should stay under data/captured/, which is ignored by Git."
            ),
        },
    ]

    return {
        "ready_for_confirmed_real_smoke": all(
            check["ok"] for check in checks if check["required_for_confirmed_call"]
        ),
        "will_call_real_api": False,
        "service_key_configured": bool(settings.g2b_api_service_key),
        "service_key_value": "not_returned",
        "base_url_configured": bool(settings.g2b_api_base_url),
        "endpoint_path_configured": endpoint_ready,
        "endpoint_path_source": endpoint_path_source,
        "endpoint_preset": settings.g2b_endpoint_preset or None,
        "recommended_first_preset": "bid_notice_service",
        "recommended_first_request": {
            "mode": "real",
            "keyword": "AI",
            "page_no": 1,
            "num_rows": 3,
            "confirm_real_api_call": True,
        },
        "checks": checks,
    }


def main() -> None:
    print(json.dumps(build_real_readiness(get_settings()), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
