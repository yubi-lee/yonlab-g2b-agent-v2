from typing import Any

from fastapi import APIRouter, Body

from app.core.config import get_settings
from app.domain.bid_notice import BidNotice
from app.domain.recommendation import (
    DemoRecommendation,
    DemoRecommendationResponse,
    FixtureNoticeResponse,
    NormalizedNoticeResponse,
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
def normalize_notice(raw_notice: dict[str, Any]) -> NormalizedNoticeResponse:
    return NormalizedNoticeResponse(notice=normalize_g2b_notice(raw_notice))


@router.post("/recommendations/score", response_model=RecommendationScore)
def score_recommendation(raw_notice: dict[str, Any]) -> RecommendationScore:
    notice = normalize_g2b_notice(raw_notice)
    return score_notice(notice)


@router.post("/recommendations/report", response_model=RecommendationReport)
def recommendation_report(raw_notice: dict[str, Any]) -> RecommendationReport:
    notice = normalize_g2b_notice(raw_notice)
    score = score_notice(notice)
    return generate_markdown_report(notice, score)


@router.post("/demo/recommendations", response_model=DemoRecommendationResponse)
def demo_recommendations(payload: Any = OPTIONAL_JSON_BODY) -> DemoRecommendationResponse:
    raw_notices = _demo_input_notices(payload)
    scored = []
    for raw_notice in raw_notices:
        notice = normalize_g2b_notice(raw_notice)
        score = score_notice(notice)
        report = generate_markdown_report(notice, score)
        scored.append((notice, score, report))

    ranked = sorted(scored, key=lambda item: item[1].total_score, reverse=True)
    recommendations = [
        DemoRecommendation(rank=index, normalized_notice=notice, score=score, report=report)
        for index, (notice, score, report) in enumerate(ranked, start=1)
    ]
    return DemoRecommendationResponse(
        recommendations=recommendations,
        ranked_order=[item.normalized_notice.notice_id for item in recommendations],
        source_count=len(raw_notices),
    )


def _demo_input_notices(payload: Any) -> list[dict[str, Any] | BidNotice]:
    if payload in (None, {}, []):
        return load_sample_g2b_notices()
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and isinstance(payload.get("notices"), list):
        return payload["notices"]
    if isinstance(payload, dict):
        return [payload]
    return load_sample_g2b_notices()
