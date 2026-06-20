from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

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


class CompactDemoRecommendation(BaseModel):
    rank: int
    notice_id: str
    title: str
    agency: str
    total_score: int
    recommendation_label: str
    top_positive_reasons: list[str] = Field(default_factory=list)
    risk_summaries: list[str] = Field(default_factory=list)


class DemoRecommendationResponse(BaseModel):
    include_reports: bool
    recommendations: list[DemoRecommendation | CompactDemoRecommendation]
    ranked_order: list[str]
    source_count: int


class NormalizedNoticeResponse(BaseModel):
    notice: BidNotice


class FixtureNoticeResponse(BaseModel):
    notices: list[dict[str, Any]]


class NoticeRequest(BaseModel):
    model_config = ConfigDict(
        extra="allow",
        json_schema_extra={
            "examples": [
                {
                    "공고명": "서울 AI 소프트웨어 개발",
                    "수요기관": "테스트기관",
                    "추정가격": "55,000,000원",
                    "입찰마감일시": "2026-07-20",
                    "지역제한": "서울특별시",
                    "참가자격": "소프트웨어사업자, 소기업, 창업기업 우대",
                    "과업내용": "AI Agent 정보시스템개발서비스 클라우드 시스템 구축",
                }
            ]
        },
    )

    notice: BidNotice | None = Field(
        default=None,
        description="Already normalized notice. If omitted, extra raw fields are normalized.",
    )
    raw_notice: dict[str, Any] | None = Field(
        default=None,
        description="Raw G2B-like or Korean-field notice JSON.",
    )


class DemoRecommendationsRequest(BaseModel):
    include_reports: bool = Field(
        default=True,
        description="When false, return a compact ranked list without full reports.",
    )
    limit: int = Field(default=5, ge=1, le=50)
    notices: list[dict[str, Any]] | None = Field(
        default=None,
        description="Optional raw notices. If omitted, local G2B fixtures are used.",
    )
