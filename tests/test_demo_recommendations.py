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
