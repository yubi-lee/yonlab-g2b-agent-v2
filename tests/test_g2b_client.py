import httpx

from app.core.config import Settings
from app.domain.search import G2BSearchMode, G2BSearchRequest
from app.integrations.g2b.client import G2BClient
from app.integrations.g2b.errors import G2BClientError
from app.integrations.g2b.normalizer import normalize_g2b_notice


class RecordingHttpClient:
    def __init__(self, response: httpx.Response | None = None) -> None:
        self.response = response
        self.called = False
        self.params = None

    def get(self, url, params):  # noqa: ANN001
        self.called = True
        self.params = params
        if self.response is None:
            raise AssertionError("HTTP client should not have been called.")
        return self.response


def test_real_api_call_blocked_when_disabled() -> None:
    http_client = RecordingHttpClient()
    client = G2BClient(Settings(g2b_enable_real_api=False), http_client=http_client)

    error = _capture_error(client)

    assert error.code == "real_api_disabled"
    assert http_client.called is False


def test_real_api_call_blocked_when_confirmation_missing() -> None:
    settings = Settings(
        g2b_enable_real_api=True,
        g2b_api_service_key="SECRET-KEY",
        g2b_list_endpoint_path="/g2b/list",
    )
    http_client = RecordingHttpClient()
    client = G2BClient(settings, http_client=http_client)

    error = _capture_error(client, confirm_real_api_call=False)

    assert error.code == "confirmation_required"
    assert "SECRET-KEY" not in str(error)
    assert http_client.called is False


def test_real_api_call_blocked_when_service_key_missing() -> None:
    settings = Settings(g2b_enable_real_api=True, g2b_list_endpoint_path="/g2b/list")
    http_client = RecordingHttpClient()
    client = G2BClient(settings, http_client=http_client)

    error = _capture_error(client)

    assert error.code == "service_key_missing"
    assert "serviceKey" not in str(error)
    assert http_client.called is False


def test_mocked_successful_real_api_response_is_normalized() -> None:
    settings = Settings(
        g2b_enable_real_api=True,
        g2b_api_service_key="SECRET-KEY",
        g2b_list_endpoint_path="/g2b/list",
    )
    request = httpx.Request("GET", "https://example.test/g2b/list")
    response = httpx.Response(
        200,
        json={
            "response": {
                "body": {
                    "items": {
                        "item": [
                            {
                                "bidNtceNo": "REAL-001",
                                "bidNtceNm": "AI 시스템 구축",
                                "dminsttNm": "테스트기관",
                            }
                        ]
                    }
                }
            }
        },
        request=request,
    )
    http_client = RecordingHttpClient(response=response)
    client = G2BClient(settings, http_client=http_client)

    raw_notices = client.search(_real_request())
    notice = normalize_g2b_notice(raw_notices[0])

    assert http_client.called is True
    assert http_client.params["serviceKey"] == "SECRET-KEY"
    assert notice.notice_id == "REAL-001"
    assert notice.title == "AI 시스템 구축"


def test_mocked_empty_real_api_response_returns_empty_result() -> None:
    settings = Settings(
        g2b_enable_real_api=True,
        g2b_api_service_key="SECRET-KEY",
        g2b_list_endpoint_path="/g2b/list",
    )
    response = httpx.Response(
        200,
        json={"response": {"body": {"items": {"item": []}}}},
        request=httpx.Request("GET", "https://example.test/g2b/list"),
    )
    client = G2BClient(settings, http_client=RecordingHttpClient(response=response))

    assert client.search(_real_request()) == []


def _real_request(confirm_real_api_call: bool = True) -> G2BSearchRequest:
    return G2BSearchRequest(
        mode=G2BSearchMode.REAL,
        keyword="AI",
        confirm_real_api_call=confirm_real_api_call,
    )


def _capture_error(
    client: G2BClient,
    confirm_real_api_call: bool = True,
) -> G2BClientError:
    try:
        client.search(_real_request(confirm_real_api_call=confirm_real_api_call))
    except G2BClientError as exc:
        return exc
    raise AssertionError("Expected G2BClientError.")
