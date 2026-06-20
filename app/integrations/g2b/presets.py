from dataclasses import dataclass

from app.core.config import Settings


@dataclass(frozen=True)
class G2BEndpointPreset:
    code: str
    operation_name: str
    endpoint_path: str
    recommended_for_yonlab: bool
    guidance: str


ENDPOINT_PATH_SOURCE_EXPLICIT = "explicit"
ENDPOINT_PATH_SOURCE_PRESET = "preset"
ENDPOINT_PATH_SOURCE_MISSING = "missing"
ENDPOINT_PATH_SOURCE_UNKNOWN_PRESET = "unknown_preset"

G2B_ENDPOINT_PRESETS: dict[str, G2BEndpointPreset] = {
    "bid_notice_service": G2BEndpointPreset(
        code="bid_notice_service",
        operation_name="입찰공고 목록 조회 - 용역",
        endpoint_path="/1230000/ad/BidPublicInfoService/getBidPblancListInfoServc",
        recommended_for_yonlab=True,
        guidance="YOnLab AI/SW 용역 공고의 첫 실연동 후보입니다. 실제 사용 전 data.go.kr에서 "
        "운영명과 endpoint path를 재확인합니다.",
    ),
    "bid_notice_goods": G2BEndpointPreset(
        code="bid_notice_goods",
        operation_name="입찰공고 목록 조회 - 물품",
        endpoint_path="/1230000/ad/BidPublicInfoService/getBidPblancListInfoThng",
        recommended_for_yonlab=False,
        guidance="장비·물품 공고 확인용 후보입니다. 단순 H/W 납품은 YOnLab 추천 적합도가 낮을 수 "
        "있습니다.",
    ),
    "bid_notice_construction": G2BEndpointPreset(
        code="bid_notice_construction",
        operation_name="입찰공고 목록 조회 - 공사",
        endpoint_path="/1230000/ad/BidPublicInfoService/getBidPblancListInfoCnstwk",
        recommended_for_yonlab=False,
        guidance="건설·공사 공고 확인용 후보입니다. YOnLab 기본 추천 대상은 아닙니다.",
    ),
}


def list_endpoint_presets() -> list[G2BEndpointPreset]:
    return list(G2B_ENDPOINT_PRESETS.values())


def get_endpoint_preset(code: str) -> G2BEndpointPreset | None:
    normalized_code = code.strip().casefold()
    if not normalized_code:
        return None
    return G2B_ENDPOINT_PRESETS.get(normalized_code)


def resolve_endpoint_path(settings: Settings) -> tuple[str, str]:
    explicit_path = settings.g2b_list_endpoint_path.strip()
    if explicit_path:
        return explicit_path, ENDPOINT_PATH_SOURCE_EXPLICIT

    preset_code = settings.g2b_endpoint_preset.strip()
    if not preset_code:
        return "", ENDPOINT_PATH_SOURCE_MISSING

    preset = get_endpoint_preset(preset_code)
    if preset is None:
        return "", ENDPOINT_PATH_SOURCE_UNKNOWN_PRESET
    return preset.endpoint_path, ENDPOINT_PATH_SOURCE_PRESET
