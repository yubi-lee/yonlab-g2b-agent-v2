from pathlib import Path

from app.core.config import Settings
from app.integrations.g2b.readiness import build_real_readiness

PROJECT_ENV_EXAMPLE = "G2B_API_SERVICE_KEY=\n"


def test_readiness_default_is_not_ready_and_does_not_call_real_api() -> None:
    readiness = build_real_readiness(Settings())

    assert readiness["ready"] is False
    assert readiness["checks"]["real_api_enabled"] is False
    assert readiness["checks"]["service_key_configured"] is False
    assert readiness["checks"]["endpoint_path_configured"] is False
    assert "G2B_ENABLE_REAL_API=true" in readiness["missing"]
    assert "G2B_API_SERVICE_KEY" in readiness["missing"]


def test_readiness_can_use_endpoint_preset_without_exposing_secret() -> None:
    readiness = build_real_readiness(
        Settings(
            g2b_enable_real_api=True,
            g2b_api_service_key="SECRET-KEY",
            g2b_endpoint_preset="servc_pps_search",
        )
    )

    assert readiness["ready"] is True
    assert readiness["checks"]["endpoint_path_configured"] is True
    assert readiness["missing"] == []
    assert "SECRET-KEY" not in str(readiness)
    assert (
        "Set G2B_LIST_ENDPOINT_PATH=/1230000/ad/BidPublicInfoService/"
        "getBidPblancListInfoServcPPSSrch" in str(readiness)
    )


def test_readiness_marks_unknown_endpoint_preset_not_ready() -> None:
    readiness = build_real_readiness(
        Settings(
            g2b_enable_real_api=True,
            g2b_api_service_key="SECRET-KEY",
            g2b_endpoint_preset="unknown",
        )
    )

    assert readiness["ready"] is False
    assert readiness["checks"]["endpoint_path_configured"] is False
    assert "SECRET-KEY" not in str(readiness)


def test_env_example_keeps_service_key_empty() -> None:
    content = (Path(__file__).resolve().parents[1] / ".env.example").read_text(
        encoding="utf-8"
    )

    assert PROJECT_ENV_EXAMPLE in content
    assert (
        "G2B_LIST_ENDPOINT_PATH=/1230000/ad/BidPublicInfoService/"
        "getBidPblancListInfoServcPPSSrch" in content
    )
