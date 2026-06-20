import httpx

import app.integrations.g2b.client as client_module
from app.core.config import Settings
from app.domain.search import G2BSearchMode, G2BSearchRequest
from app.integrations.g2b import capture
from app.integrations.g2b.capture import MASKED_VALUE
from app.integrations.g2b.client import G2BClient
from app.integrations.g2b.errors import G2BClientError
from app.integrations.g2b.normalizer import normalize_g2b_notice


class RecordingHttpClient:
    def __init__(
        self,
        response: httpx.Response | None = None,
        error: Exception | None = None,
    ) -> None:
        self.response = response
        self.error = error
        self.called = False
        self.params = None

    def get(self, url, params):  # noqa: ANN001
        self.called = True
        self.params = params
        if self.error is not None:
            raise self.error
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

    assert error.code == "real_api_confirmation_required"
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


def test_real_api_call_blocked_when_endpoint_path_missing() -> None:
    settings = Settings(g2b_enable_real_api=True, g2b_api_service_key="SECRET-KEY")
    http_client = RecordingHttpClient()
    client = G2BClient(settings, http_client=http_client)

    error = _capture_error(client)

    assert error.code == "endpoint_path_missing"
    assert "SECRET-KEY" not in str(error)
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


def test_mocked_http_error_returns_controlled_error() -> None:
    settings = _enabled_settings()
    request = httpx.Request("GET", "https://example.test/g2b/list")
    response = httpx.Response(500, request=request)
    client = G2BClient(settings, http_client=RecordingHttpClient(response=response))

    error = _capture_error(client)

    assert error.code == "http_error"
    assert "SECRET-KEY" not in str(error)


def test_mocked_timeout_returns_controlled_error() -> None:
    settings = _enabled_settings()
    client = G2BClient(
        settings,
        http_client=RecordingHttpClient(error=httpx.TimeoutException("boom")),
    )

    error = _capture_error(client)

    assert error.code == "timeout"
    assert "boom" not in str(error)


def test_unsupported_xml_response_returns_controlled_error() -> None:
    settings = _enabled_settings()
    response = httpx.Response(
        200,
        text="<response><body></body></response>",
        request=httpx.Request("GET", "https://example.test/g2b/list"),
    )
    client = G2BClient(settings, http_client=RecordingHttpClient(response=response))

    error = _capture_error(client)

    assert error.code == "unsupported_response_format"


def test_unexpected_json_shape_returns_controlled_error() -> None:
    settings = _enabled_settings()
    response = httpx.Response(
        200,
        json={"unexpected": {"shape": True}},
        request=httpx.Request("GET", "https://example.test/g2b/list"),
    )
    client = G2BClient(settings, http_client=RecordingHttpClient(response=response))

    error = _capture_error(client)

    assert error.code == "unexpected_response_shape"


def test_capture_disabled_by_default_writes_no_files() -> None:
    settings = _enabled_settings(g2b_capture_dir="data/captured/g2b")
    client = G2BClient(settings, http_client=RecordingHttpClient(response=_success_response()))

    client.search(_real_request())

    assert settings.g2b_capture_real_responses is False


def test_capture_enabled_passes_sanitized_metadata(monkeypatch) -> None:  # noqa: ANN001
    captured = {}

    def fake_capture_real_response(capture_dir, request_metadata, response_payload):  # noqa: ANN001
        captured["capture_dir"] = capture_dir
        captured["request_metadata"] = request_metadata
        captured["response_payload"] = response_payload

    monkeypatch.setattr(client_module, "capture_real_response", fake_capture_real_response)
    settings = _enabled_settings(
        g2b_capture_real_responses=True,
        g2b_capture_dir="data/captured/g2b",
    )
    client = G2BClient(settings, http_client=RecordingHttpClient(response=_success_response()))

    client.search(_real_request())

    assert captured["capture_dir"] == "data/captured/g2b"
    assert captured["request_metadata"]["params"]["serviceKey"] == MASKED_VALUE
    assert "SECRET-KEY" not in str(captured)
    response_item = captured["response_payload"]["response"]["body"]["items"]["item"][0]
    assert response_item["bidNtceNo"] == "REAL-001"


def test_capture_module_writes_sanitized_json_without_exposing_key(monkeypatch) -> None:  # noqa: ANN001
    written = {}

    monkeypatch.setattr(capture.Path, "mkdir", lambda self, parents, exist_ok: None)
    monkeypatch.setattr(capture.Path, "exists", lambda self: False)

    def fake_write_text(self, text, encoding):  # noqa: ANN001
        written["path"] = self
        written["text"] = text
        written["encoding"] = encoding
        return len(text)

    monkeypatch.setattr(capture.Path, "write_text", fake_write_text)

    capture.capture_real_response(
        capture_dir="data/captured/g2b",
        request_metadata={"params": {"serviceKey": "SECRET-KEY", "keyword": "AI"}},
        response_payload={"items": [{"bidNtceNo": "REAL-001"}]},
    )

    assert str(written["path"]).startswith("data\\captured\\g2b")
    assert written["encoding"] == "utf-8"
    assert "SECRET-KEY" not in written["text"]
    assert MASKED_VALUE in written["text"]
    assert "REAL-001" in written["text"]


def _real_request(confirm_real_api_call: bool = True) -> G2BSearchRequest:
    return G2BSearchRequest(
        mode=G2BSearchMode.REAL,
        keyword="AI",
        confirm_real_api_call=confirm_real_api_call,
    )


def _enabled_settings(**overrides) -> Settings:  # noqa: ANN001
    values = {
        "g2b_enable_real_api": True,
        "g2b_api_service_key": "SECRET-KEY",
        "g2b_list_endpoint_path": "/g2b/list",
    }
    values.update(overrides)
    return Settings(**values)


def _success_response() -> httpx.Response:
    return httpx.Response(
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
        request=httpx.Request("GET", "https://example.test/g2b/list"),
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
