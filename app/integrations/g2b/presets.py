from dataclasses import dataclass

from app.core.config import Settings


@dataclass(frozen=True)
class G2BEndpointPreset:
    name: str
    path: str
    description: str


ENDPOINT_PATH_SOURCE_EXPLICIT = "explicit"
ENDPOINT_PATH_SOURCE_PRESET = "preset"
ENDPOINT_PATH_SOURCE_MISSING = "missing"
ENDPOINT_PATH_SOURCE_UNKNOWN_PRESET = "unknown_preset"

G2B_ENDPOINT_PRESETS = [
    {
        "name": "custom",
        "path": "",
        "description": "Use G2B_LIST_ENDPOINT_PATH from .env.",
    },
    {
        "name": "approved_bid_public_info_service",
        "path": "/1230000/ad/BidPublicInfoService",
        "description": (
            "Approved G2B BidPublicInfoService endpoint base path. Confirm exact operation "
            "path in Public Data Portal Swagger if real smoke returns HTTP/path errors."
        ),
    },
]


def list_endpoint_presets() -> list[G2BEndpointPreset]:
    return [G2BEndpointPreset(**preset) for preset in G2B_ENDPOINT_PRESETS]


def get_endpoint_preset(name: str) -> G2BEndpointPreset | None:
    normalized_name = name.strip().casefold()
    if not normalized_name:
        return None
    return next(
        (
            preset
            for preset in list_endpoint_presets()
            if preset.name.casefold() == normalized_name
        ),
        None,
    )


def resolve_endpoint_path(settings: Settings) -> tuple[str, str]:
    explicit_path = settings.g2b_list_endpoint_path.strip()
    if explicit_path:
        return explicit_path, ENDPOINT_PATH_SOURCE_EXPLICIT

    preset_name = settings.g2b_endpoint_preset.strip()
    if not preset_name or preset_name.casefold() == "custom":
        return "", ENDPOINT_PATH_SOURCE_MISSING

    preset = get_endpoint_preset(preset_name)
    if preset is None:
        return "", ENDPOINT_PATH_SOURCE_UNKNOWN_PRESET
    return preset.path, ENDPOINT_PATH_SOURCE_PRESET
