import json
from pathlib import Path

from app.integrations.g2b.fixtures import load_normalized_sample_notices, load_sample_g2b_notices
from app.integrations.g2b.normalizer import normalize_g2b_notice

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_g2b_fixture_loader_returns_at_least_five_notices() -> None:
    notices = load_sample_g2b_notices()

    assert len(notices) >= 5


def test_normalizer_maps_korean_and_g2b_like_fields() -> None:
    raw_notice = {
        "공고번호": "TEST-001",
        "공고명": "AI 기반 업무 시스템 구축",
        "수요기관": "서울테스트기관",
        "추정가격": "77,000,000원",
        "입찰마감일시": "2026-07-01",
        "지역제한": "서울특별시",
        "계약방법": "협상에 의한 계약",
        "참가자격": "소프트웨어사업자, 소기업",
        "과업내용": "인공지능소프트웨어와 정보시스템개발서비스 구축",
    }

    notice = normalize_g2b_notice(raw_notice)

    assert notice.notice_id == "TEST-001"
    assert notice.title == "AI 기반 업무 시스템 구축"
    assert notice.agency == "서울테스트기관"
    assert notice.budget_amount == 77_000_000
    assert notice.deadline == "2026-07-01"
    assert notice.region == "서울특별시"
    assert notice.contract_type == "협상에 의한 계약"
    assert "소프트웨어사업자" in notice.qualification_text
    assert "정보시스템개발서비스" in notice.description


def test_normalized_fixture_notices_have_titles() -> None:
    notices = load_normalized_sample_notices()

    assert all(notice.title for notice in notices)


def test_real_service_search_fixture_maps_contract_business_and_categories() -> None:
    raw_notice = _load_real_service_search_items()[0]

    notice = normalize_g2b_notice(raw_notice)

    assert notice.notice_id == "R26BK01540922"
    assert notice.title == "국산 AI반도체 성능 평가 체계화 시범검증 용역"
    assert notice.agency == "한국연구재단 정보통신기획평가원"
    assert notice.budget_amount == 252_210_000
    assert notice.deadline == "2026-06-16 10:00:00"
    assert notice.contract_type == "제한경쟁"
    assert notice.business_type == "일반용역"
    assert "연구조사서비스" in notice.categories
    assert "학술연구서비스" in notice.categories
    assert "80909032" in notice.categories
    assert "기타연구조사서비스" in notice.categories
    assert "공동수급불허" in notice.restrictions
    assert "업종제한 있음" in notice.restrictions
    assert "기술평가비율 90" in notice.requirements
    assert "가격평가비율 10" in notice.requirements
    assert "협상에의한계약" in notice.description


def _load_real_service_search_items() -> list[dict]:
    payload = json.loads(
        (PROJECT_ROOT / "data" / "fixtures" / "g2b" / "real_servc_search_sample.json").read_text(
            encoding="utf-8"
        )
    )
    return payload["response"]["body"]["items"]
