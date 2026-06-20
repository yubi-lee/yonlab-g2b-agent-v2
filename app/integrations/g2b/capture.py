import json
from datetime import datetime
from pathlib import Path
from typing import Any

MASKED_VALUE = "****MASKED****"
SECRET_KEYS = {"servicekey", "service_key", "g2b_api_service_key", "apikey", "api_key"}


def capture_real_response(
    capture_dir: str,
    request_metadata: dict[str, Any],
    response_payload: Any,
) -> Path:
    target_dir = Path(capture_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target_path = target_dir / f"g2b_real_response_{timestamp}.json"
    suffix = 1
    while target_path.exists():
        target_path = target_dir / f"g2b_real_response_{timestamp}_{suffix}.json"
        suffix += 1

    payload = {
        "captured_at": timestamp,
        "request": sanitize_for_capture(request_metadata),
        "response": sanitize_for_capture(response_payload),
    }
    target_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return target_path


def sanitize_for_capture(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: MASKED_VALUE if _is_secret_key(key) else sanitize_for_capture(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [sanitize_for_capture(item) for item in value]
    if isinstance(value, tuple):
        return [sanitize_for_capture(item) for item in value]
    return value


def _is_secret_key(key: str) -> bool:
    return key.replace("-", "_").casefold() in SECRET_KEYS
