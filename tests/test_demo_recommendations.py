from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_demo_recommendations_returns_ranked_recommendations() -> None:
    response = client.post("/demo/recommendations")

    assert response.status_code == 200
    payload = response.json()
    recommendations = payload["recommendations"]

    assert payload["source_count"] >= 5
    assert len(recommendations) >= 5
    assert payload["ranked_order"][0] == recommendations[0]["normalized_notice"]["notice_id"]
    scores = [item["score"]["total_score"] for item in recommendations]
    assert scores == sorted(scores, reverse=True)
    assert "report" in recommendations[0]


def test_demo_recommendations_accepts_empty_object_request() -> None:
    response = client.post("/demo/recommendations", json={})

    assert response.status_code == 200
    payload = response.json()
    assert payload["include_reports"] is True
    assert len(payload["recommendations"]) == 5


def test_demo_recommendations_returns_compact_response_when_reports_disabled() -> None:
    response = client.post(
        "/demo/recommendations",
        json={"include_reports": False, "limit": 3},
    )

    assert response.status_code == 200
    payload = response.json()
    recommendations = payload["recommendations"]

    assert payload["include_reports"] is False
    assert len(recommendations) == 3
    first = recommendations[0]
    assert set(first) == {
        "rank",
        "notice_id",
        "title",
        "agency",
        "total_score",
        "recommendation_label",
        "top_positive_reasons",
        "risk_summaries",
    }
    assert first["rank"] == 1
    assert isinstance(first["top_positive_reasons"], list)


def test_demo_recommendations_returns_full_response_when_reports_enabled() -> None:
    response = client.post(
        "/demo/recommendations",
        json={"include_reports": True, "limit": 2},
    )

    assert response.status_code == 200
    recommendations = response.json()["recommendations"]

    assert len(recommendations) == 2
    assert "normalized_notice" in recommendations[0]
    assert "score" in recommendations[0]
    assert "report" in recommendations[0]
