from dataclasses import dataclass

from app.domain.document_analysis import DocumentRiskAnalysisResult, RiskKeywordHit


@dataclass(frozen=True)
class KeywordRule:
    code: str
    label: str
    severity: str
    terms: tuple[str, ...]
    recommendation: str


RISK_RULES: tuple[KeywordRule, ...] = (
    KeywordRule(
        "recent_performance_required",
        "Recent performance requirement",
        "high",
        ("최근 3년", "최근3년", "최근 수행실적", "recent performance"),
        "Check whether YOnLab can submit accepted public or private performance records.",
    ),
    KeywordRule(
        "single_contract_amount_required",
        "Single contract amount requirement",
        "high",
        ("단일 계약", "단일계약", "단일 실적", "single contract"),
        "Confirm the minimum amount and whether subcontract or consortium records are accepted.",
    ),
    KeywordRule(
        "similar_project_performance_required",
        "Similar project performance requirement",
        "high",
        ("유사 사업", "수행실적", "실적증명", "실적 증명", "similar project"),
        "Prepare proof of comparable AI/SW work before investing proposal effort.",
    ),
    KeywordRule(
        "industry_restriction_possible",
        "Industry participation restriction",
        "medium",
        ("업종제한", "입찰참가자격 제한", "입찰참가 제한", "industry restriction"),
        "Verify the exact registered business categories in G2B before bidding.",
    ),
    KeywordRule(
        "direct_production_required",
        "Direct production requirement",
        "medium",
        ("직접생산", "직접 생산", "direct production"),
        "Check whether a direct production certificate is required for this scope.",
    ),
    KeywordRule(
        "vendor_or_reseller_requirement",
        "Vendor or reseller proof requirement",
        "medium",
        ("제조사 공급확약", "대리점 증빙", "reseller", "vendor letter"),
        "Confirm whether YOnLab can provide vendor authorization documents.",
    ),
    KeywordRule(
        "joint_supply_not_allowed",
        "Joint supply not allowed",
        "high",
        (
            "공동수급불허",
            "공동계약 불가",
            "공동수급 불가",
            "공동수급 제한",
            "joint supply not allowed",
        ),
        "Treat this as a major risk if partner credentials are needed.",
    ),
    KeywordRule(
        "subcontract_restricted",
        "Subcontract restricted",
        "medium",
        ("하도급 불가", "하도급 금지", "하도급 제한", "subcontract prohibited"),
        "Review whether YOnLab can deliver the full scope directly.",
    ),
    KeywordRule(
        "onsite_or_dedicated_staff_required",
        "Onsite or dedicated staff requirement",
        "medium",
        ("상주", "전담인력", "전담 인력", "onsite", "dedicated staff"),
        "Estimate staffing burden and delivery schedule before bidding.",
    ),
    KeywordRule(
        "regional_restriction_possible",
        "Regional restriction possible",
        "medium",
        (
            "지역제한",
            "지역 제한",
            "소재 업체",
            "본점 소재지",
            "서울특별시",
            "부산광역시",
            "대구광역시",
            "경기도",
            "regional restriction",
        ),
        "Confirm whether YOnLab's Seoul location satisfies the restriction.",
    ),
    KeywordRule(
        "proposal_evaluation_required",
        "Proposal evaluation required",
        "medium",
        ("제안서 평가", "제안 평가", "협상에 의한 계약", "proposal evaluation"),
        "Prepare a proposal strategy around AI validation, delivery stability, and references.",
    ),
    KeywordRule(
        "high_technical_evaluation_weight",
        "High technical evaluation weight",
        "medium",
        ("기술평가 90", "기술 평가 90", "기술능력평가", "technical evaluation 90"),
        "Prioritize technical differentiation over price competition.",
    ),
    KeywordRule(
        "evaluation_criteria_present",
        "Evaluation criteria present",
        "low",
        ("기술평가", "가격평가", "정성평가", "정량평가", "평가 기준", "evaluation criteria"),
        "Map YOnLab evidence to each evaluation category.",
    ),
    KeywordRule(
        "security_pledge_required",
        "Security pledge required",
        "low",
        ("보안서약", "보안 서약", "security pledge"),
        "Prepare standard security pledge documents.",
    ),
    KeywordRule(
        "integrity_pledge_required",
        "Integrity pledge required",
        "low",
        ("청렴계약", "청렴 계약", "integrity pledge"),
        "Prepare integrity contract pledge documents.",
    ),
    KeywordRule(
        "privacy_requirement_possible",
        "Privacy requirement possible",
        "medium",
        ("개인정보", "개인 정보", "privacy"),
        "Check whether personal data processing safeguards are required.",
    ),
    KeywordRule(
        "copyright_requirement_possible",
        "Copyright requirement possible",
        "medium",
        ("저작권", "지식재산권", "copyright"),
        "Confirm ownership and license terms for deliverables.",
    ),
    KeywordRule(
        "software_business_certificate_required",
        "Software business certificate required",
        "low",
        ("소프트웨어사업자", "소프트웨어 사업자", "software business"),
        "Use YOnLab's software business registration as a core eligibility document.",
    ),
    KeywordRule(
        "small_business_certificate_required",
        "Small business certificate required",
        "low",
        ("중소기업확인", "소기업", "소상공인", "소상공인 확인", "small business"),
        "Prepare small business or microbusiness certificates.",
    ),
    KeywordRule(
        "startup_certificate_useful",
        "Startup certificate useful",
        "low",
        ("창업기업", "초기창업기업", "startup"),
        "Use startup status if it is an eligibility or preference factor.",
    ),
    KeywordRule(
        "g2b_registration_certificate_required",
        "G2B registration certificate required",
        "low",
        (
            "나라장터 경쟁입찰참가자격등록증",
            "경쟁입찰참가자격등록증",
            "g2b registration",
        ),
        "Prepare the G2B competitive bidding registration certificate.",
    ),
)

POSITIVE_RULES: tuple[KeywordRule, ...] = (
    KeywordRule(
        "ai_software_fit",
        "AI/SW fit",
        "low",
        ("AI", "인공지능", "NPU", "소프트웨어 개발", "AI 소프트웨어"),
        "Highlight YOnLab's AI software and agent capabilities.",
    ),
    KeywordRule(
        "cloud_system_fit",
        "Cloud system fit",
        "low",
        ("클라우드", "정보시스템", "cloud", "system"),
        "Position cloud system development and operations experience.",
    ),
    KeywordRule(
        "device_validation_fit",
        "Device validation fit",
        "low",
        ("Device Farm", "온디바이스", "검증", "NPU"),
        "Connect the requirement to YOnLab's device validation strengths.",
    ),
    KeywordRule(
        "platform_development_fit",
        "Platform development fit",
        "low",
        ("플랫폼", "platform"),
        "Frame the proposal around platform delivery and repeatable validation workflow.",
    ),
)


def analyze_document_risks(
    text: str,
    *,
    source_name: str,
    include_positive_signals: bool = True,
) -> DocumentRiskAnalysisResult:
    risk_hits = [_hit for rule in RISK_RULES if (_hit := _build_hit(rule, text)) is not None]
    positive_hits = []
    if include_positive_signals:
        positive_hits = [
            _hit for rule in POSITIVE_RULES if (_hit := _build_hit(rule, text)) is not None
        ]

    summary = (
        f"{len(risk_hits)} risk signal(s), {len(positive_hits)} positive signal(s) detected."
    )
    return DocumentRiskAnalysisResult(
        source_name=source_name,
        analysis_mode="deterministic_keyword",
        text_length=len(text),
        risk_hits=risk_hits,
        positive_hits=positive_hits,
        summary=summary,
        service_key_exposed=False,
    )


def _build_hit(rule: KeywordRule, text: str) -> RiskKeywordHit | None:
    matched_terms = [term for term in rule.terms if term.casefold() in text.casefold()]
    if not matched_terms:
        return None
    return RiskKeywordHit(
        code=rule.code,
        label=rule.label,
        severity=rule.severity,
        matched_terms=matched_terms,
        evidence=_evidence_snippet(text, matched_terms[0]),
        recommendation=rule.recommendation,
    )


def _evidence_snippet(text: str, term: str, radius: int = 36) -> str:
    index = text.casefold().find(term.casefold())
    if index < 0:
        return ""
    start = max(index - radius, 0)
    end = min(index + len(term) + radius, len(text))
    return text[start:end].strip()
