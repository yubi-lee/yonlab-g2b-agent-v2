from app.domain.bid_notice import BidNotice
from app.domain.recommendation import FitLevel
from app.integrations.g2b.fixtures import load_normalized_sample_notices
from app.scoring.eligibility import evaluate_eligibility


def test_high_fit_ai_software_notice_has_positive_signals() -> None:
    notice = load_normalized_sample_notices()[0]

    result = evaluate_eligibility(notice)

    assert result.eligible is True
    assert result.fit == FitLevel.HIGH
    assert _has_signal(result, "sw_business_required")
    assert _has_signal(result, "small_business")
    assert _has_signal(result, "startup_preference")
    assert _has_signal(result, "seoul_region")
    assert _has_signal(result, "ai_sw_fit")


def test_non_seoul_region_restriction_creates_risk_signal() -> None:
    notice = BidNotice(
        title="부산 AI 관제 시스템 구축",
        region="부산광역시 소재 업체",
        qualification_text="소프트웨어사업자",
        description="인공지능 정보시스템 개발",
        deadline="2026-07-30",
    )

    result = evaluate_eligibility(notice)

    assert _has_signal(result, "non_seoul_region")


def test_performance_requirement_creates_risk_signal() -> None:
    notice = BidNotice(
        title="클라우드 시스템 구축",
        qualification_text="최근 3년 유사 사업 수행실적 제출",
        description="소프트웨어사업자 클라우드 시스템 개발",
        deadline="2026-07-30",
    )

    result = evaluate_eligibility(notice)

    assert _has_signal(result, "recent_performance_required")


def test_hardware_only_notice_is_low_fit() -> None:
    notice = BidNotice(
        title="사무용 PC 납품",
        contract_type="물품 구매",
        description="단순 H/W 장비 납품",
        deadline="2026-07-30",
    )

    result = evaluate_eligibility(notice)

    assert result.fit == FitLevel.LOW
    assert _has_signal(result, "hardware_only")


def _has_signal(result, code: str) -> bool:
    return any(signal.code == code for signal in result.signals)
