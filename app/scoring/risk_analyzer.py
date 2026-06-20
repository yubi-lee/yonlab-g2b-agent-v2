from datetime import date, datetime

from app.domain.bid_notice import BidNotice
from app.domain.recommendation import RiskItem, RiskSeverity

SEOUL_OR_OPEN_REGION_TERMS = ("서울", "전국", "수도권")
OTHER_REGION_TERMS = (
    "부산",
    "대구",
    "인천",
    "광주",
    "대전",
    "울산",
    "세종",
    "강원",
    "충북",
    "충청북도",
    "충남",
    "충청남도",
    "전북",
    "전라북도",
    "전남",
    "전라남도",
    "경북",
    "경상북도",
    "경남",
    "경상남도",
    "제주",
)
HARDWARE_TERMS = ("h/w", "hw", "하드웨어", "전산장비", "pc 납품", "서버 납품", "장비 납품")
SOFTWARE_TERMS = ("ai", "인공지능", "소프트웨어", "sw", "정보시스템", "클라우드", "시스템")
FIXED_EVALUATION_DATE = date(2026, 6, 20)


def analyze_risks(
    notice: BidNotice,
    evaluation_date: date = FIXED_EVALUATION_DATE,
) -> list[RiskItem]:
    text = notice.searchable_text()
    risks: list[RiskItem] = []

    if _is_other_region_limited(notice, text):
        risks.append(
            RiskItem(
                code="non_seoul_region",
                severity=RiskSeverity.HIGH,
                message="서울 외 특정 지역 소재 업체 제한 가능성이 있습니다.",
                recommendation="공고문 원문에서 지역 제한이 참가 필수 조건인지 먼저 확인합니다.",
            )
        )

    if _has_recent_performance_requirement(text):
        risks.append(
            RiskItem(
                code="recent_performance_required",
                severity=RiskSeverity.HIGH,
                message="최근 3년 유사 사업 수행 실적 제출 조건이 있습니다.",
                recommendation=(
                    "민간 실적 인정 여부와 계약서·세금계산서·검수확인서 확보 여부를 "
                    "확인합니다."
                ),
            )
        )

    has_single_contract = _has_any(text, ("단일 계약", "단일건", "단일 건", "1건"))
    if has_single_contract and _has_any(text, ("실적", "계약")):
        risks.append(
            RiskItem(
                code="single_contract_amount_required",
                severity=RiskSeverity.HIGH,
                message="단일 계약 금액 기준 실적 제한이 있을 수 있습니다.",
                recommendation=(
                    "요구 금액과 인정 범위를 확인하고 증빙 가능한 실적을 사전 "
                    "매핑합니다."
                ),
            )
        )

    if _is_hardware_only(text):
        risks.append(
            RiskItem(
                code="hardware_only",
                severity=RiskSeverity.HIGH,
                message="단순 하드웨어 또는 장비 납품 중심 공고입니다.",
                recommendation=(
                    "AI/SW 구축 범위가 별도로 있는지 확인하고 직접 참여 우선순위는 "
                    "낮춥니다."
                ),
            )
        )

    if _has_any(text, ("상주", "전담 인력", "투입인력", "현장근무", "파견")):
        risks.append(
            RiskItem(
                code="staffing_or_onsite_required",
                severity=RiskSeverity.MEDIUM,
                message="상주 또는 전담 인력 투입 부담이 있을 수 있습니다.",
                recommendation="단독 수행 가능성과 협력사 투입 필요성을 검토합니다.",
            )
        )

    if _has_any(text, ("제조사", "총판", "대리점", "공급확약서", "특정 라이선스")):
        risks.append(
            RiskItem(
                code="license_mismatch",
                severity=RiskSeverity.MEDIUM,
                message="제조사·총판·대리점 또는 특정 라이선스 조건이 있을 수 있습니다.",
                recommendation="와이온랩 보유 자격과 다른 유통 자격인지 확인합니다.",
            )
        )

    deadline_risk = _deadline_risk(notice.deadline, evaluation_date)
    if deadline_risk is not None:
        risks.append(deadline_risk)

    return risks


def _is_other_region_limited(notice: BidNotice, text: str) -> bool:
    region_text = f"{notice.region} {text}".casefold()
    has_other_region = _has_any(region_text, OTHER_REGION_TERMS)
    has_open_region = _has_any(region_text, SEOUL_OR_OPEN_REGION_TERMS)
    return has_other_region and not has_open_region


def _has_recent_performance_requirement(text: str) -> bool:
    has_recent_window = _has_any(text, ("최근 3년", "최근3년", "3년 이내"))
    return has_recent_window and _has_any(text, ("실적", "수행실적"))


def _is_hardware_only(text: str) -> bool:
    return _has_any(text, HARDWARE_TERMS) and not _has_any(text, SOFTWARE_TERMS)


def _deadline_risk(deadline: str | None, evaluation_date: date) -> RiskItem | None:
    if not deadline:
        return RiskItem(
            code="deadline_missing",
            severity=RiskSeverity.MEDIUM,
            message="마감일 정보가 없어 준비 가능 기간을 판단하기 어렵습니다.",
            recommendation="공고 원문에서 입찰 마감일시를 확인합니다.",
        )

    parsed_deadline = _parse_deadline(deadline)
    if parsed_deadline is None:
        return None

    days_left = (parsed_deadline - evaluation_date).days
    if days_left < 0:
        return RiskItem(
            code="deadline_passed",
            severity=RiskSeverity.HIGH,
            message="마감일이 이미 지난 공고일 수 있습니다.",
            recommendation="정정공고 또는 재공고 여부를 확인합니다.",
        )
    if days_left <= 7:
        return RiskItem(
            code="deadline_urgent",
            severity=RiskSeverity.MEDIUM,
            message="입찰 마감까지 준비 기간이 짧습니다.",
            recommendation="필수 서류 보유 여부와 제안서 작성 가능 시간을 즉시 확인합니다.",
        )
    return None


def _parse_deadline(deadline: str) -> date | None:
    normalized = deadline.replace(".", "-").replace("/", "-").strip()
    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(normalized[: len("2026-06-20 12:00:00")], fmt).date()
        except ValueError:
            continue
    return None


def _has_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(term.casefold() in text for term in terms)
