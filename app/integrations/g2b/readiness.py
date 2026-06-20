import json
from typing import Any

from app.core.config import Settings, get_settings
from app.integrations.g2b.presets import ENDPOINT_PATH_SOURCE_UNKNOWN_PRESET, resolve_endpoint_path


def build_real_readiness(settings: Settings) -> dict[str, Any]:
    endpoint_path, endpoint_path_source = resolve_endpoint_path(settings)
    endpoint_ready = (
        bool(endpoint_path) and endpoint_path_source != ENDPOINT_PATH_SOURCE_UNKNOWN_PRESET
    )
    checks = {
        "real_api_enabled": settings.g2b_enable_real_api,
        "service_key_configured": bool(settings.g2b_api_service_key),
        "endpoint_path_configured": endpoint_ready,
        "capture_dir_configured": bool(settings.g2b_capture_dir),
    }
    missing = []
    if not checks["real_api_enabled"]:
        missing.append("G2B_ENABLE_REAL_API=true")
    if not checks["service_key_configured"]:
        missing.append("G2B_API_SERVICE_KEY")
    if not checks["endpoint_path_configured"]:
        missing.append("G2B_LIST_ENDPOINT_PATH")

    readiness = {
        "ready": all(
            (
                checks["real_api_enabled"],
                checks["service_key_configured"],
                checks["endpoint_path_configured"],
            )
        ),
        "checks": checks,
        "missing": missing,
        "next_steps": [
            "Create .env from .env.example",
            "Set G2B_ENABLE_REAL_API=true",
            "Set G2B_API_SERVICE_KEY manually",
            "Set G2B_LIST_ENDPOINT_PATH=/1230000/ad/BidPublicInfoService",
            "Run guarded blocked smoke before confirmed real smoke",
        ],
    }
    return readiness


def main() -> None:
    payload = build_real_readiness(get_settings())
    payload["will_call_real_api"] = False
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
