from app.core.config import Settings
from app.integrations.g2b.readiness import build_real_readiness


def test_readiness_default_is_not_ready_and_does_not_call_real_api() -> None:
    readiness = build_real_readiness(Settings())

    assert readiness["ready_for_confirmed_real_smoke"] is False
    assert readiness["will_call_real_api"] is False
    assert readiness["service_key_configured"] is False
    assert readiness["service_key_value"] == "not_returned"
    assert readiness["endpoint_path_source"] == "missing"


def test_readiness_can_use_endpoint_preset_without_exposing_secret() -> None:
    readiness = build_real_readiness(
        Settings(
            g2b_enable_real_api=True,
            g2b_api_service_key="SECRET-KEY",
            g2b_endpoint_preset="bid_notice_service",
        )
    )

    assert readiness["ready_for_confirmed_real_smoke"] is True
    assert readiness["will_call_real_api"] is False
    assert readiness["endpoint_path_source"] == "preset"
    assert readiness["endpoint_preset"] == "bid_notice_service"
    assert "SECRET-KEY" not in str(readiness)
    assert readiness["recommended_first_request"] == {
        "mode": "real",
        "keyword": "AI",
        "page_no": 1,
        "num_rows": 3,
        "confirm_real_api_call": True,
    }


def test_readiness_marks_unknown_endpoint_preset_not_ready() -> None:
    readiness = build_real_readiness(
        Settings(
            g2b_enable_real_api=True,
            g2b_api_service_key="SECRET-KEY",
            g2b_endpoint_preset="unknown",
        )
    )

    assert readiness["ready_for_confirmed_real_smoke"] is False
    assert readiness["endpoint_path_source"] == "unknown_preset"
    assert "SECRET-KEY" not in str(readiness)
