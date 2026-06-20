from app.domain.bid_notice import BidNotice
from app.domain.recommendation import EligibilityResult, EligibilitySignal, FitLevel, SignalKind
from app.domain.yonlab_profile import YOnLabProfile, default_yonlab_profile

SEOUL_TERMS = ("서울", "서울특별시")
OTHER_REGION_TERMS = (
    "부산",
    "대구",
    "인천",
    "광주",
    "대전",
    "울산",
    "세종",
    "경기",
    "강원",
    "충북",
    "충청북도",
    "충남",
    "충청남도",
    "전북",
    "전라북도",
    "전남",
    "전라남도",
    "경북",
    "경상북도",
    "경남",
    "경상남도",
    "제주",
)
AI_SW_TERMS = (
    "ai",
    "인공지능",
    "소프트웨어",
    "sw",
    "정보시스템",
    "클라우드",
    "시스템관리",
    "원격 검증",
    "device farm",
    "agent",
)
HARDWARE_TERMS = ("h/w", "hw", "하드웨어", "장비 납품", "pc 납품", "서버 납품")


def evaluate_eligibility(
    notice: BidNotice,
    profile: YOnLabProfile | None = None,
) -> EligibilityResult:
    profile = profile or default_yonlab_profile()
    text = notice.searchable_text()
    signals: list[EligibilitySignal] = []

    if _has_any(text, ("소프트웨어사업자", "sw사업자", "소프트웨어 사업자")):
        signals.append(
            EligibilitySignal(
                kind=SignalKind.ELIGIBLE,
                code="sw_business_required",
                message=f"{profile.core_qualification} 요구 공고입니다.",
            )
        )

    if _has_any(text, ("소기업", "소상공인")):
        signals.append(_favorable("small_business", "소기업/소상공인 제한 공고입니다."))

    if _has_any(text, ("창업기업", "초기창업기업", "창업 기업")):
        signals.append(_favorable("startup_preference", "창업기업 우대 공고입니다."))

    if _is_region_limited(text) and _has_any(text, SEOUL_TERMS):
        signals.append(_favorable("seoul_region", "서울 지역 제한 공고입니다."))

    if _is_region_limited(text) and _has_any(text, OTHER_REGION_TERMS):
        signals.append(
            EligibilitySignal(
                kind=SignalKind.RISK,
                code="other_region_limit",
                message="YOnLab 소재지와 다른 지역 제한 공고입니다.",
            )
        )

    if _has_any(text, ("최근 3년", "최근3년", "3년 이내")) and _has_any(text, ("실적", "수행실적")):
        signals.append(
            EligibilitySignal(
                kind=SignalKind.RISK,
                code="three_year_performance_limit",
                message="최근 3년 실적 제한이 있습니다.",
            )
        )

    ai_sw_fit = _has_any(text, AI_SW_TERMS) or any(
        category.casefold() in text for category in profile.procurement_categories
    )
    if ai_sw_fit:
        signals.append(_favorable("ai_sw_fit", "AI/SW 관련 공고입니다."))

    hardware_only = _has_any(text, HARDWARE_TERMS) and not ai_sw_fit
    if hardware_only:
        signals.append(
            EligibilitySignal(
                kind=SignalKind.RISK,
                code="hardware_delivery_low_fit",
                message="단순 H/W 납품 중심 공고로 적합도가 낮습니다.",
            )
        )

    fit = _fit_level(signals)
    return EligibilityResult(
        eligible=bool(_signals_with_code(signals, "sw_business_required")),
        fit=fit,
        signals=tuple(signals),
    )


def _fit_level(signals: list[EligibilitySignal]) -> FitLevel:
    if _signals_with_code(signals, "hardware_delivery_low_fit"):
        return FitLevel.LOW
    positive_count = len(
        [signal for signal in signals if signal.kind in {SignalKind.ELIGIBLE, SignalKind.FAVORABLE}]
    )
    if positive_count >= 2:
        return FitLevel.HIGH
    if any(signal.kind in {SignalKind.ELIGIBLE, SignalKind.FAVORABLE} for signal in signals):
        return FitLevel.MEDIUM
    return FitLevel.LOW


def _favorable(code: str, message: str) -> EligibilitySignal:
    return EligibilitySignal(kind=SignalKind.FAVORABLE, code=code, message=message)


def _has_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(term.casefold() in text for term in terms)


def _is_region_limited(text: str) -> bool:
    return _has_any(text, ("지역 제한", "지역제한", "소재지", "본점 소재지"))


def _signals_with_code(signals: list[EligibilitySignal], code: str) -> list[EligibilitySignal]:
    return [signal for signal in signals if signal.code == code]
