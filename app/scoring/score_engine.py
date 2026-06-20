from app.domain.bid_notice import BidNotice
from app.domain.recommendation import (
    RECOMMENDATION_LEVEL_LABELS,
    RecommendationLevel,
    RecommendationScore,
    RiskSeverity,
)
from app.domain.yonlab_profile import YOnLabProfile, default_yonlab_profile
from app.scoring.eligibility import evaluate_eligibility
from app.scoring.risk_analyzer import analyze_risks


def score_notice(
    notice: BidNotice,
    profile: YOnLabProfile | None = None,
) -> RecommendationScore:
    profile = profile or default_yonlab_profile()
    eligibility = evaluate_eligibility(notice, profile)
    risks = analyze_risks(notice)
    text = notice.searchable_text()

    breakdown = {
        "required_qualification_fit": _required_qualification_score(text),
        "technical_fit": _technical_fit_score(text, profile),
        "company_condition_fit": _company_condition_score(text),
        "budget_contract_fit": _budget_contract_score(notice, text),
        "region_fit": _region_score(notice, text),
        "strategic_value": _strategic_value_score(text),
    }
    risk_penalty = min(20, sum(_risk_penalty(risk.severity) for risk in risks))
    total_score = max(0, min(100, sum(breakdown.values()) - risk_penalty))
    breakdown["risk_penalty"] = -risk_penalty

    level = _recommendation_level(total_score)
    return RecommendationScore(
        total_score=total_score,
        recommendation_level=level,
        recommendation_label=RECOMMENDATION_LEVEL_LABELS[level],
        positive_reasons=eligibility.positive_reasons or _fallback_reasons(total_score),
        risks=risks,
        score_breakdown=breakdown,
        eligibility=eligibility,
    )


def _required_qualification_score(text: str) -> int:
    if _has_any(text, ("소프트웨어사업자", "sw사업자", "컴퓨터관련서비스사업", "패키지소프트웨어")):
        return 25
    if _has_any(text, ("소프트웨어", "정보시스템", "클라우드", "ai", "인공지능")):
        return 17
    if _has_any(text, ("제조사", "총판", "대리점")):
        return 4
    return 10


def _technical_fit_score(text: str, profile: YOnLabProfile) -> int:
    matched_categories = sum(
        1 for category in profile.procurement_categories if category.casefold() in text
    )
    matched_keywords = sum(
        1 for keyword in profile.technical_keywords if keyword.casefold() in text
    )
    if matched_categories >= 1 and matched_keywords >= 1:
        return 25
    if matched_categories >= 1:
        return 22
    if matched_keywords >= 1:
        return 20
    if _has_any(text, ("ai", "인공지능", "정보시스템", "소프트웨어", "클라우드")):
        return 17
    if _has_any(text, ("하드웨어", "전산장비", "pc 납품")):
        return 3
    return 8


def _company_condition_score(text: str) -> int:
    score = 6
    if _has_any(text, ("소기업", "소상공인")):
        score += 8
    if _has_any(text, ("창업기업", "초기창업기업")):
        score += 6
    return min(score, 20)


def _budget_contract_score(notice: BidNotice, text: str) -> int:
    if _has_any(text, ("물품 구매", "물품구매", "단순 납품")):
        return 3
    if notice.budget_amount is None:
        return 6
    if notice.budget_amount <= 100_000_000:
        return 10
    if notice.budget_amount <= 300_000_000:
        return 7
    return 4


def _region_score(notice: BidNotice, text: str) -> int:
    region_text = f"{notice.region} {text}".casefold()
    if _has_any(region_text, ("서울", "전국", "수도권")):
        return 10
    if notice.region:
        return 1
    return 5


def _strategic_value_score(text: str) -> int:
    if _has_any(text, ("온디바이스", "npu", "device farm", "ai agent", "로봇 ai", "검증 플랫폼")):
        return 10
    if _has_any(text, ("ai", "인공지능", "클라우드", "정보시스템")):
        return 7
    if _has_any(text, ("하드웨어", "전산장비", "pc 납품")):
        return 1
    return 4


def _risk_penalty(severity: RiskSeverity) -> int:
    if severity == RiskSeverity.HIGH:
        return 8
    if severity == RiskSeverity.MEDIUM:
        return 5
    return 2


def _recommendation_level(score: int) -> RecommendationLevel:
    if score >= 85:
        return RecommendationLevel.STRONG_RECOMMEND
    if score >= 70:
        return RecommendationLevel.RECOMMEND
    if score >= 50:
        return RecommendationLevel.CONSIDER
    return RecommendationLevel.NOT_RECOMMENDED


def _fallback_reasons(total_score: int) -> list[str]:
    if total_score >= 70:
        return ["와이온랩 기준에서 검토 가치가 있는 공고입니다."]
    return ["와이온랩 핵심 기술·자격과의 직접 적합성이 제한적입니다."]


def _has_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(term.casefold() in text for term in terms)
