from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_profile_endpoint_returns_company_name_and_qualifications() -> None:
    response = client.get("/profile/yonlab")

    assert response.status_code == 200
    payload = response.json()
    assert payload["company_name"] == "주식회사 와이온랩"
    assert "소프트웨어사업자" in payload["core_qualifications"]


def test_fixture_endpoint_returns_sample_notices() -> None:
    response = client.get("/fixtures/g2b/notices")

    assert response.status_code == 200
    assert len(response.json()["notices"]) >= 5


def test_normalize_endpoint_returns_bid_notice() -> None:
    response = client.post(
        "/notices/normalize",
        json={"공고명": "AI 시스템 구축", "수요기관": "테스트기관", "추정가격": "10,000,000원"},
    )

    assert response.status_code == 200
    assert response.json()["notice"]["title"] == "AI 시스템 구축"
    assert response.json()["notice"]["budget_amount"] == 10_000_000


def test_score_endpoint_accepts_raw_notice() -> None:
    response = client.post(
        "/recommendations/score",
        json={
            "공고명": "서울 AI 소프트웨어 개발",
            "지역제한": "서울특별시",
            "참가자격": "소프트웨어사업자, 소기업, 창업기업 우대",
            "과업내용": "인공지능소프트웨어 정보시스템개발서비스",
            "입찰마감일시": "2026-07-20",
        },
    )

    assert response.status_code == 200
    assert response.json()["total_score"] >= 85


def test_score_endpoint_accepts_explicit_raw_notice_request_schema() -> None:
    response = client.post(
        "/recommendations/score",
        json={
            "raw_notice": {
                "공고명": "서울 AI 소프트웨어 개발",
                "지역제한": "서울특별시",
                "참가자격": "소프트웨어사업자, 소기업, 창업기업 우대",
                "과업내용": "인공지능소프트웨어 정보시스템개발서비스",
                "입찰마감일시": "2026-07-20",
            }
        },
    )

    assert response.status_code == 200
    assert response.json()["total_score"] >= 85


def test_report_endpoint_returns_markdown() -> None:
    response = client.post(
        "/recommendations/report",
        json={
            "공고명": "서울 AI 소프트웨어 개발",
            "수요기관": "테스트기관",
            "참가자격": "소프트웨어사업자, 소기업",
            "과업내용": "AI Agent 정보시스템개발서비스",
            "입찰마감일시": "2026-07-20",
        },
    )

    assert response.status_code == 200
    assert "## 🎯 와이온랩 맞춤 추천 공고" in response.json()["markdown"]


def test_openapi_uses_explicit_request_schemas() -> None:
    openapi = client.get("/openapi.json").json()

    score_schema = openapi["paths"]["/recommendations/score"]["post"]["requestBody"]
    demo_schema = openapi["paths"]["/demo/recommendations"]["post"]["requestBody"]

    assert "NoticeRequest" in str(score_schema)
    assert "DemoRecommendationsRequest" in str(demo_schema)
