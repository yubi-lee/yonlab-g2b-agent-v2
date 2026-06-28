from datetime import date, datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Body, HTTPException
from fastapi.responses import FileResponse, RedirectResponse, Response

from app.core.config import get_settings
from app.domain.bid_notice import BidNotice
from app.domain.document_analysis import (
    AttachmentAnalysisPlanResponse,
    AttachmentDownloadPlanRequest,
    AttachmentDownloadPlanResponse,
    DocumentRiskAnalysisRequest,
    DocumentRiskAnalysisResult,
    PdfAnalysisCandidatesRequest,
    PdfAnalysisCandidatesResponse,
    PdfTextAnalysisRequest,
    PdfTextAnalysisResponse,
    PdfTextExtractionResult,
)
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
from app.domain.request_validation import meaningful_notice_payload
from app.domain.search import (
    G2BConfigResponse,
    G2BEndpointPresetListResponse,
    G2BEndpointPresetResponse,
    G2BRealReadinessResponse,
    G2BRecommendationRequest,
    G2BRecommendationResponse,
    G2BSearchMode,
    G2BSearchRequest,
    G2BSearchResponse,
)
from app.domain.yonlab_profile import YOnLabProfile, default_yonlab_profile
from app.integrations.g2b.client import G2BClient
from app.integrations.g2b.detail_queue import build_detail_analysis_queue
from app.integrations.g2b.errors import G2BClientError
from app.integrations.g2b.fixtures import load_sample_g2b_notices, search_sample_g2b_notices
from app.integrations.g2b.normalizer import normalize_g2b_notice
from app.integrations.g2b.presets import list_endpoint_presets, resolve_endpoint_path
from app.integrations.g2b.readiness import build_real_readiness
from app.reports.markdown_report import generate_markdown_report
from app.scoring.score_engine import score_notice
from app.services.attachment_analysis_planner import (
    build_attachment_analysis_plan_items,
    build_pdf_analysis_candidates,
)
from app.services.attachment_downloader import build_attachment_download_plan_items
from app.services.daily_review_pack import (
    build_daily_review_csv,
    build_daily_review_pack,
)
from app.services.document_risk_analyzer import analyze_document_risks
from app.services.local_ops_package import build_local_ops_package_info
from app.services.operations_runner import run_recommendation_job
from app.services.opportunity_inbox import (
    build_opportunity_inbox,
    build_opportunity_report_response,
    get_opportunity_detail,
)
from app.services.pdf_text_extractor import extract_pdf_text_from_file
from app.services.real_ops_readiness import build_real_ops_readiness
from app.storage.models import OperationsRunSummary, OpsRunRequest
from app.storage.repository import OperationsRepository

router = APIRouter()
UI_TEMPLATE_PATH = Path(__file__).resolve().parents[1] / "ui" / "templates" / "dashboard.html"
NOTICE_REQUEST_BODY = Body(
    openapi_examples={
        "yonlab_ai_notice": {
            "summary": "Score a real-looking AI/SW notice",
            "value": {
                "raw_notice": {
                    "bidNtceNo": "G2B-SWAGGER-001",
                    "bidNtceNm": "서울 AI 소프트웨어 검증 플랫폼 구축",
                    "dminsttNm": "서울특별시 산하기관",
                    "asignBdgtAmt": "55000000",
                    "bidClseDt": "2026-07-20",
                    "regionRestriction": "서울특별시",
                    "qualification": "소프트웨어사업자, 소기업 또는 소상공인, 창업기업 우대",
                    "descriptionText": "AI Agent 기반 정보시스템개발서비스 및 클라우드 시스템 구축",
                }
            },
        }
    }
)
DEMO_RECOMMENDATIONS_BODY = Body(
    default=None,
    openapi_examples={
        "fixture_recommendations": {
            "summary": "Use local fixture notices",
            "value": {"include_reports": False, "limit": 5},
        },
        "fixture_full_reports": {
            "summary": "Use local fixture notices with full reports",
            "value": {"include_reports": True, "limit": 3},
        },
        "custom_notice_recommendations": {
            "summary": "Rank custom AI/SW notices",
            "value": {
                "include_reports": True,
                "limit": 1,
                "notices": [
                    {
                        "bidNtceNo": "G2B-SWAGGER-001",
                        "bidNtceNm": "서울 AI 소프트웨어 검증 플랫폼 구축",
                        "dminsttNm": "서울특별시 산하기관",
                        "asignBdgtAmt": "55000000",
                        "bidClseDt": "2026-07-20",
                        "regionRestriction": "서울특별시",
                        "qualification": "소프트웨어사업자, 소기업 또는 소상공인, 창업기업 우대",
                        "descriptionText": (
                            "AI Agent 기반 정보시스템개발서비스 및 클라우드 시스템 구축"
                        ),
                    }
                ],
            },
        },
    },
)
G2B_SEARCH_BODY = Body(
    openapi_examples={
        "fixture_search": {
            "summary": "Search local fixtures without real API access",
            "value": {
                "mode": "fixture",
                "keyword": "AI",
                "page_no": 1,
                "num_rows": 5,
                "active_only": False,
                "confirm_real_api_call": False,
            },
        }
    }
)
G2B_RECOMMENDATION_BODY = Body(
    openapi_examples={
        "fixture_recommendations": {
            "summary": "Rank local fixture notices",
            "value": {
                "mode": "fixture",
                "keyword": "AI",
                "page_no": 1,
                "num_rows": 5,
                "include_reports": False,
                "active_only": False,
                "confirm_real_api_call": False,
            },
        },
        "real_controlled_recommendations": {
            "summary": "Template for controlled real API recommendation smoke",
            "value": {
                "mode": "real",
                "keyword": "AI",
                "start_date": "2026-06-01",
                "end_date": "2026-06-20",
                "page_no": 1,
                "num_rows": 3,
                "active_only": False,
                "confirm_real_api_call": True,
                "include_reports": False,
            },
        },
        "real_active_only_recommendations": {
            "summary": "Template for controlled real API active-only recommendations",
            "value": {
                "mode": "real",
                "keyword": "AI",
                "start_date": "2026-06-01",
                "end_date": "2026-06-20",
                "page_no": 1,
                "num_rows": 3,
                "active_only": True,
                "confirm_real_api_call": True,
                "include_reports": False,
            },
        },
    }
)
DOCUMENT_RISK_ANALYSIS_BODY = Body(
    openapi_examples={
        "fixture_text": {
            "summary": "Analyze fixture-like RFP text",
            "value": {
                "source_name": "sample-rfp-text",
                "text": (
                    "본 사업은 AI 소프트웨어 개발 및 클라우드 시스템 구축이며 "
                    "최근 3년 유사 사업 수행실적과 소프트웨어사업자 확인서를 요구합니다. "
                    "공동수급불허 조건이고 기술평가 90점입니다."
                ),
                "include_positive_signals": True,
            },
        }
    }
)
PDF_CANDIDATES_BODY = Body(
    openapi_examples={
        "fixture_candidates": {
            "summary": "List fixture PDF candidates without downloading",
            "value": {
                "mode": "fixture",
                "keyword": "AI",
                "page_no": 1,
                "num_rows": 3,
                "confirm_real_api_call": False,
            },
        }
    }
)
PDF_TEXT_ANALYSIS_BODY = Body(
    openapi_examples={
        "local_pdf": {
            "summary": "Analyze an already-local PDF only",
            "value": {
                "file_path": "data/fixtures/documents/sample_rfp.pdf",
                "source_name": "sample_rfp.pdf",
                "confirm_pdf_analysis": True,
            },
        }
    }
)


@router.get("/health")
def health_check() -> dict[str, str]:
    settings = get_settings()
    return {
        "status": "ok",
        "app": settings.app_name,
    }


@router.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    return RedirectResponse(url="/ui")


@router.get("/ui", include_in_schema=False)
def operations_dashboard() -> FileResponse:
    return FileResponse(UI_TEMPLATE_PATH, media_type="text/html; charset=utf-8")


@router.get("/profile/yonlab", response_model=YOnLabProfile)
def get_yonlab_profile() -> YOnLabProfile:
    return default_yonlab_profile()


@router.get("/fixtures/g2b/notices", response_model=FixtureNoticeResponse)
def get_g2b_fixture_notices() -> FixtureNoticeResponse:
    return FixtureNoticeResponse(notices=load_sample_g2b_notices())


@router.get("/g2b/config", response_model=G2BConfigResponse)
def get_g2b_config() -> G2BConfigResponse:
    settings = get_settings()
    endpoint_path, endpoint_path_source = resolve_endpoint_path(settings)
    return G2BConfigResponse(
        real_api_enabled=settings.g2b_enable_real_api,
        base_url_configured=bool(settings.g2b_api_base_url),
        service_key_configured=bool(settings.g2b_api_service_key),
        default_num_rows=settings.g2b_default_num_rows,
        default_page_no=settings.g2b_default_page_no,
        endpoint_path_configured=bool(endpoint_path),
        endpoint_preset=settings.g2b_endpoint_preset or None,
        endpoint_path_source=endpoint_path_source,
        fixture_mode=settings.g2b_fixture_mode,
        capture_real_responses=settings.g2b_capture_real_responses,
    )


@router.get("/g2b/endpoint-presets", response_model=G2BEndpointPresetListResponse)
def get_g2b_endpoint_presets() -> G2BEndpointPresetListResponse:
    return G2BEndpointPresetListResponse(
        presets=[
            G2BEndpointPresetResponse(
                name=preset.name,
                path=preset.path,
                description=preset.description,
            )
            for preset in list_endpoint_presets()
        ],
        message="Verify the exact operation path in data.go.kr before a confirmed real call.",
    )


@router.get("/g2b/real-readiness", response_model=G2BRealReadinessResponse)
def get_g2b_real_readiness() -> G2BRealReadinessResponse:
    return G2BRealReadinessResponse(**build_real_readiness(get_settings()))


@router.get("/ops/package-info")
def get_ops_package_info() -> dict[str, object]:
    return build_local_ops_package_info(get_settings())


@router.get("/ops/real-readiness")
def get_ops_real_readiness() -> dict[str, Any]:
    return build_real_ops_readiness(get_settings())


@router.post("/g2b/document-risk-analysis", response_model=DocumentRiskAnalysisResult)
def document_risk_analysis(
    request: DocumentRiskAnalysisRequest = DOCUMENT_RISK_ANALYSIS_BODY,
) -> DocumentRiskAnalysisResult:
    return analyze_document_risks(
        request.text,
        source_name=request.source_name,
        include_positive_signals=request.include_positive_signals,
    )


@router.post("/g2b/search", response_model=G2BSearchResponse)
def search_g2b_notices(request: G2BSearchRequest = G2B_SEARCH_BODY) -> G2BSearchResponse:
    return _search_g2b_notices(request)


@router.post("/g2b/recommendations", response_model=G2BRecommendationResponse)
def g2b_recommendations(
    request: G2BRecommendationRequest = G2B_RECOMMENDATION_BODY,
) -> G2BRecommendationResponse:
    search_response = _search_g2b_notices(request)
    if not search_response.ok:
        return G2BRecommendationResponse(
            ok=False,
            mode=request.mode,
            source=search_response.source,
            include_reports=request.include_reports,
            recommendations=[],
            ranked_order=[],
            source_count=0,
            message=search_response.message,
            error_code=search_response.error_code,
            status_code=search_response.status_code,
            safe_endpoint_path=search_response.safe_endpoint_path,
            service_key_exposed=search_response.service_key_exposed,
        )

    scored = []
    for notice in search_response.notices:
        score = score_notice(notice)
        report = generate_markdown_report(notice, score)
        scored.append((notice, score, report))

    ranked = sorted(scored, key=lambda item: item[1].total_score, reverse=True)
    recommendations = _demo_recommendation_items(
        ranked,
        include_reports=request.include_reports,
    )
    return G2BRecommendationResponse(
        ok=True,
        mode=request.mode,
        source=search_response.source,
        include_reports=request.include_reports,
        recommendations=recommendations,
        ranked_order=[_demo_notice_id(item) for item in recommendations],
        detail_analysis_queue=search_response.detail_analysis_queue,
        source_count=search_response.raw_count,
        message=search_response.message,
        safe_endpoint_path=search_response.safe_endpoint_path,
        service_key_exposed=search_response.service_key_exposed,
    )


@router.post("/g2b/detail-links")
def g2b_detail_links(request: G2BSearchRequest = G2B_SEARCH_BODY) -> dict[str, Any]:
    search_response = _search_g2b_notices(request)
    queue = _detail_queue_from_response(search_response)
    return {
        "ok": search_response.ok,
        "mode": request.mode,
        "source": search_response.source,
        "links": [
            {
                "notice_id": item.notice_id,
                "title": item.title,
                "detail_url": item.detail_url,
                "notice_url": item.notice_url,
            }
            for item in queue
        ],
        "service_key_exposed": False,
    }


@router.post("/g2b/detail-analysis-queue")
def g2b_detail_analysis_queue(request: G2BSearchRequest = G2B_SEARCH_BODY) -> dict[str, Any]:
    search_response = _search_g2b_notices(request)
    return {
        "ok": search_response.ok,
        "mode": request.mode,
        "source": search_response.source,
        "detail_analysis_queue": [
            item.model_dump() for item in _detail_queue_from_response(search_response)
        ],
        "service_key_exposed": False,
    }


@router.post("/g2b/attachment-download-plan", response_model=AttachmentDownloadPlanResponse)
def g2b_attachment_download_plan(
    request: AttachmentDownloadPlanRequest = PDF_CANDIDATES_BODY,
) -> AttachmentDownloadPlanResponse:
    search_response = _search_g2b_notices(request)
    settings = get_settings()
    queue = _detail_queue_from_response(search_response)
    items = build_attachment_download_plan_items(
        queue,
        download_enabled=settings.g2b_enable_attachment_download,
        confirm_attachment_download=request.confirm_attachment_download,
    )
    return AttachmentDownloadPlanResponse(
        ok=search_response.ok,
        mode=request.mode,
        source=search_response.source,
        download_enabled=settings.g2b_enable_attachment_download,
        confirm_attachment_download=request.confirm_attachment_download,
        items=items,
        message="Attachment download plan generated; no files were downloaded.",
        service_key_exposed=False,
    )


@router.post("/g2b/attachment-analysis-plan", response_model=AttachmentAnalysisPlanResponse)
def g2b_attachment_analysis_plan(
    request: G2BSearchRequest = PDF_CANDIDATES_BODY,
) -> AttachmentAnalysisPlanResponse:
    search_response = _search_g2b_notices(request)
    queue = _detail_queue_from_response(search_response)
    items = build_attachment_analysis_plan_items(queue)
    return AttachmentAnalysisPlanResponse(
        ok=search_response.ok,
        mode=request.mode,
        source=search_response.source,
        items=items,
        pdf_candidates=build_pdf_analysis_candidates(queue),
        message="Attachment analysis plan generated; no files were downloaded.",
        service_key_exposed=False,
    )


@router.post("/g2b/pdf-analysis-candidates", response_model=PdfAnalysisCandidatesResponse)
def g2b_pdf_analysis_candidates(
    request: PdfAnalysisCandidatesRequest = PDF_CANDIDATES_BODY,
) -> PdfAnalysisCandidatesResponse:
    search_response = _search_g2b_notices(request)
    queue = _detail_queue_from_response(search_response)
    candidates = build_pdf_analysis_candidates(queue)
    return PdfAnalysisCandidatesResponse(
        ok=search_response.ok,
        mode=request.mode,
        source=search_response.source,
        candidates=candidates,
        source_count=len(queue),
        message="PDF candidates generated from attachment metadata; no files were downloaded.",
        service_key_exposed=False,
    )


@router.post("/g2b/pdf-text-analysis", response_model=PdfTextAnalysisResponse)
def g2b_pdf_text_analysis(
    request: PdfTextAnalysisRequest = PDF_TEXT_ANALYSIS_BODY,
) -> PdfTextAnalysisResponse:
    if not request.confirm_pdf_analysis:
        extraction = PdfTextExtractionResult(
            file_name=Path(request.file_path).name,
            source="local_file",
            extraction_ok=False,
            message="PDF text analysis requires confirm_pdf_analysis=true.",
        )
        return PdfTextAnalysisResponse(ok=False, extraction=extraction, message=extraction.message)

    settings = get_settings()
    if Path(request.file_path).suffix.casefold() != ".pdf":
        extraction = extract_pdf_text_from_file(
            request.file_path,
            max_bytes=settings.g2b_pdf_max_bytes,
        )
        return PdfTextAnalysisResponse(ok=False, extraction=extraction, message=extraction.message)

    if not settings.g2b_enable_pdf_text_extraction and not _is_fixture_document_path(
        request.file_path
    ):
        extraction = PdfTextExtractionResult(
            file_name=Path(request.file_path).name,
            source="local_file",
            extraction_ok=False,
            message="PDF text extraction is disabled by configuration.",
        )
        return PdfTextAnalysisResponse(ok=False, extraction=extraction, message=extraction.message)

    extraction = extract_pdf_text_from_file(
        request.file_path,
        max_bytes=settings.g2b_pdf_max_bytes,
    )
    risk_analysis = None
    if extraction.extraction_ok:
        risk_analysis = analyze_document_risks(
            extraction.text,
            source_name=request.source_name or extraction.file_name,
        )
    return PdfTextAnalysisResponse(
        ok=extraction.extraction_ok,
        extraction=extraction,
        risk_analysis=risk_analysis,
        message=extraction.message,
        service_key_exposed=False,
    )


@router.post("/notices/normalize", response_model=NormalizedNoticeResponse)
def normalize_notice(payload: NoticeRequest = NOTICE_REQUEST_BODY) -> NormalizedNoticeResponse:
    return NormalizedNoticeResponse(notice=normalize_g2b_notice(_notice_input(payload)))


@router.post("/recommendations/score", response_model=RecommendationScore)
def score_recommendation(payload: NoticeRequest = NOTICE_REQUEST_BODY) -> RecommendationScore:
    notice = normalize_g2b_notice(_notice_input(payload))
    return score_notice(notice)


@router.post("/recommendations/report", response_model=RecommendationReport)
def recommendation_report(payload: NoticeRequest = NOTICE_REQUEST_BODY) -> RecommendationReport:
    notice = normalize_g2b_notice(_notice_input(payload))
    score = score_notice(notice)
    return generate_markdown_report(notice, score)


@router.post("/demo/recommendations", response_model=DemoRecommendationResponse)
def demo_recommendations(
    payload: DemoRecommendationsRequest | None = DEMO_RECOMMENDATIONS_BODY,
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


@router.post("/ops/run-recommendations", response_model=OperationsRunSummary)
def ops_run_recommendations(request: OpsRunRequest | None = None) -> OperationsRunSummary:
    payload = request or OpsRunRequest()
    settings = get_settings()
    return run_recommendation_job(
        settings=settings,
        mode=payload.mode or settings.yonlab_default_run_mode,
        keyword=payload.keyword or settings.yonlab_default_keyword,
        start_date=payload.start_date,
        end_date=payload.end_date,
        page_no=payload.page_no,
        num_rows=payload.num_rows or settings.yonlab_default_num_rows,
        include_reports=payload.include_reports,
        active_only=payload.active_only,
        confirm_real_api_call=payload.confirm_real_api_call,
    )


@router.get("/ops/runs")
def ops_list_runs(limit: int = 20) -> dict[str, Any]:
    repository = OperationsRepository(get_settings().yonlab_storage_db_path)
    return {"runs": repository.list_runs(limit=limit)}


@router.get("/ops/runs/{run_id}")
def ops_get_run(run_id: str) -> dict[str, Any]:
    repository = OperationsRepository(get_settings().yonlab_storage_db_path)
    return repository.get_run_detail(run_id)


@router.get("/ops/recommendations")
def ops_list_recommendations(
    limit: int = 20,
    min_score: int | None = None,
    label: str | None = None,
    keyword: str | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    repository = OperationsRepository(get_settings().yonlab_storage_db_path)
    return {
        "recommendations": repository.list_recommendations(
            limit=limit,
            min_score=min_score,
            label=label,
            keyword=keyword,
            run_id=run_id,
        )
    }


@router.get("/ops/reports/{run_id}")
def ops_list_reports(run_id: str) -> dict[str, Any]:
    repository = OperationsRepository(get_settings().yonlab_storage_db_path)
    return {"reports": repository.list_reports(run_id)}


@router.get("/ops/quality-summary")
def ops_quality_summary() -> dict[str, Any]:
    settings = get_settings()
    if not Path(settings.yonlab_storage_db_path).is_file():
        return _empty_quality_summary()
    repository = OperationsRepository(settings.yonlab_storage_db_path)
    return repository.build_quality_summary()


@router.get("/ops/report-index")
def ops_report_index(limit: int = 20) -> dict[str, Any]:
    settings = get_settings()
    if not Path(settings.yonlab_storage_db_path).is_file():
        return _empty_report_index()

    repository = OperationsRepository(settings.yonlab_storage_db_path)
    reports = []
    for report in repository.list_report_index(limit=limit):
        report_path = _safe_report_path(str(report["report_path"]), settings.yonlab_report_dir)
        if report_path is None:
            continue
        reports.append(
            {
                "run_id": report["run_id"],
                "notice_id": report["notice_id"],
                "title": report["title"],
                "report_path": str(report_path),
                "created_at": report["created_at"],
                "mode": report["mode"],
                "source": report["source"],
                "keyword": report["keyword"],
                "query_label": report["query_label"],
                "total_items": report["total_items"],
                "recommendation_count": report["recommendation_count"],
                "recommended_count": report["recommended_count"],
                "average_score": report["average_score"],
                "score_min": report["score_min"],
                "score_max": report["score_max"],
                "matching_score": report["matching_score"],
                "recommendation_grade": report["recommendation_grade"],
                "quality_label": report["quality_label"],
                "warning_count": report["warning_count"],
                "run_warning_count": report["run_warning_count"],
                "error_count": report["error_count"],
                "report_metadata_reference": report["report_metadata_reference"],
                "report_content_url": (
                    f"/ops/report-content/{report['run_id']}/{report['notice_id']}"
                ),
            }
        )
    return {
        "status": "success" if reports else "empty",
        "report_count": len(reports),
        "total_items": len(reports),
        "latest_run_id": reports[0]["run_id"] if reports else None,
        "quality_label_distribution": _count_by_key(reports, "quality_label"),
        "warning_count": sum(int(report["warning_count"]) for report in reports),
        "error_count": sum(int(report["error_count"]) for report in reports),
        "reports": reports,
        "service_key_exposed": False,
    }


@router.get("/ops/report-content/{run_id}/{notice_id}")
def ops_report_content(run_id: str, notice_id: str) -> dict[str, str]:
    settings = get_settings()
    repository = OperationsRepository(settings.yonlab_storage_db_path)
    report = repository.get_report(run_id, notice_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found.")

    report_path = _safe_report_path(report["report_path"], settings.yonlab_report_dir)
    if report_path is None or not report_path.is_file():
        raise HTTPException(status_code=404, detail="Report not found.")

    return {
        "run_id": run_id,
        "notice_id": notice_id,
        "title": str(report["title"]),
        "markdown": report_path.read_text(encoding="utf-8"),
    }


@router.get("/ops/opportunity-inbox")
def ops_opportunity_inbox(
    limit: int = 20,
    grade: str | None = None,
    risk_level: str | None = None,
    keyword: str | None = None,
    source_type: str | None = None,
    sort: str = "score_desc",
) -> dict[str, Any]:
    settings = get_settings()
    return build_opportunity_inbox(
        db_path=settings.yonlab_storage_db_path,
        limit=limit,
        grade=grade,
        risk_level=risk_level,
        keyword=keyword,
        source_type=source_type,
        sort=sort,
    )


@router.get("/ops/daily-review-pack")
def ops_daily_review_pack() -> dict[str, Any]:
    settings = get_settings()
    inbox = build_opportunity_inbox(
        db_path=settings.yonlab_storage_db_path,
        limit=100,
        sort="score_desc",
    )
    pack = build_daily_review_pack(inbox.get("items") or [])
    if pack["status"] == "success" and inbox.get("status") == "demo":
        pack["status"] = "demo"
    pack["source_mode"] = inbox.get("source_mode") or pack["source_mode"]
    pack["service_key_exposed"] = False
    pack["real_api_call_attempted"] = False
    return pack


@router.get("/ops/daily-review-pack/markdown")
def ops_daily_review_pack_markdown() -> Response:
    pack = ops_daily_review_pack()
    return Response(
        content=str(pack.get("markdown_report") or ""),
        media_type="text/markdown; charset=utf-8",
    )


@router.get("/ops/daily-review-pack/csv")
def ops_daily_review_pack_csv() -> Response:
    pack = ops_daily_review_pack()
    return Response(
        content=build_daily_review_csv(pack),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="yonlab-daily-review-pack.csv"'},
    )


@router.get("/ops/opportunity-inbox/{notice_id}")
def ops_opportunity_detail(notice_id: str) -> dict[str, Any]:
    settings = get_settings()
    detail = get_opportunity_detail(
        db_path=settings.yonlab_storage_db_path,
        notice_id=notice_id,
    )
    if detail is None:
        raise HTTPException(status_code=404, detail="Opportunity not found.")
    return detail


@router.get("/ops/opportunity-report/{notice_id}")
def ops_opportunity_report(notice_id: str) -> dict[str, Any]:
    settings = get_settings()
    report = build_opportunity_report_response(
        db_path=settings.yonlab_storage_db_path,
        notice_id=notice_id,
    )
    if report is None:
        raise HTTPException(status_code=404, detail="Opportunity report not found.")
    return report


def _notice_input(payload: NoticeRequest) -> dict[str, Any] | BidNotice:
    if payload.notice is not None:
        return payload.notice
    if payload.raw_notice is not None:
        return payload.raw_notice
    return dict(payload.model_extra or {})


def _demo_input_notices(payload: DemoRecommendationsRequest) -> list[dict[str, Any] | BidNotice]:
    if not payload.notices:
        return load_sample_g2b_notices()
    valid_notices = [notice for notice in payload.notices if meaningful_notice_payload(notice)]
    if not valid_notices:
        return load_sample_g2b_notices()
    return valid_notices


def _detail_queue_from_response(search_response: G2BSearchResponse) -> list[Any]:
    if search_response.detail_analysis_queue:
        return search_response.detail_analysis_queue
    return build_detail_analysis_queue(search_response.notices)


def _safe_report_path(report_path: str, report_dir: str) -> Path | None:
    base_dir = Path(report_dir).resolve()
    candidate = Path(report_path)
    if not candidate.is_absolute():
        candidate = Path.cwd() / candidate
    resolved = candidate.resolve()
    try:
        resolved.relative_to(base_dir)
    except ValueError:
        return None
    return resolved


def _empty_quality_summary() -> dict[str, Any]:
    return {
        "total_runs": 0,
        "total_reports": 0,
        "real_report_count": 0,
        "total_recommendations": 0,
        "strong_recommend_count": 0,
        "recommend_count": 0,
        "consider_count": 0,
        "not_recommended_count": 0,
        "average_score": 0,
        "summary_status": "empty",
        "latest_run_id": None,
        "latest_run_created_at": None,
        "latest_run": None,
        "successful_run_count": 0,
        "failed_run_count": 0,
        "warning_count": 0,
        "error_count": 0,
        "real_run_count": 0,
        "fixture_run_count": 0,
        "real_mode_executed": False,
        "real_mode_status": "empty",
        "quality_label_distribution": {},
        "service_key_exposed": False,
    }


def _empty_report_index() -> dict[str, Any]:
    return {
        "status": "empty",
        "report_count": 0,
        "total_items": 0,
        "latest_run_id": None,
        "quality_label_distribution": {},
        "warning_count": 0,
        "error_count": 0,
        "reports": [],
        "service_key_exposed": False,
    }


def _count_by_key(items: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        value = str(item.get(key) or "unknown")
        counts[value] = counts.get(value, 0) + 1
    return counts


def _is_fixture_document_path(file_path: str) -> bool:
    normalized = Path(file_path).as_posix()
    return normalized.startswith("data/fixtures/documents/")


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


def _search_g2b_notices(request: G2BSearchRequest) -> G2BSearchResponse:
    if request.mode == G2BSearchMode.FIXTURE:
        raw_notices = search_sample_g2b_notices(
            keyword=request.keyword,
            region=request.region,
            business_type=request.business_type,
            limit=request.num_rows,
        )
        normalized = _filter_active_notices(
            [normalize_g2b_notice(notice) for notice in raw_notices],
            active_only=request.active_only is True,
        )
        message = "Fixture notices returned."
        if not normalized:
            message = "No fixture notices matched the search criteria."
        return G2BSearchResponse(
            ok=True,
            mode=request.mode,
            source="fixture",
            notices=normalized,
            raw_count=len(raw_notices),
            message=message,
        )

    settings = get_settings()
    endpoint_path, _ = resolve_endpoint_path(settings)
    try:
        raw_notices = G2BClient(settings).search(request)
    except G2BClientError as exc:
        return G2BSearchResponse(
            ok=False,
            mode=request.mode,
            source="real",
            notices=[],
            raw_count=0,
            message=str(exc),
            error_code=exc.code,
            status_code=exc.status_code,
            safe_endpoint_path=exc.safe_endpoint_path,
            service_key_exposed=exc.service_key_exposed,
        )

    active_only = request.active_only
    if active_only is None and isinstance(request, G2BRecommendationRequest):
        active_only = True
    normalized = _filter_active_notices(
        [normalize_g2b_notice(notice) for notice in raw_notices],
        active_only=active_only is True,
    )
    message = "Real G2B notices returned."
    if not normalized:
        message = "Real G2B response contained no notices."
    return G2BSearchResponse(
        ok=True,
        mode=request.mode,
        source="real",
        notices=normalized,
        detail_analysis_queue=build_detail_analysis_queue(normalized),
        raw_count=len(raw_notices),
        message=message,
        safe_endpoint_path=endpoint_path or None,
        service_key_exposed=False,
    )


def _filter_active_notices(
    notices: list[BidNotice],
    *,
    active_only: bool,
    today: date | None = None,
) -> list[BidNotice]:
    if not active_only:
        return notices

    today = today or date.today()
    active_notices = []
    for notice in notices:
        if not notice.deadline:
            active_notices.append(notice)
            continue
        parsed_deadline = _parse_deadline_date(notice.deadline)
        if parsed_deadline is None or parsed_deadline >= today:
            active_notices.append(notice)
    return active_notices


def _parse_deadline_date(deadline: str) -> date | None:
    normalized = deadline.replace(".", "-").replace("/", "-").strip()
    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(normalized[: len("2026-06-20 12:00:00")], fmt).date()
        except ValueError:
            continue
    return None
