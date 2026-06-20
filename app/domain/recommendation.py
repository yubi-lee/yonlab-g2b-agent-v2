from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from app.domain.bid_notice import BidNotice


class SignalKind(StrEnum):
    FAVORABLE = "favorable"
    RISK = "risk"
    ELIGIBLE = "eligible"


class FitLevel(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class RiskSeverity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class RecommendationLevel(StrEnum):
    STRONG_RECOMMEND = "strong_recommend"
    RECOMMEND = "recommend"
    CONSIDER = "consider"
    NOT_RECOMMENDED = "not_recommended"


RECOMMENDATION_LEVEL_LABELS: dict[RecommendationLevel, str] = {
    RecommendationLevel.STRONG_RECOMMEND: "적극 추천",
    RecommendationLevel.RECOMMEND: "추천",
    RecommendationLevel.CONSIDER: "조건부 검토",
    RecommendationLevel.NOT_RECOMMENDED: "비추천",
}


class EligibilitySignal(BaseModel):
    kind: SignalKind
    code: str
    message: str


class RiskItem(BaseModel):
    code: str
    severity: RiskSeverity
    message: str
    recommendation: str


class EligibilityResult(BaseModel):
    eligible: bool
    fit: FitLevel
    positive_reasons: list[str] = Field(default_factory=list)
    risk_codes: list[str] = Field(default_factory=list)
    signals: list[EligibilitySignal] = Field(default_factory=list)

    @property
    def favorable_signals(self) -> tuple[EligibilitySignal, ...]:
        return tuple(signal for signal in self.signals if signal.kind == SignalKind.FAVORABLE)

    @property
    def risk_signals(self) -> tuple[EligibilitySignal, ...]:
        return tuple(signal for signal in self.signals if signal.kind == SignalKind.RISK)

    @property
    def eligible_signals(self) -> tuple[EligibilitySignal, ...]:
        return tuple(signal for signal in self.signals if signal.kind == SignalKind.ELIGIBLE)


class RecommendationScore(BaseModel):
    total_score: int
    recommendation_level: RecommendationLevel
    recommendation_label: str
    positive_reasons: list[str] = Field(default_factory=list)
    risks: list[RiskItem] = Field(default_factory=list)
    score_breakdown: dict[str, int] = Field(default_factory=dict)
    eligibility: EligibilityResult


class RecommendationReport(BaseModel):
    notice_title: str
    score: RecommendationScore
    markdown: str


class DemoRecommendation(BaseModel):
    rank: int
    normalized_notice: BidNotice
    score: RecommendationScore
    report: RecommendationReport


class DemoRecommendationResponse(BaseModel):
    recommendations: list[DemoRecommendation]
    ranked_order: list[str]
    source_count: int


class NormalizedNoticeResponse(BaseModel):
    notice: BidNotice


class FixtureNoticeResponse(BaseModel):
    notices: list[dict[str, Any]]
