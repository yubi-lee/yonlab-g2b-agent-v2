from __future__ import annotations

from datetime import date, datetime
from typing import Any

DECISION_LABELS_KO = {
    "strong_recommend": "적극 추천",
    "recommend": "추천",
    "consider": "검토",
    "hold": "보류",
    "not_recommended": "비추천",
}
GO_NO_GO_KO = {
    "Go": "대응 권장",
    "Go after RFP review": "RFP 확인 후 대응",
    "Review with partner": "협력사 검토 후 대응",
    "Hold": "보류",
    "No-Go": "비추천",
}
RISK_LABELS_KO = {
    "deadline_risk": "마감 리스크",
    "eligibility_risk": "참가자격 리스크",
    "scope_risk": "과업범위 리스크",
    "budget_risk": "예산 리스크",
    "evidence_risk": "실적/증빙 리스크",
    "consortium_risk": "공동수급 리스크",
}
BASE_REQUIRED_DOCUMENTS = [
    ("사업자등록증", "required", "기본 입찰 서류입니다."),
    ("중소기업/소상공인 확인서", "required", "소기업·소상공인 제한 또는 우대 확인에 필요합니다."),
    ("법인등기부등본", "required", "법인 자격 확인용 기본 서류입니다."),
    ("국세/지방세 완납증명서", "required", "납세 상태 확인용 기본 서류입니다."),
    ("4대보험 완납증명서", "check", "공고별 요구 여부를 확인합니다."),
    ("직접생산확인증명서", "check", "세부 품명과 참가자격에서 요구되는지 확인합니다."),
    ("소프트웨어사업자 신고확인서", "check", "SW사업자 요구 공고에서 필수로 전환됩니다."),
    ("가격제안서", "required", "투찰 및 가격 평가용 필수 서류입니다."),
    ("기술제안서", "required", "협상/기술평가 대응의 핵심 서류입니다."),
    ("보안서약서/청렴계약이행서약서", "required", "대부분 공공 입찰의 공통 제출 서류입니다."),
]


def build_decision_label(item: dict[str, Any]) -> dict[str, str]:
    score = _score(item)
    risk_level = _risk_level(item)
    deadline_missing = not item.get("deadline")

    if score >= 80:
        label = "strong_recommend"
    elif score >= 65:
        label = "recommend"
    elif score >= 45:
        label = "consider"
    elif score >= 35:
        label = "hold"
    else:
        label = "not_recommended"

    if risk_level == "high":
        if label == "strong_recommend":
            label = "recommend"
        elif label in {"recommend", "consider"}:
            label = "hold"
    if deadline_missing and label == "consider" and risk_level == "high":
        label = "hold"

    return {"decision_label": label, "decision_label_ko": DECISION_LABELS_KO[label]}


def build_bid_priority(item: dict[str, Any]) -> str:
    score = _score(item)
    risk_level = _risk_level(item)
    if risk_level == "high" and score < 65:
        return "Hold"
    if score >= 80 and risk_level != "high":
        return "P1"
    if score >= 65:
        return "P2" if risk_level != "high" else "P3"
    if score >= 45:
        return "P3"
    return "Hold"


def build_decision_reasons(item: dict[str, Any]) -> list[str]:
    text = _search_text(item)
    score = _score(item)
    risk_level = _risk_level(item)
    reasons: list[str] = []
    if _contains_any(text, ["ai", "인공지능", "소프트웨어", "정보시스템", "클라우드"]):
        reasons.append("AI/SW 과업이 와이온랩의 사업 영역과 일치합니다.")
    if _contains_any(text, ["정보시스템", "클라우드", "소프트웨어"]):
        reasons.append("정보시스템·클라우드·AI 소프트웨어 성격의 공고로 기술 적합성이 확인됩니다.")
    budget = _budget(item)
    if budget:
        reasons.append(f"예산 규모 {budget:,}원은 초기 검토와 제안 준비 가능 범위입니다.")
    if _deadline_days(item) is None:
        reasons.append("마감일 정보가 불명확해 원문 공고 확인 전까지 검토 대상으로 분류합니다.")
    elif _deadline_days(item) <= 7:
        reasons.append("마감일이 임박해 즉시 Go/No-Go 판단이 필요합니다.")
    if risk_level == "high":
        reasons.append("참가자격·실적·지역 제한 리스크가 있어 단독 대응 가능성을 확인해야 합니다.")
    elif score >= 80:
        reasons.append("매칭 점수가 높아 내부 입찰 검토 회의에 우선 상정할 만합니다.")
    if not reasons:
        reasons.append("세부 과업 범위 확인 전까지 검토 후보로 유지합니다.")
    return reasons[:5]


def build_action_plan(item: dict[str, Any]) -> dict[str, str]:
    priority = build_bid_priority(item)
    go_no_go = build_go_no_go_recommendation(item)["go_no_go_recommendation_ko"]
    go_no_go_action = (
        f"30분 검토 후 Go/No-Go를 결정합니다. 현재 판단: {priority} / {go_no_go}."
    )
    return {
        "today_action": "오늘 원문 공고와 첨부 제안요청서를 확인합니다.",
        "document_action": "참가자격, 직접생산확인, 소기업·소상공인 제한 여부를 확인합니다.",
        "business_action": "유사 실적 또는 협력사 보완 필요성을 검토합니다.",
        "go_no_go_action": go_no_go_action,
    }


def build_required_documents(item: dict[str, Any]) -> list[dict[str, str]]:
    text = _search_text(item)
    documents = [
        {"name": name, "status": status, "reason": reason}
        for name, status, reason in BASE_REQUIRED_DOCUMENTS
    ]
    for document in documents:
        if document["name"] == "소프트웨어사업자 신고확인서" and _contains_any(
            text, ["소프트웨어사업자", "sw사업자", "소프트웨어"]
        ):
            document["status"] = "required"
            document["reason"] = "SW사업자 요구 가능성이 있어 필수로 준비합니다."
        if document["name"] == "직접생산확인증명서" and _contains_any(
            text, ["직접생산", "세부품명", "물품"]
        ):
            document["status"] = "required"
            document["reason"] = "공고 품명에서 직접생산 요구 여부를 확인해야 합니다."
    if _contains_any(text, ["실적", "최근 3년", "유사 사업"]):
        documents.append(
            {
                "name": "최근 3년 유사 사업 수행 실적 증빙",
                "status": "check",
                "reason": "실적 제한 또는 평가 증빙 요구 가능성이 있습니다.",
            }
        )
    if _contains_any(text, ["클라우드", "보안", "시스템"]):
        documents.append(
            {
                "name": "클라우드/보안 운영 계획",
                "status": "optional",
                "reason": "기술제안서 보강 자료로 활용할 수 있습니다.",
            }
        )
    return documents


def build_risk_categories(item: dict[str, Any]) -> list[dict[str, str]]:
    text = _search_text(item)
    days_left = _deadline_days(item)
    budget = _budget(item)
    categories = {
        "deadline_risk": "low",
        "eligibility_risk": "low",
        "scope_risk": "low",
        "budget_risk": "low",
        "evidence_risk": "low",
        "consortium_risk": "low",
    }

    if days_left is None or days_left <= 7:
        categories["deadline_risk"] = "medium"
    if days_left is not None and days_left < 0:
        categories["deadline_risk"] = "high"
    if _contains_any(text, ["지역", "제한", "소재", "참가자격"]):
        categories["eligibility_risk"] = "high"
    if _contains_any(text, ["상주", "전담", "운영", "복잡", "통합"]):
        categories["scope_risk"] = "medium"
    if budget is not None and budget < 30000000:
        categories["budget_risk"] = "medium"
    if _contains_any(text, ["실적", "최근 3년", "증빙", "유사 사업"]):
        categories["evidence_risk"] = "high"
    if _contains_any(text, ["공동수급", "컨소시엄", "협력사", "공동"]):
        categories["consortium_risk"] = "high"

    return [
        {
            "category": category,
            "category_ko": RISK_LABELS_KO[category],
            "level": level,
            "message": _risk_message(category, level),
        }
        for category, level in categories.items()
    ]


def build_go_no_go_recommendation(item: dict[str, Any]) -> dict[str, str]:
    score = _score(item)
    risk_level = _risk_level(item)
    text = _search_text(item)
    if score < 35:
        value = "No-Go"
    elif risk_level == "high" and _contains_any(text, ["공동수급", "협력사", "컨소시엄"]):
        value = "Review with partner"
    elif risk_level == "high" or score < 50:
        value = "Hold"
    elif risk_level == "medium" or score < 80:
        value = "Go after RFP review"
    else:
        value = "Go"
    return {"go_no_go_recommendation": value, "go_no_go_recommendation_ko": GO_NO_GO_KO[value]}


def build_commercial_decision_fields(item: dict[str, Any]) -> dict[str, Any]:
    fields: dict[str, Any] = {}
    fields.update(build_decision_label(item))
    fields["bid_priority"] = build_bid_priority(item)
    fields["decision_reasons"] = build_decision_reasons(item)
    fields["action_plan"] = build_action_plan(item)
    fields["required_documents"] = build_required_documents(item)
    fields["risk_categories"] = build_risk_categories(item)
    fields.update(build_go_no_go_recommendation(item))
    return fields


def build_commercial_recommendation_report(item: dict[str, Any]) -> str:
    enriched = {**item, **build_commercial_decision_fields(item)}
    budget = _format_budget(enriched.get("budget"))
    documents = _documents_markdown(enriched["required_documents"])
    risks = _risk_categories_markdown(enriched["risk_categories"])
    action_plan = enriched["action_plan"]
    reasons = _list_markdown(enriched["decision_reasons"])
    existing_risks = _list_markdown(enriched.get("risks") or ["확인된 주요 리스크 없음"])
    return "\n".join(
        [
            f"## YOnLab 맞춤 추천 공고: {enriched.get('title') or '제목 없음'}",
            "",
            f"- 매칭 점수: {_score(enriched)}점 / 100점",
            f"- Decision Label: {enriched['decision_label_ko']} ({enriched['decision_label']})",
            f"- Priority: {enriched['bid_priority']}",
            f"- Go/No-Go: {enriched['go_no_go_recommendation_ko']}",
            "- 추천 사유:",
            reasons,
            "- 입찰 정보:",
            f"  - 발주처: {enriched.get('agency') or '확인 필요'}",
            f"  - 예산: {budget}",
            f"  - 마감일: {enriched.get('deadline') or '확인 필요'}",
            (
                f"  - 출처: {enriched.get('source_type') or 'unknown'} / "
                f"{enriched.get('source_run_id') or 'none'}"
            ),
            f"- 오늘 액션: {action_plan['today_action']}",
            "- Action Plan:",
            f"  - 문서: {action_plan['document_action']}",
            f"  - 사업: {action_plan['business_action']}",
            f"  - Go/No-Go: {action_plan['go_no_go_action']}",
            "- 제출 필요 서류:",
            documents,
            "- 리스크 카테고리:",
            risks,
            "- 리스크:",
            existing_risks,
            f"- 권장 대응: {enriched.get('recommended_action') or action_plan['go_no_go_action']}",
            "",
        ]
    )


def _score(item: dict[str, Any]) -> int:
    return int(item.get("score") or item.get("total_score") or 0)


def _risk_level(item: dict[str, Any]) -> str:
    return str(item.get("risk_level") or "medium")


def _budget(item: dict[str, Any]) -> int | None:
    value = item.get("budget")
    if value is None:
        value = item.get("budget_amount")
    try:
        return int(value) if value not in {None, ""} else None
    except (TypeError, ValueError):
        return None


def _deadline_days(item: dict[str, Any]) -> int | None:
    deadline = _parse_date(item.get("deadline"))
    if deadline is None:
        return None
    return (deadline - date.today()).days


def _parse_date(value: Any) -> date | None:
    if not value:
        return None
    text = str(value).strip()
    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(text[: len(fmt)], fmt).date()
        except ValueError:
            continue
    return None


def _search_text(item: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in (
        "title",
        "agency",
        "grade",
        "decision_label_ko",
        "fit_summary",
        "why_now",
        "bid_strategy",
        "recommended_action",
    ):
        parts.append(str(item.get(key) or ""))
    for key in ("reasons", "risks", "required_documents"):
        values = item.get(key) or []
        if isinstance(values, list):
            for value in values:
                if isinstance(value, dict):
                    parts.extend(str(v) for v in value.values())
                else:
                    parts.append(str(value))
    return " ".join(parts).casefold()


def _contains_any(text: str, needles: list[str]) -> bool:
    return any(needle.casefold() in text for needle in needles)


def _risk_message(category: str, level: str) -> str:
    if level == "low":
        return "현재 자동 분석 기준에서 낮음으로 분류됩니다."
    return {
        "deadline_risk": "마감일 또는 준비 기간 확인이 필요합니다.",
        "eligibility_risk": "참가자격과 지역/업종 제한을 원문에서 확인해야 합니다.",
        "scope_risk": "상주, 운영, 전담 인력 등 과업 부담을 확인해야 합니다.",
        "budget_risk": "예산 대비 투입 범위와 수익성을 확인해야 합니다.",
        "evidence_risk": "최근 실적 또는 증빙자료 인정 범위를 확인해야 합니다.",
        "consortium_risk": "협력사 또는 공동수급 가능성을 확인해야 합니다.",
    }[category]


def _format_budget(value: Any) -> str:
    budget = _budget({"budget": value})
    if budget is None:
        return "확인 필요"
    return f"{budget:,}원"


def _list_markdown(values: list[str]) -> str:
    return "\n".join(f"  - {value}" for value in values)


def _documents_markdown(documents: list[dict[str, str]]) -> str:
    return "\n".join(
        f"  - [{document['status']}] {document['name']} - {document['reason']}"
        for document in documents
    )


def _risk_categories_markdown(categories: list[dict[str, str]]) -> str:
    return "\n".join(
        f"  - {entry['category_ko']}: {entry['level']} - {entry['message']}"
        for entry in categories
    )
