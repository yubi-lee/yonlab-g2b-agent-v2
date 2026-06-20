from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from app.integrations.g2b.fixtures import load_normalized_sample_notices
from app.main import app

client = TestClient(app)

EXPECTED_TITLE = "서울 AI 기반 행정지원 업무 자동화 시스템 구축"
EXPECTED_AGENCY = "서울특별시 산하기관"
EXPECTED_BUSAN_TITLE = "부산 지역 AI 관제 시스템 구축"
EXPECTED_RECOMMENDATION = "적극 추천"
EXPECTED_REPORT_HEADING = "와이온랩 맞춤 추천 공고"
MOJIBAKE_FRAGMENTS = ("ì", "ê", "ë", "í")
DUPLICATED_KOREAN_FRAGMENTS = (
    "부" * 2 + "산" * 2,
    "지" * 2 + "역" * 2,
    "관" * 2 + "제" * 2,
    "시" * 2 + "스" * 2 + "템" * 2,
    "구" * 2 + "축" * 2,
)


def test_fixture_file_is_utf8_without_bom_and_loader_returns_korean_title() -> None:
    fixture_path = Path("data/fixtures/g2b/sample_notices.json")
    fixture_bytes = fixture_path.read_bytes()

    assert not fixture_bytes.startswith(b"\xef\xbb\xbf")
    assert EXPECTED_TITLE in fixture_path.read_text(encoding="utf-8")
    assert load_normalized_sample_notices()[0].title == EXPECTED_TITLE


def test_fixture_raw_source_does_not_contain_duplicated_korean_text() -> None:
    notices = load_normalized_sample_notices()
    busan_notice = notices[4]

    assert busan_notice.title == EXPECTED_BUSAN_TITLE
    assert busan_notice.raw_source["bidNtceNm"] == EXPECTED_BUSAN_TITLE
    raw_source_text = str(busan_notice.raw_source)
    for fragment in DUPLICATED_KOREAN_FRAGMENTS:
        assert fragment not in raw_source_text


def test_g2b_search_fixture_response_preserves_korean() -> None:
    response = client.post("/g2b/search", json={"mode": "fixture", "keyword": "AI"})

    assert response.status_code == 200
    payload = response.json()
    first_notice = payload["notices"][0]
    assert first_notice["title"] == EXPECTED_TITLE
    assert first_notice["agency"] == EXPECTED_AGENCY
    _assert_no_mojibake([first_notice["title"], first_notice["agency"]])


def test_g2b_recommendations_response_preserves_korean_label() -> None:
    response = client.post(
        "/g2b/recommendations",
        json={"mode": "fixture", "keyword": "AI", "include_reports": False},
    )

    assert response.status_code == 200
    first_recommendation = response.json()["recommendations"][0]
    assert first_recommendation["recommendation_label"] == EXPECTED_RECOMMENDATION
    _assert_no_mojibake(
        [
            first_recommendation["title"],
            first_recommendation["agency"],
            first_recommendation["recommendation_label"],
        ]
    )


def test_recommendations_report_response_preserves_korean_markdown() -> None:
    response = client.post(
        "/recommendations/report",
        json={
            "공고명": "서울 AI 소프트웨어 개발",
            "수요기관": "서울특별시 강남구",
            "참가자격": "소프트웨어사업자, 소기업 또는 소상공인",
            "과업내용": "인공지능 소프트웨어 개발 및 클라우드 기반 시스템 구축",
            "입찰마감일시": "2026-07-15",
        },
    )

    assert response.status_code == 200
    markdown = response.json()["markdown"]
    assert EXPECTED_REPORT_HEADING in markdown
    _assert_no_mojibake([markdown])


def test_no_mojibake_fragments_in_korean_pipeline_content_fields() -> None:
    search_payload = client.post("/g2b/search", json={"mode": "fixture"}).json()
    recommendation_payload = client.post(
        "/g2b/recommendations",
        json={"mode": "fixture", "keyword": "AI", "include_reports": True},
    ).json()

    content_values: list[str] = []
    for notice in search_payload["notices"]:
        content_values.extend(_notice_content_values(notice))
    for recommendation in recommendation_payload["recommendations"]:
        content_values.extend(_notice_content_values(recommendation["normalized_notice"]))
        content_values.append(recommendation["score"]["recommendation_label"])
        content_values.append(recommendation["report"]["markdown"])

    _assert_no_mojibake(content_values)


def _notice_content_values(notice: dict[str, Any]) -> list[str]:
    values = [
        notice.get("title", ""),
        notice.get("agency", ""),
        notice.get("region", ""),
        notice.get("contract_type", ""),
        notice.get("business_type", ""),
        notice.get("qualification_text", ""),
        notice.get("description", ""),
        *notice.get("keywords", []),
    ]
    return [value for value in values if isinstance(value, str)]


def _assert_no_mojibake(values: list[str]) -> None:
    joined = "\n".join(values)
    for fragment in MOJIBAKE_FRAGMENTS:
        assert fragment not in joined
