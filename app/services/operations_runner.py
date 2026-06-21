from datetime import datetime, timezone

from app.core.config import Settings
from app.domain.bid_notice import BidNotice
from app.domain.recommendation import RecommendationReport, RecommendationScore
from app.domain.search import G2BRecommendationRequest, G2BSearchMode
from app.integrations.g2b.client import G2BClient
from app.integrations.g2b.detail_queue import build_detail_analysis_queue
from app.integrations.g2b.errors import G2BClientError
from app.integrations.g2b.fixtures import search_sample_g2b_notices
from app.integrations.g2b.normalizer import normalize_g2b_notice
from app.reports.markdown_report import generate_markdown_report
from app.scoring.score_engine import score_notice
from app.services.report_persistence import (
    write_markdown_report,
    write_raw_recommendation_json,
)
from app.storage.models import (
    OperationsRunSummary,
    StoredRecommendation,
    StoredReport,
    StoredSearchRun,
)
from app.storage.repository import OperationsRepository


def run_recommendation_job(
    *,
    settings: Settings,
    mode: G2BSearchMode | str | None = None,
    keyword: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    page_no: int | None = None,
    num_rows: int | None = None,
    include_reports: bool = True,
    active_only: bool | None = None,
    confirm_real_api_call: bool = False,
) -> OperationsRunSummary:
    run_id = _new_run_id()
    created_at = _utc_now()
    request = G2BRecommendationRequest(
        mode=mode or settings.yonlab_default_run_mode,
        keyword=keyword or settings.yonlab_default_keyword,
        start_date=start_date,
        end_date=end_date,
        page_no=page_no or settings.g2b_default_page_no,
        num_rows=num_rows or settings.yonlab_default_num_rows,
        include_reports=include_reports,
        active_only=active_only,
        confirm_real_api_call=confirm_real_api_call,
    )
    repository = OperationsRepository(settings.yonlab_storage_db_path)

    try:
        notices, source_count, message = _search_notices(settings, request)
    except G2BClientError as exc:
        repository.save_search_run(
            StoredSearchRun(
                run_id=run_id,
                created_at=created_at,
                mode=request.mode.value,
                keyword=request.keyword,
                start_date=request.start_date,
                end_date=request.end_date,
                num_rows=request.num_rows,
                source_count=0,
                status="error",
                message=str(exc),
                error_code=exc.code,
                service_key_exposed=exc.service_key_exposed,
            )
        )
        return OperationsRunSummary(
            run_id=run_id,
            status="error",
            mode=request.mode.value,
            keyword=request.keyword,
            source_count=0,
            recommendation_count=0,
            report_count=0,
            message=str(exc),
            error_code=exc.code,
            service_key_exposed=exc.service_key_exposed,
        )

    scored = [_score_notice(notice) for notice in notices]
    ranked = sorted(scored, key=lambda item: item[1].total_score, reverse=True)
    detail_url_by_notice_id = {
        item.notice_id: item.detail_url for item in build_detail_analysis_queue(notices)
    }

    repository.save_search_run(
        StoredSearchRun(
            run_id=run_id,
            created_at=created_at,
            mode=request.mode.value,
            keyword=request.keyword,
            start_date=request.start_date,
            end_date=request.end_date,
            num_rows=request.num_rows,
            source_count=source_count,
            status="success",
            message=message,
            service_key_exposed=False,
        )
    )

    report_count = 0
    for rank, (notice, score, report) in enumerate(ranked, start=1):
        report_path = ""
        if include_reports:
            report_path = write_markdown_report(
                report_dir=settings.yonlab_report_dir,
                run_id=run_id,
                rank=rank,
                notice_id=notice.notice_id,
                markdown=report.markdown,
            )
            repository.save_report(
                StoredReport(
                    run_id=run_id,
                    notice_id=notice.notice_id,
                    title=notice.title,
                    report_path=report_path,
                    created_at=_utc_now(),
                )
            )
            report_count += 1

        raw_json_path = write_raw_recommendation_json(
            report_dir=settings.yonlab_report_dir,
            run_id=run_id,
            rank=rank,
            notice_id=notice.notice_id,
            payload={
                "notice": notice,
                "score": score,
                "report_path": report_path,
                "service_key_exposed": False,
            },
        )
        repository.save_recommendation(
            StoredRecommendation(
                run_id=run_id,
                rank=rank,
                notice_id=notice.notice_id,
                title=notice.title,
                agency=notice.agency,
                budget_amount=notice.budget_amount,
                deadline=notice.deadline,
                total_score=score.total_score,
                recommendation_label=score.recommendation_label,
                risk_count=len(score.risks),
                top_reasons=score.positive_reasons[:3],
                risk_summaries=[risk.message for risk in score.risks],
                detail_url=detail_url_by_notice_id.get(notice.notice_id, ""),
                report_path=report_path,
                raw_json_path=raw_json_path,
                created_at=_utc_now(),
            )
        )

    return OperationsRunSummary(
        run_id=run_id,
        status="success",
        mode=request.mode.value,
        keyword=request.keyword,
        source_count=source_count,
        recommendation_count=len(ranked),
        report_count=report_count,
        message=message,
        service_key_exposed=False,
    )


def _search_notices(
    settings: Settings,
    request: G2BRecommendationRequest,
) -> tuple[list[BidNotice], int, str]:
    if request.mode == G2BSearchMode.FIXTURE:
        raw_notices = search_sample_g2b_notices(
            keyword=request.keyword,
            limit=request.num_rows,
        )
        notices = [normalize_g2b_notice(notice) for notice in raw_notices]
        return notices, len(raw_notices), "Fixture operation run completed."

    if not settings.yonlab_auto_run_real_api:
        raise G2BClientError(
            "real_ops_disabled",
            "Real G2B operations runs are disabled by default.",
        )

    raw_notices = G2BClient(settings).search(request)
    notices = [normalize_g2b_notice(notice) for notice in raw_notices]
    return notices, len(raw_notices), "Real G2B operation run completed."


def _score_notice(notice: BidNotice) -> tuple[BidNotice, RecommendationScore, RecommendationReport]:
    score = score_notice(notice)
    report = generate_markdown_report(notice, score)
    return notice, score, report


def _new_run_id() -> str:
    return datetime.now(timezone.utc).strftime("run_%Y%m%d_%H%M%S_%f")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
