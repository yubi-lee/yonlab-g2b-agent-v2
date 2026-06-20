from typing import Any

from fastapi import APIRouter, Body

from app.core.config import get_settings
from app.domain.bid_notice import BidNotice
from app.domain.recommendation import (
    CompactDemoRecommendation,
    DemoRecommendation,
    DemoRecommendationResponse,
    DemoRecommendationsRequest,
    FixtureNoticeResponse,
    NormalizedNoticeResponse,
    NoticeRequest,
    RecommendationReport,
    RecommendationScore,
)
from app.domain.yonlab_profile import YOnLabProfile, default_yonlab_profile
from app.integrations.g2b.fixtures import load_sample_g2b_notices
from app.integrations.g2b.normalizer import normalize_g2b_notice
from app.reports.markdown_report import generate_markdown_report
from app.scoring.score_engine import score_notice

router = APIRouter()
OPTIONAL_JSON_BODY = Body(default=None)


@router.get("/health")
def health_check() -> dict[str, str]:
    settings = get_settings()
    return {
        "status": "ok",
        "app": settings.app_name,
    }


@router.get("/profile/yonlab", response_model=YOnLabProfile)
def get_yonlab_profile() -> YOnLabProfile:
    return default_yonlab_profile()


@router.get("/fixtures/g2b/notices", response_model=FixtureNoticeResponse)
def get_g2b_fixture_notices() -> FixtureNoticeResponse:
    return FixtureNoticeResponse(notices=load_sample_g2b_notices())


@router.post("/notices/normalize", response_model=NormalizedNoticeResponse)
def normalize_notice(payload: NoticeRequest) -> NormalizedNoticeResponse:
    return NormalizedNoticeResponse(notice=normalize_g2b_notice(_notice_input(payload)))


@router.post("/recommendations/score", response_model=RecommendationScore)
def score_recommendation(payload: NoticeRequest) -> RecommendationScore:
    notice = normalize_g2b_notice(_notice_input(payload))
    return score_notice(notice)


@router.post("/recommendations/report", response_model=RecommendationReport)
def recommendation_report(payload: NoticeRequest) -> RecommendationReport:
    notice = normalize_g2b_notice(_notice_input(payload))
    score = score_notice(notice)
    return generate_markdown_report(notice, score)


@router.post("/demo/recommendations", response_model=DemoRecommendationResponse)
def demo_recommendations(
    payload: DemoRecommendationsRequest | None = OPTIONAL_JSON_BODY,
) -> DemoRecommendationResponse:
    request = payload or DemoRecommendationsRequest()
    raw_notices = _demo_input_notices(request)
    scored = []
    for raw_notice in raw_notices:
        notice = normalize_g2b_notice(raw_notice)
        score = score_notice(notice)
        report = generate_markdown_report(notice, score)
        scored.append((notice, score, report))

    ranked = sorted(scored, key=lambda item: item[1].total_score, reverse=True)[: request.limit]
    recommendations = _demo_recommendation_items(ranked, include_reports=request.include_reports)
    return DemoRecommendationResponse(
        include_reports=request.include_reports,
        recommendations=recommendations,
        ranked_order=[_demo_notice_id(item) for item in recommendations],
        source_count=len(raw_notices),
    )


def _notice_input(payload: NoticeRequest) -> dict[str, Any] | BidNotice:
    if payload.notice is not None:
        return payload.notice
    if payload.raw_notice is not None:
        return payload.raw_notice
    return dict(payload.model_extra or {})


def _demo_input_notices(payload: DemoRecommendationsRequest) -> list[dict[str, Any] | BidNotice]:
    if not payload.notices:
        return load_sample_g2b_notices()
    return payload.notices


def _demo_recommendation_items(
    ranked: list[tuple[BidNotice, RecommendationScore, RecommendationReport]],
    include_reports: bool,
) -> list[DemoRecommendation | CompactDemoRecommendation]:
    if include_reports:
        return [
            DemoRecommendation(rank=index, normalized_notice=notice, score=score, report=report)
            for index, (notice, score, report) in enumerate(ranked, start=1)
        ]

    return [
        CompactDemoRecommendation(
            rank=index,
            notice_id=notice.notice_id,
            title=notice.title,
            agency=notice.agency,
            total_score=score.total_score,
            recommendation_label=score.recommendation_label,
            top_positive_reasons=score.positive_reasons[:3],
            risk_summaries=[risk.message for risk in score.risks],
        )
        for index, (notice, score, _report) in enumerate(ranked, start=1)
    ]


def _demo_notice_id(item: DemoRecommendation | CompactDemoRecommendation) -> str:
    if isinstance(item, DemoRecommendation):
        return item.normalized_notice.notice_id
    return item.notice_id
