from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.services.document_risk_analyzer import analyze_document_risks

client = TestClient(app)
PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_document_risk_analyzer_detects_procurement_risks_and_positive_signals() -> None:
    text = _fixture_text()

    result = analyze_document_risks(text, source_name="sample_rfp_text.txt")
    risk_codes = {hit.code for hit in result.risk_hits}
    positive_codes = {hit.code for hit in result.positive_hits}

    assert "recent_performance_required" in risk_codes
    assert "single_contract_amount_required" in risk_codes
    assert "joint_supply_not_allowed" in risk_codes
    assert "software_business_certificate_required" in risk_codes
    assert "small_business_certificate_required" in risk_codes
    assert "high_technical_evaluation_weight" in risk_codes
    assert "ai_software_fit" in positive_codes
    assert "cloud_system_fit" in positive_codes
    assert "device_validation_fit" in positive_codes
    assert result.service_key_exposed is False


def test_document_risk_analysis_endpoint_works_with_fixture_text() -> None:
    response = client.post(
        "/g2b/document-risk-analysis",
        json={
            "source_name": "sample-rfp-text",
            "text": _fixture_text(),
            "include_positive_signals": True,
        },
    )

    payload = response.json()
    risk_codes = {hit["code"] for hit in payload["risk_hits"]}
    positive_codes = {hit["code"] for hit in payload["positive_hits"]}
    assert response.status_code == 200
    assert payload["analysis_mode"] == "deterministic_keyword"
    assert "recent_performance_required" in risk_codes
    assert "joint_supply_not_allowed" in risk_codes
    assert "ai_software_fit" in positive_codes
    assert payload["service_key_exposed"] is False
    assert "serviceKey" not in str(payload)


def test_pdf_analysis_candidates_returns_only_pdf_fixture_candidates() -> None:
    response = client.post(
        "/g2b/pdf-analysis-candidates",
        json={
            "mode": "fixture",
            "keyword": "AI",
            "page_no": 1,
            "num_rows": 3,
            "confirm_real_api_call": False,
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["ok"] is True
    assert payload["candidates"]
    assert {candidate["extension"] for candidate in payload["candidates"]} == {".pdf"}
    assert all(candidate["analysis_allowed"] is True for candidate in payload["candidates"])
    assert "serviceKey" not in str(payload)


def test_pdf_text_analysis_is_blocked_without_confirmation() -> None:
    response = client.post(
        "/g2b/pdf-text-analysis",
        json={
            "file_path": "data/fixtures/documents/sample_rfp.pdf",
            "source_name": "sample_rfp.pdf",
            "confirm_pdf_analysis": False,
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["ok"] is False
    assert payload["extraction"]["extraction_ok"] is False
    assert "confirm_pdf_analysis=true" in payload["message"]


def test_pdf_text_analysis_rejects_non_pdf_files() -> None:
    response = client.post(
        "/g2b/pdf-text-analysis",
        json={
            "file_path": "data/fixtures/documents/sample_rfp_text.txt",
            "source_name": "sample_rfp_text.txt",
            "confirm_pdf_analysis": True,
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["ok"] is False
    assert payload["extraction"]["extraction_ok"] is False
    assert "Only local PDF files are supported" in payload["message"]


def test_attachment_download_plan_remains_disabled_by_default() -> None:
    response = client.post(
        "/g2b/attachment-download-plan",
        json={
            "mode": "fixture",
            "keyword": "AI",
            "page_no": 1,
            "num_rows": 3,
            "confirm_real_api_call": False,
            "confirm_attachment_download": True,
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["download_enabled"] is False
    assert payload["items"]
    assert all(item["download_allowed"] is False for item in payload["items"])
    assert "serviceKey" not in str(payload)


def test_attachment_analysis_plan_marks_hwp_as_manual_review() -> None:
    response = client.post(
        "/g2b/attachment-analysis-plan",
        json={
            "mode": "fixture",
            "keyword": "AI",
            "page_no": 1,
            "num_rows": 3,
            "confirm_real_api_call": False,
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["pdf_candidates"]
    assert any(item["extension"] == ".hwp" for item in payload["items"])
    assert any(item["analysis_mode"] == "manual_review_required" for item in payload["items"])


def _fixture_text() -> str:
    return (
        PROJECT_ROOT / "data" / "fixtures" / "documents" / "sample_rfp_text.txt"
    ).read_text(encoding="utf-8")
