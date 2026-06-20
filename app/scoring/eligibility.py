from app.domain.bid_notice import BidNotice
from app.domain.recommendation import EligibilityResult, EligibilitySignal, FitLevel, SignalKind
from app.domain.yonlab_profile import YOnLabProfile, default_yonlab_profile
from app.scoring.risk_analyzer import analyze_risks

AI_SW_TERMS = (
    "ai",
    "인공지능",
    "소프트웨어",
    "sw",
    "정보시스템",
    "시스템 개발",
    "클라우드",
    "시스템관리",
    "원격 검증",
    "device farm",
    "agent",
    "npu",
    "온디바이스",
)


def evaluate_eligibility(
    notice: BidNotice,
    profile: YOnLabProfile | None = None,
) -> EligibilityResult:
    profile = profile or default_yonlab_profile()
    text = notice.searchable_text()
    signals: list[EligibilitySignal] = []
    positive_reasons: list[str] = []

    if _has_any(text, ("소프트웨어사업자", "sw사업자", "소프트웨어 사업자")):
        _add_signal(
            signals,
            positive_reasons,
            SignalKind.ELIGIBLE,
            "sw_business_required",
            "소프트웨어사업자 요구 조건이 와이온랩 핵심 자격과 부합합니다.",
        )

    if _has_any(text, AI_SW_TERMS):
        _add_signal(
            signals,
            positive_reasons,
            SignalKind.FAVORABLE,
            "ai_sw_fit",
            "AI/SW/정보시스템 개발 과업으로 와이온랩 기술 방향과 부합합니다.",
        )

    if _has_any(text, ("소기업", "소상공인", "중소기업자간 경쟁")):
        _add_signal(
            signals,
            positive_reasons,
            SignalKind.FAVORABLE,
            "small_business",
            "소기업·소상공인 조건이 초기기업인 와이온랩에 유리합니다.",
        )

    if _has_any(text, ("창업기업", "초기창업기업", "창업 기업")):
        _add_signal(
            signals,
            positive_reasons,
            SignalKind.FAVORABLE,
            "startup_preference",
            "창업기업 우대 조건이 있어 제안 전략상 유리합니다.",
        )

    if _has_any(f"{notice.region} {text}".casefold(), ("서울", "서울특별시", "강남구")):
        _add_signal(
            signals,
            positive_reasons,
            SignalKind.FAVORABLE,
            "seoul_region",
            "서울 지역 조건은 와이온랩 소재지와 부합합니다.",
        )

    if _has_any(text, ("클라우드", "정보시스템개발", "시스템관리", "소프트웨어 개발")):
        _add_signal(
            signals,
            positive_reasons,
            SignalKind.FAVORABLE,
            "cloud_system_fit",
            "클라우드·시스템·소프트웨어 개발 역량을 활용할 수 있습니다.",
        )

    matched_categories = [
        category for category in profile.procurement_categories if category.casefold() in text
    ]
    if matched_categories:
        _add_signal(
            signals,
            positive_reasons,
            SignalKind.FAVORABLE,
            "procurement_category_match",
            f"와이온랩 등록 품목과 직접 일치합니다: {', '.join(matched_categories)}.",
        )

    risks = analyze_risks(notice)
    for risk in risks:
        signals.append(
            EligibilitySignal(kind=SignalKind.RISK, code=risk.code, message=risk.message)
        )
        alias = _legacy_risk_code(risk.code)
        if alias != risk.code:
            signals.append(
                EligibilitySignal(kind=SignalKind.RISK, code=alias, message=risk.message)
            )

    fit = _fit_level(signals)
    return EligibilityResult(
        eligible=bool(_signals_with_code(signals, "sw_business_required")),
        fit=fit,
        positive_reasons=positive_reasons,
        risk_codes=[risk.code for risk in risks],
        signals=signals,
    )


def _fit_level(signals: list[EligibilitySignal]) -> FitLevel:
    if _signals_with_code(signals, "hardware_only") or _signals_with_code(
        signals, "license_mismatch"
    ):
        return FitLevel.LOW
    positive_count = len(
        [signal for signal in signals if signal.kind in {SignalKind.ELIGIBLE, SignalKind.FAVORABLE}]
    )
    if positive_count >= 4:
        return FitLevel.HIGH
    if positive_count >= 1:
        return FitLevel.MEDIUM
    return FitLevel.LOW


def _add_signal(
    signals: list[EligibilitySignal],
    positive_reasons: list[str],
    kind: SignalKind,
    code: str,
    message: str,
) -> None:
    signals.append(EligibilitySignal(kind=kind, code=code, message=message))
    if kind in {SignalKind.ELIGIBLE, SignalKind.FAVORABLE}:
        positive_reasons.append(message)


def _has_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(term.casefold() in text for term in terms)


def _signals_with_code(signals: list[EligibilitySignal], code: str) -> list[EligibilitySignal]:
    return [signal for signal in signals if signal.code == code]


def _legacy_risk_code(code: str) -> str:
    aliases = {
        "non_seoul_region": "other_region_limit",
        "recent_performance_required": "three_year_performance_limit",
        "hardware_only": "hardware_delivery_low_fit",
    }
    return aliases.get(code, code)
