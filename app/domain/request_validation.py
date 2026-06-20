from typing import Any

SWAGGER_PLACEHOLDER_KEYS = {"additionalProp1", "additionalProp2", "additionalProp3"}
SWAGGER_PLACEHOLDER_VALUES = {"string"}


def ensure_no_swagger_placeholders(value: Any, field_name: str) -> None:
    if _contains_swagger_placeholder(value):
        raise ValueError(
            f"{field_name} contains Swagger placeholder values. "
            "Replace 'string' and additionalProp examples with real notice fields."
        )


def ensure_meaningful_notice_payload(value: Any, field_name: str) -> None:
    if not _has_meaningful_value(value):
        raise ValueError(
            f"{field_name} must include at least one real notice field, "
            "such as bidNtceNm, title, agency, qualification, or description."
        )


def _contains_swagger_placeholder(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().casefold() in SWAGGER_PLACEHOLDER_VALUES
    if isinstance(value, dict):
        return any(
            key in SWAGGER_PLACEHOLDER_KEYS or _contains_swagger_placeholder(item)
            for key, item in value.items()
        )
    if isinstance(value, list | tuple | set):
        return any(_contains_swagger_placeholder(item) for item in value)
    return False


def _has_meaningful_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        text = value.strip()
        return bool(text) and text.casefold() not in SWAGGER_PLACEHOLDER_VALUES
    if isinstance(value, dict):
        return any(
            key not in SWAGGER_PLACEHOLDER_KEYS and _has_meaningful_value(item)
            for key, item in value.items()
        )
    if isinstance(value, list | tuple | set):
        return any(_has_meaningful_value(item) for item in value)
    return True
