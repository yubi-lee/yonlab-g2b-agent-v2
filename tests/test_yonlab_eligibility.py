from app.domain.bid_notice import BidNotice
from app.domain.recommendation import FitLevel
from app.domain.yonlab_profile import default_yonlab_profile
from app.scoring.eligibility import evaluate_eligibility


def test_default_yonlab_profile_contains_required_baseline() -> None:
    profile = default_yonlab_profile()

    assert profile.company_name == "주식회사 와이온랩"
    assert profile.location == "서울특별시 강남구"
    assert profile.company_size == "소기업 / 소상공인"
    assert profile.startup_status == "초기창업기업"
    assert profile.core_qualification == "소프트웨어사업자"
    assert "인공지능소프트웨어" in profile.procurement_categories
    assert "AI Agent" in profile.technical_keywords


def test_sw_business_requirement_marks_yonlab_eligible() -> None:
    notice = BidNotice(
        title="AI 기반 원격 검증 시스템 개발",
        requirements=("소프트웨어사업자 등록 업체",),
    )

    result = evaluate_eligibility(notice)

    assert result.eligible is True
    assert _has_signal(result, "sw_business_required")


def test_small_business_startup_and_seoul_limits_are_favorable() -> None:
    notice = BidNotice(
        title="서울 AI Agent 서비스 구축",
        restrictions=("서울특별시 본점 소재지 업체", "소기업 또는 소상공인 제한"),
        preferences=("창업기업 우대",),
    )

    result = evaluate_eligibility(notice)

    assert _has_signal(result, "small_business")
    assert _has_signal(result, "startup_preference")
    assert _has_signal(result, "seoul_region")
    assert result.fit == FitLevel.HIGH


def test_other_region_limit_is_risk() -> None:
    notice = BidNotice(
        title="정보시스템 유지보수",
        restrictions=("부산광역시 본점 소재지 업체 지역 제한",),
    )

    result = evaluate_eligibility(notice)

    assert _has_signal(result, "other_region_limit")


def test_recent_three_year_performance_limit_is_risk() -> None:
    notice = BidNotice(
        title="클라우드 시스템 구축",
        requirements=("최근 3년 이내 유사 사업 수행실적 보유",),
    )

    result = evaluate_eligibility(notice)

    assert _has_signal(result, "three_year_performance_limit")


def test_ai_sw_related_notice_is_favorable() -> None:
    notice = BidNotice(
        title="온디바이스 AI 소프트웨어 개발",
        categories=("인공지능소프트웨어",),
    )

    result = evaluate_eligibility(notice)

    assert _has_signal(result, "ai_sw_fit")
    assert result.fit == FitLevel.MEDIUM


def test_simple_hardware_delivery_is_low_fit_risk() -> None:
    notice = BidNotice(title="사무용 PC 납품", description="단순 H/W 장비 납품")

    result = evaluate_eligibility(notice)

    assert _has_signal(result, "hardware_delivery_low_fit")
    assert result.fit == FitLevel.LOW


def _has_signal(result, code: str) -> bool:
    return any(signal.code == code for signal in result.signals)
