from app.domain.bid_notice import BidNotice
from app.domain.recommendation import RecommendationReport, RecommendationScore
from app.scoring.score_engine import score_notice


def generate_markdown_report(
    notice: BidNotice,
    score: RecommendationScore | None = None,
) -> RecommendationReport:
    score = score or score_notice(notice)
    risks = score.risks
    risk_lines = [f"{risk.message} 대응: {risk.recommendation}" for risk in risks]
    if not risk_lines:
        risk_lines = ["현재 자동 분석 기준에서 중대한 리스크는 발견되지 않았습니다."]

    markdown = "\n".join(
        [
            f"## 🎯 와이온랩 맞춤 추천 공고: {notice.title or '제목 없음'}",
            "",
            f"- **매칭 점수**: {score.total_score}점 / 100점",
            f"- **추천 등급**: {score.recommendation_label}",
            "- **추천 사유**:",
            *_bullet_lines(score.positive_reasons),
            "- **핵심 정보**:",
            f"  - 발주처: {notice.agency or '확인 필요'}",
            f"  - 예산: {_format_budget(notice.budget_amount)}",
            f"  - 마감일: {notice.deadline or '확인 필요'}",
            f"  - 지역 제한: {notice.region or '확인 필요'}",
            f"  - 계약 유형: {notice.contract_type or '확인 필요'}",
            "- **입찰 준비 전략**:",
            "  - 예비창업패키지 기반 AI/Device Farm/AI 검증 플랫폼 경험을 "
            "실환경 검증 역량으로 연결해 제안서에 반영합니다.",
            "  - 온디바이스 AI/NPU/로봇 AI 기술역량을 활용해 AI 모델의 실행성, "
            "검증성, 운영 안정성을 강조합니다.",
            "  - 소기업/소상공인 및 창업기업 지위를 활용해 제한·우대 조건의 "
            "전략적 적합성을 명확히 제시합니다.",
            "- **제출 필요 서류**:",
            "  - 소프트웨어사업자 일반 현황 관리확인서",
            "  - 중소기업/소기업/소상공인 확인서",
            "  - 창업기업 확인서",
            "  - 나라장터 경쟁입찰참가자격등록증",
            "- **리스크**:",
            *_bullet_lines(risk_lines),
            "- **권장 대응**:",
            "  - 공고문 원문에서 참가자격, 실적 조건, 지역 제한이 필수인지 먼저 확인합니다.",
            "  - 민간 실적 인정 여부와 증빙자료 준비 가능성을 사전에 점검합니다.",
            "  - 제안서에는 AI/SW 개발뿐 아니라 검증·배포·운영 안정성 확보 방안을 함께 제시합니다.",
        ]
    )

    return RecommendationReport(notice_title=notice.title, score=score, markdown=markdown)


def _format_budget(budget_amount: int | None) -> str:
    if budget_amount is None:
        return "확인 필요"
    return f"{budget_amount:,}원"


def _bullet_lines(items: list[str]) -> list[str]:
    return [f"  - {item}" for item in items]
