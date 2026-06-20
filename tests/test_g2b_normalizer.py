from app.integrations.g2b.fixtures import load_normalized_sample_notices, load_sample_g2b_notices
from app.integrations.g2b.normalizer import normalize_g2b_notice


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
