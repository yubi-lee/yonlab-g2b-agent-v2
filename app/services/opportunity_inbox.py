
from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Any

from app.integrations.g2b.fixtures import search_sample_g2b_notices
from app.integrations.g2b.normalizer import normalize_g2b_notice
from app.scoring.score_engine import score_notice
from app.services.daily_review_pack import (
    EMPTY_STATE_NEXT_ACTIONS,
    PRIORITY_LEGEND,
    build_source_mode_message,
)
from app.services.opportunity_decision import (
    build_commercial_decision_fields,
    build_commercial_recommendation_report,
)
from app.storage.repository import OperationsRepository

EMPTY_STATE_MESSAGE = (
    "No opportunity data yet. Run a fixture recommendation job or a controlled real run "
    "to populate saved commercial opportunities."
)
YONLAB_REQUIRED_DOCUMENTS = [
    "사업자등록증",
    "소프트웨어사업자 확인서",
    "소기업/소상공인 확인서",
    "초기창업기업 증빙",
    "기술 제안서 및 수행 계획서",
]
AI_SW_KEYWORDS = (
    "AI",
    "인공지능",
    "소프트웨어",
    "정보시스템",
    "클라우드",
    "시스템",
    "Agent",
    "Device Farm",
    "검증",
)


def build_opportunity_inbox(
    *,
    db_path: str | Path,
    limit: int = 20,
    grade: str | None = None,
    risk_level: str | None = None,
    keyword: str | None = None,
    source_type: str | None = None,
    sort: str = "score_desc",
) -> dict[str, Any]:
    db_file = Path(db_path)
    saved_items: list[dict[str, Any]] = []
    if db_file.is_file():
        repository = OperationsRepository(db_file)
        saved_items = _saved_opportunity_items(repository, limit=max(limit, 100))

    source_mode = "saved" if saved_items else "demo"
    items = saved_items or build_demo_opportunity_items(limit=max(limit, 5))
    filtered = _filter_items(
        items,
        grade=grade,
        risk_level=risk_level,
        keyword=keyword,
        source_type=source_type,
    )
    ordered = _sort_items(filtered, sort=sort)[:limit]
    return {
        "status": "success" if saved_items else "demo",
        "source_mode": source_mode,
        "source_mode_message": build_source_mode_message(
            source_mode,
            has_items=bool(ordered),
        ),
        "latest_run_id": _latest_run_id(ordered),
        "latest_run_created_at": _latest_run_created_at(ordered),
        "total_items": len(ordered),
        "available_items": len(items),
        "sort": sort,
        "filters": {
            "grade": grade,
            "risk_level": risk_level,
            "keyword": keyword,
            "source_type": source_type,
        },
        "empty_state_message": "" if saved_items else EMPTY_STATE_MESSAGE,
        "empty_state_next_actions": [] if ordered else list(EMPTY_STATE_NEXT_ACTIONS),
        "priority_legend": PRIORITY_LEGEND,
        "items": ordered,
        "service_key_exposed": False,
        "real_api_call_attempted": False,
    }


def get_opportunity_detail(
    *,
    db_path: str | Path,
    notice_id: str,
) -> dict[str, Any] | None:
    inbox = build_opportunity_inbox(db_path=db_path, limit=100)
    for item in inbox["items"]:
        if item["notice_id"] == notice_id:
            detail = dict(item)
            detail["markdown"] = build_yonlab_opportunity_report(item)
            detail["service_key_exposed"] = False
            detail["real_api_call_attempted"] = False
            return detail
    return None


def build_opportunity_report_response(
    *,
    db_path: str | Path,
    notice_id: str,
) -> dict[str, Any] | None:
    detail = get_opportunity_detail(db_path=db_path, notice_id=notice_id)
    if detail is None:
        return None
    return {
        "notice_id": detail["notice_id"],
        "title": detail["title"],
        "markdown": detail["markdown"],
        "content_type": "text/markdown; charset=utf-8",
        "source_type": detail["source_type"],
        "source_run_id": detail["source_run_id"],
        "decision_label": detail["decision_label"],
        "decision_label_ko": detail["decision_label_ko"],
        "bid_priority": detail["bid_priority"],
        "decision_reasons": detail["decision_reasons"],
        "action_plan": detail["action_plan"],
        "required_documents": detail["required_documents"],
        "required_documents_grouped": detail.get("required_documents_grouped") or {},
        "risk_categories": detail["risk_categories"],
        "go_no_go_recommendation": detail["go_no_go_recommendation"],
        "go_no_go_recommendation_ko": detail["go_no_go_recommendation_ko"],
        "service_key_exposed": False,
        "real_api_call_attempted": False,
    }


def build_demo_opportunity_items(limit: int = 5) -> list[dict[str, Any]]:
    raw_notices = search_sample_g2b_notices(keyword="AI", limit=limit)
    items = []
    for rank, raw_notice in enumerate(raw_notices, start=1):
        notice = normalize_g2b_notice(raw_notice)
        score = score_notice(notice)
        item = _base_item(
            notice_id=notice.notice_id or f"demo-{rank}",
            title=notice.title or "Demo opportunity",
            agency=notice.agency,
            budget=notice.budget_amount,
            deadline=notice.deadline,
            score=score.total_score,
            grade=score.recommendation_label,
            reasons=score.positive_reasons[:3],
            risks=[risk.message for risk in score.risks],
            source_run_id="demo_fixture",
            source_type="demo",
            created_at="demo",
            detail_url="",
            report_url="",
        )
        items.append(item)
    return _sort_items(items, sort="score_desc")[:limit]


def build_yonlab_opportunity_report(item: dict[str, Any]) -> str:
    return build_commercial_recommendation_report(item)


def _saved_opportunity_items(repository: OperationsRepository, limit: int) -> list[dict[str, Any]]:
    recommendations = repository.list_recommendations(limit=limit)
    runs: dict[str, dict[str, Any]] = {}
    items = []
    for rec in recommendations:
        run_id = str(rec.get("run_id") or "")
        if run_id not in runs:
            runs[run_id] = repository.get_run(run_id) or {}
        run = runs[run_id]
        source_type = _source_type_from_run(run)
        item = _base_item(
            notice_id=str(rec.get("notice_id") or ""),
            title=str(rec.get("title") or ""),
            agency=str(rec.get("agency") or ""),
            budget=rec.get("budget_amount"),
            deadline=rec.get("deadline"),
            score=int(rec.get("total_score") or 0),
            grade=str(rec.get("recommendation_label") or "unknown"),
            reasons=list(rec.get("top_reasons") or []),
            risks=list(rec.get("risk_summaries") or []),
            source_run_id=run_id,
            source_type=source_type,
            created_at=str(rec.get("created_at") or run.get("created_at") or ""),
            detail_url=str(rec.get("detail_url") or ""),
            report_url=(
                f"/ops/report-content/{run_id}/{rec.get('notice_id')}"
                if rec.get("report_path")
                else ""
            ),
        )
        items.append(item)
    return items


def _base_item(
    *,
    notice_id: str,
    title: str,
    agency: str,
    budget: Any,
    deadline: Any,
    score: int,
    grade: str,
    reasons: list[str],
    risks: list[str],
    source_run_id: str,
    source_type: str,
    created_at: str,
    detail_url: str,
    report_url: str,
) -> dict[str, Any]:
    display_risks = risks or ["확인된 주요 리스크 없음"]
    risk_level = _risk_level(score=score, risk_count=len(risks), deadline=deadline)
    fit_summary = _fit_summary(title=title, reasons=reasons, score=score)
    item = {
        "notice_id": notice_id,
        "title": title,
        "agency": agency,
        "budget": budget,
        "deadline": deadline,
        "score": score,
        "grade": grade,
        "risk_level": risk_level,
        "reasons": reasons,
        "risks": display_risks,
        "source_run_id": source_run_id,
        "source_type": source_type,
        "source_badges": _source_badges(source_type),
        "created_at": created_at,
        "detail_url": detail_url,
        "report_url": f"/ops/opportunity-report/{notice_id}",
        "saved_report_url": report_url,
        "fit_summary": fit_summary,
        "why_now": _why_now(deadline=deadline, score=score, source_type=source_type),
        "bid_strategy": _bid_strategy(title=title, reasons=reasons, score=score),
        "required_documents": _required_documents(title=title, reasons=reasons),
        "recommended_action": _recommended_action(score=score, risk_level=risk_level),
        "service_key_exposed": False,
    }
    item.update(build_commercial_decision_fields(item))
    return item


def _fit_summary(*, title: str, reasons: list[str], score: int) -> str:
    text = " ".join([title, *reasons]).casefold()
    if any(keyword.casefold() in text for keyword in AI_SW_KEYWORDS):
        return "YOnLab의 AI/SW, 클라우드 시스템, 검증 자동화 역량과 직접 관련된 공고입니다."
    if score >= 70:
        return "정량 점수가 높아 우선 검토할 만한 공고입니다."
    return "기본 조건은 확인되었지만 세부 과업과 자격 제한 검토가 필요합니다."


def _why_now(*, deadline: Any, score: int, source_type: str) -> str:
    deadline_date = _parse_deadline(deadline)
    if deadline_date:
        days_left = (deadline_date - date.today()).days
        if days_left < 0:
            return "마감일이 지났을 수 있어 후속 공고나 정정 공고 확인이 필요합니다."
        if days_left <= 7:
            return "마감이 임박해 즉시 제출 가능성과 필수 서류를 확인해야 합니다."
    if source_type == "real":
        return "실제 수집된 운영 데이터이므로 담당자 검토 우선순위에 올릴 수 있습니다."
    if score >= 75:
        return "YOnLab 적합도가 높아 내부 검토 회의 후보로 바로 올릴 수 있습니다."
    return "초기 선별 후보로 과업 범위와 참가 제한을 확인하세요."


def _bid_strategy(*, title: str, reasons: list[str], score: int) -> str:
    text = " ".join([title, *reasons]).casefold()
    if "ai" in text or "인공지능" in text:
        return "AI Agent, 온디바이스 AI, 원격 검증 경험을 중심으로 제안 차별성을 구성하세요."
    if "클라우드" in text or "시스템" in text:
        return "클라우드 운영 안정성, 시스템 개발 방법론, 유지보수 대응 체계를 강조하세요."
    if score >= 70:
        return "핵심 적합 사유를 제안서 첫 장에 배치하고 리스크 항목을 사전 확인하세요."
    return "요구 조건과 실적 제한을 먼저 확인한 뒤 컨소시엄 필요성을 판단하세요."


def _required_documents(*, title: str, reasons: list[str]) -> list[str]:
    documents = list(YONLAB_REQUIRED_DOCUMENTS)
    text = " ".join([title, *reasons])
    if "실적" in text:
        documents.append("최근 3년 유사 사업 수행 실적 증빙")
    if "클라우드" in text:
        documents.append("클라우드 시스템 구성 및 보안 운영 계획")
    return documents


def _recommended_action(*, score: int, risk_level: str) -> str:
    if score >= 80 and risk_level != "high":
        return "오늘 검토 회의 안건으로 올리고 제안 준비를 시작하세요."
    if score >= 65:
        return "자격 제한과 제출 서류를 확인한 뒤 진행 여부를 결정하세요."
    return "낮은 우선순위로 보류하고 유사 AI/SW 공고를 추가 탐색하세요."


def _risk_level(*, score: int, risk_count: int, deadline: Any) -> str:
    deadline_date = _parse_deadline(deadline)
    if deadline_date and (deadline_date - date.today()).days < 0:
        return "high"
    if risk_count >= 3 or score < 50:
        return "high"
    if risk_count >= 1 or score < 70:
        return "medium"
    return "low"


def _source_type_from_run(run: dict[str, Any]) -> str:
    mode = str(run.get("mode") or "fixture")
    if mode in {"real", "fixture", "synthetic", "safe_daily"}:
        return mode
    return "fixture"


def _source_badges(source_type: str) -> list[str]:
    if source_type == "real":
        return ["real", "operator-reviewed"]
    if source_type == "demo":
        return ["demo", "fixture-derived"]
    if source_type == "synthetic":
        return ["synthetic"]
    if source_type == "safe_daily":
        return ["safe daily", "no real API"]
    return ["fixture", "no real API"]


def _latest_run_id(items: list[dict[str, Any]]) -> str | None:
    for item in items:
        run_id = str(item.get("source_run_id") or "")
        if run_id:
            return run_id
    return None


def _latest_run_created_at(items: list[dict[str, Any]]) -> str | None:
    values = sorted(
        (
            str(item.get("created_at") or "")
            for item in items
            if str(item.get("created_at") or "")
        ),
        reverse=True,
    )
    return values[0] if values else None


def _filter_items(
    items: list[dict[str, Any]],
    *,
    grade: str | None,
    risk_level: str | None,
    keyword: str | None,
    source_type: str | None,
) -> list[dict[str, Any]]:
    result = items
    if grade:
        result = [item for item in result if str(item.get("grade")) == grade]
    if risk_level:
        result = [item for item in result if item.get("risk_level") == risk_level]
    if source_type:
        result = [item for item in result if item.get("source_type") == source_type]
    if keyword:
        needle = keyword.casefold()
        result = [
            item
            for item in result
            if needle in " ".join(
                str(value)
                for value in [
                    item.get("title"),
                    item.get("agency"),
                    item.get("fit_summary"),
                    *(item.get("reasons") or []),
                    *(item.get("risks") or []),
                ]
            ).casefold()
        ]
    return result


def _sort_items(items: list[dict[str, Any]], *, sort: str) -> list[dict[str, Any]]:
    if sort == "deadline_asc":
        return sorted(items, key=lambda item: (_parse_deadline(item.get("deadline")) or date.max))
    return sorted(items, key=lambda item: int(item.get("score") or 0), reverse=True)


def _parse_deadline(value: Any) -> date | None:
    if not value:
        return None
    text = str(value).replace(".", "-").replace("/", "-").strip()
    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(text[: len("2026-06-20 12:00:00")], fmt).date()
        except ValueError:
            continue
    return None


def _format_budget(value: Any) -> str:
    if value in (None, ""):
        return "미확인"
    try:
        return f"{int(value):,}원"
    except (TypeError, ValueError):
        return str(value)


def _markdown_list(values: list[str]) -> str:
    return "\n".join(f"  - {value}" for value in values if value) or "  - 확인 필요"
