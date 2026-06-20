import httpx

from app.core.config import Settings
from app.domain.search import G2BSearchMode, G2BSearchRequest
from app.integrations.g2b.client import G2BClient
from app.integrations.g2b.errors import G2BClientError
from app.integrations.g2b.presets import (
    ENDPOINT_PATH_SOURCE_EXPLICIT,
    ENDPOINT_PATH_SOURCE_PRESET,
    get_endpoint_preset,
    list_endpoint_presets,
    resolve_endpoint_path,
)


def test_endpoint_presets_include_yonlab_recommended_service_operation() -> None:
    presets = list_endpoint_presets()
    service_preset = get_endpoint_preset("approved_bid_public_info_service")

    assert len(presets) >= 2
    assert service_preset is not None
    assert service_preset.path == "/1230000/ad/BidPublicInfoService"
    assert "Approved G2B BidPublicInfoService" in service_preset.description
    assert get_endpoint_preset("custom") is not None


def test_explicit_endpoint_path_overrides_preset() -> None:
    settings = Settings(
        g2b_list_endpoint_path="/explicit/path",
        g2b_endpoint_preset="approved_bid_public_info_service",
    )

    endpoint_path, source = resolve_endpoint_path(settings)

    assert endpoint_path == "/explicit/path"
    assert source == ENDPOINT_PATH_SOURCE_EXPLICIT


def test_endpoint_preset_resolves_when_explicit_path_missing() -> None:
    settings = Settings(g2b_endpoint_preset="approved_bid_public_info_service")

    endpoint_path, source = resolve_endpoint_path(settings)

    assert endpoint_path == "/1230000/ad/BidPublicInfoService"
    assert source == ENDPOINT_PATH_SOURCE_PRESET


def test_unknown_endpoint_preset_blocks_before_http_call() -> None:
    http_client = _FailIfCalledHttpClient()
    client = G2BClient(
        Settings(
            g2b_enable_real_api=True,
            g2b_api_service_key="SECRET-KEY",
            g2b_endpoint_preset="not_a_real_preset",
        ),
        http_client=http_client,
    )

    try:
        client.search(
            G2BSearchRequest(
                mode=G2BSearchMode.REAL,
                keyword="AI",
                confirm_real_api_call=True,
            )
        )
    except G2BClientError as exc:
        error = exc
    else:
        raise AssertionError("Expected unknown preset to block the real call.")

    assert error.code == "endpoint_preset_unknown"
    assert "SECRET-KEY" not in str(error)
    assert http_client.called is False


class _FailIfCalledHttpClient:
    def __init__(self) -> None:
        self.called = False

    def get(self, url, params):  # noqa: ANN001
        self.called = True
        return httpx.Response(500, request=httpx.Request("GET", "https://example.test"))
