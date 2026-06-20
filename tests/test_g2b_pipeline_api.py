from fastapi.testclient import TestClient

import app.api.routes as routes
from app.core.config import Settings
from app.main import app

client = TestClient(app)


def test_g2b_config_does_not_expose_service_key() -> None:
    response = client.get("/g2b/config")

    assert response.status_code == 200
    payload = response.json()
    assert payload["real_api_enabled"] is False
    assert payload["base_url_configured"] is True
    assert payload["service_key_configured"] is False
    assert payload["capture_real_responses"] is False
    assert payload["endpoint_preset"] is None
    assert payload["endpoint_path_source"] == "missing"
    assert "service_key" not in payload
    assert "G2B_API_SERVICE_KEY" not in str(payload)


def test_g2b_search_fixture_mode_returns_notices_without_service_key() -> None:
    response = client.post("/g2b/search", json={"mode": "fixture", "keyword": "AI"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["source"] == "fixture"
    assert len(payload["notices"]) >= 1


def test_g2b_search_fixture_keyword_filtering_returns_empty_result() -> None:
    response = client.post(
        "/g2b/search",
        json={"mode": "fixture", "keyword": "NO_SUCH_NOTICE_KEYWORD"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["notices"] == []
    assert "No fixture notices matched" in payload["message"]


def test_g2b_search_real_mode_is_blocked_by_default() -> None:
    response = client.post(
        "/g2b/search",
        json={"mode": "real", "keyword": "AI", "confirm_real_api_call": True},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is False
    assert payload["error_code"] == "real_api_disabled"
    assert "serviceKey" not in str(payload)


def test_g2b_search_real_mode_blocked_when_confirmation_missing(monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.setattr(
        routes,
        "get_settings",
        lambda: Settings(
            g2b_enable_real_api=True,
            g2b_api_service_key="SECRET-KEY",
            g2b_list_endpoint_path="/g2b/list",
        ),
    )

    response = client.post("/g2b/search", json={"mode": "real", "keyword": "AI"})

    payload = response.json()
    assert payload["ok"] is False
    assert payload["error_code"] == "real_api_confirmation_required"
    assert "SECRET-KEY" not in str(payload)


def test_g2b_search_real_mode_blocked_when_service_key_missing(monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.setattr(
        routes,
        "get_settings",
        lambda: Settings(
            g2b_enable_real_api=True,
            g2b_list_endpoint_path="/g2b/list",
        ),
    )

    response = client.post(
        "/g2b/search",
        json={"mode": "real", "keyword": "AI", "confirm_real_api_call": True},
    )

    payload = response.json()
    assert payload["ok"] is False
    assert payload["error_code"] == "service_key_missing"


def test_g2b_search_real_mode_blocked_when_endpoint_path_missing(monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.setattr(
        routes,
        "get_settings",
        lambda: Settings(
            g2b_enable_real_api=True,
            g2b_api_service_key="SECRET-KEY",
        ),
    )

    response = client.post(
        "/g2b/search",
        json={"mode": "real", "keyword": "AI", "confirm_real_api_call": True},
    )

    payload = response.json()
    assert payload["ok"] is False
    assert payload["error_code"] == "endpoint_path_missing"
    assert "SECRET-KEY" not in str(payload)


def test_g2b_search_real_mode_blocked_when_endpoint_preset_unknown(monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.setattr(
        routes,
        "get_settings",
        lambda: Settings(
            g2b_enable_real_api=True,
            g2b_api_service_key="SECRET-KEY",
            g2b_endpoint_preset="unknown",
        ),
    )

    response = client.post(
        "/g2b/search",
        json={"mode": "real", "keyword": "AI", "confirm_real_api_call": True},
    )

    payload = response.json()
    assert payload["ok"] is False
    assert payload["error_code"] == "endpoint_preset_unknown"
    assert "SECRET-KEY" not in str(payload)


def test_g2b_recommendations_real_mode_blocked_safely() -> None:
    response = client.post(
        "/g2b/recommendations",
        json={"mode": "real", "keyword": "AI", "confirm_real_api_call": True},
    )

    payload = response.json()
    assert payload["ok"] is False
    assert payload["error_code"] == "real_api_disabled"


def test_g2b_config_with_service_key_only_reports_boolean(monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.setattr(
        routes,
        "get_settings",
        lambda: Settings(g2b_api_service_key="SECRET-KEY"),
    )

    response = client.get("/g2b/config")

    payload = response.json()
    assert payload["service_key_configured"] is True
    assert "SECRET-KEY" not in str(payload)


def test_g2b_config_with_endpoint_preset_reports_safe_source(monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.setattr(
        routes,
        "get_settings",
        lambda: Settings(g2b_endpoint_preset="approved_bid_public_info_service"),
    )

    response = client.get("/g2b/config")

    payload = response.json()
    assert payload["endpoint_path_configured"] is True
    assert payload["endpoint_preset"] == "approved_bid_public_info_service"
    assert payload["endpoint_path_source"] == "preset"
    assert "serviceKey" not in str(payload)


def test_g2b_endpoint_presets_are_safe_to_inspect() -> None:
    response = client.get("/g2b/endpoint-presets")

    payload = response.json()
    assert any(
        preset["name"] == "approved_bid_public_info_service"
        and preset["path"] == "/1230000/ad/BidPublicInfoService"
        for preset in payload["presets"]
    )
    assert "serviceKey" not in str(payload)
    assert "SECRET-KEY" not in str(payload)


def test_g2b_real_readiness_default_is_safe() -> None:
    response = client.get("/g2b/real-readiness")

    payload = response.json()
    assert payload["ready"] is False
    assert payload["checks"]["real_api_enabled"] is False
    assert payload["checks"]["service_key_configured"] is False
    assert "G2B_API_SERVICE_KEY" in payload["missing"]
    assert "Set G2B_LIST_ENDPOINT_PATH=/1230000/ad/BidPublicInfoService" in str(payload)
    assert "SECRET-KEY" not in str(payload)
    assert "serviceKey" not in str(payload)


def test_g2b_recommendations_fixture_compact_response() -> None:
    response = client.post(
        "/g2b/recommendations",
        json={"mode": "fixture", "keyword": "AI", "include_reports": False},
    )

    assert response.status_code == 200
    payload = response.json()
    recommendations = payload["recommendations"]
    assert payload["ok"] is True
    assert payload["include_reports"] is False
    assert len(recommendations) >= 1
    assert "total_score" in recommendations[0]
    assert "report" not in recommendations[0]
    scores = [item["total_score"] for item in recommendations]
    assert scores == sorted(scores, reverse=True)


def test_g2b_recommendations_fixture_full_report_response() -> None:
    response = client.post(
        "/g2b/recommendations",
        json={"mode": "fixture", "keyword": "AI", "include_reports": True},
    )

    assert response.status_code == 200
    first = response.json()["recommendations"][0]
    assert "normalized_notice" in first
    assert "score" in first
    assert "report" in first
    assert "## 🎯 와이온랩 맞춤 추천 공고" in first["report"]["markdown"]
