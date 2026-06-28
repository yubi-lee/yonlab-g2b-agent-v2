from app.services.opportunity_decision import (
    build_action_plan,
    build_bid_priority,
    build_commercial_recommendation_report,
    build_decision_label,
    build_decision_reasons,
    build_go_no_go_recommendation,
    build_required_documents,
    build_risk_categories,
)


def test_decision_label_thresholds_and_risk_downgrade() -> None:
    assert build_decision_label({"score": 86, "risk_level": "low"}) == {
        "decision_label": "strong_recommend",
        "decision_label_ko": "적극 추천",
    }
    assert build_decision_label({"score": 68, "risk_level": "medium"}) == {
        "decision_label": "recommend",
        "decision_label_ko": "추천",
    }
    assert build_decision_label({"score": 52, "risk_level": "medium"}) == {
        "decision_label": "consider",
        "decision_label_ko": "검토",
    }
    assert build_decision_label({"score": 43, "risk_level": "high", "deadline": None}) == {
        "decision_label": "hold",
        "decision_label_ko": "보류",
    }
    assert build_decision_label({"score": 30, "risk_level": "low"}) == {
        "decision_label": "not_recommended",
        "decision_label_ko": "비추천",
    }
    assert build_decision_label({"score": 88, "risk_level": "high"}) == {
        "decision_label": "recommend",
        "decision_label_ko": "추천",
    }


def test_priority_and_go_no_go_are_decision_ready() -> None:
    p1 = {"score": 91, "risk_level": "low", "risks": []}
    p2 = {"score": 72, "risk_level": "medium", "risks": ["RFP 확인 필요"]}
    hold = {"score": 42, "risk_level": "high", "risks": ["실적 제한"]}

    assert build_bid_priority(p1) == "P1"
    assert build_go_no_go_recommendation(p1) == {
        "go_no_go_recommendation": "Go",
        "go_no_go_recommendation_ko": "대응 권장",
    }
    assert build_bid_priority(p2) == "P2"
    assert build_go_no_go_recommendation(p2) == {
        "go_no_go_recommendation": "Go after RFP review",
        "go_no_go_recommendation_ko": "RFP 확인 후 대응",
    }
    assert build_bid_priority(hold) == "Hold"
    assert build_go_no_go_recommendation(hold) == {
        "go_no_go_recommendation": "Hold",
        "go_no_go_recommendation_ko": "보류",
    }


def test_decision_reasons_action_plan_and_documents_are_commercial() -> None:
    item = {
        "title": "서울 AI 기반 행정지원 업무 자동화 시스템 구축",
        "agency": "서울특별시 산하기관",
        "budget": 85000000,
        "deadline": "2026-07-15",
        "score": 88,
        "risk_level": "low",
        "reasons": ["AI/SW 과업", "소기업 조건 유리"],
        "risks": [],
        "source_type": "fixture",
    }

    reasons = build_decision_reasons(item)
    action_plan = build_action_plan(item)
    documents = build_required_documents(item)

    assert 3 <= len(reasons) <= 5
    assert any("AI/SW" in reason for reason in reasons)
    assert any("예산" in reason for reason in reasons)
    assert set(action_plan) == {
        "today_action",
        "document_action",
        "business_action",
        "go_no_go_action",
    }
    assert "Go/No-Go" in action_plan["go_no_go_action"]
    assert {"name": "사업자등록증", "status": "required"} in [
        {"name": doc["name"], "status": doc["status"]} for doc in documents
    ]
    assert any(
        doc["name"] == "직접생산확인증명서" and doc["status"] == "check"
        for doc in documents
    )
    assert any(doc["name"] == "기술제안서" and doc["status"] == "required" for doc in documents)


def test_risk_categories_cover_deadline_eligibility_scope_budget_evidence_and_partner() -> None:
    item = {
        "score": 44,
        "risk_level": "high",
        "deadline": None,
        "budget": 25000000,
        "risks": [
            "최근 3년 유사 사업 수행 실적 제출 조건이 있습니다.",
            "서울 외 특정 지역 소재 업체 제한 가능성이 있습니다.",
            "상주 또는 전담 인력 투입 부담이 있을 수 있습니다.",
            "공동수급 불가 조건이 있습니다.",
        ],
    }

    categories = build_risk_categories(item)
    by_category = {entry["category"]: entry for entry in categories}

    assert set(by_category) == {
        "deadline_risk",
        "eligibility_risk",
        "scope_risk",
        "budget_risk",
        "evidence_risk",
        "consortium_risk",
    }
    assert by_category["deadline_risk"]["level"] == "medium"
    assert by_category["eligibility_risk"]["level"] == "high"
    assert by_category["evidence_risk"]["level"] == "high"
    assert by_category["consortium_risk"]["level"] == "high"


def test_commercial_report_contains_required_decision_sections() -> None:
    item = {
        "title": "서울 AI 기반 행정지원 업무 자동화 시스템 구축",
        "agency": "서울특별시 산하기관",
        "budget": 85000000,
        "deadline": "2026-07-15",
        "score": 88,
        "risk_level": "low",
        "reasons": ["AI/SW 과업"],
        "risks": [],
        "source_type": "fixture",
        "source_run_id": "demo",
    }

    markdown = build_commercial_recommendation_report(item)

    assert markdown.startswith("## YOnLab 맞춤 추천 공고:")
    assert "- 매칭 점수: 88점 / 100점" in markdown
    assert "- Priority: P1" in markdown
    assert "- Go/No-Go: 대응 권장" in markdown
    assert "- 핵심 정보:" in markdown
    assert "- 입찰 준비 전략:" in markdown
    assert "- 오늘 액션:" in markdown
    assert "- 제출 필요 서류:" in markdown
    assert "- 리스크 카테고리:" in markdown
    assert "- 권장 대응:" in markdown
