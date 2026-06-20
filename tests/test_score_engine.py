from app.integrations.g2b.fixtures import load_normalized_sample_notices
from app.scoring.score_engine import score_notice


def test_high_fit_ai_software_notice_scores_85_or_higher() -> None:
    notice = load_normalized_sample_notices()[0]

    score = score_notice(notice)

    assert score.total_score >= 85
    assert score.recommendation_level == "strong_recommend"
    assert score.score_breakdown["risk_penalty"] <= 0


def test_hardware_only_notice_scores_lower_than_ai_software_notice() -> None:
    notices = load_normalized_sample_notices()
    ai_notice = notices[0]
    hardware_notice = notices[3]

    ai_score = score_notice(ai_notice)
    hardware_score = score_notice(hardware_notice)

    assert hardware_score.total_score < ai_score.total_score
    assert any(risk.code == "hardware_only" for risk in hardware_score.risks)


def test_risk_case_contains_region_and_performance_risks() -> None:
    notice = load_normalized_sample_notices()[4]

    score = score_notice(notice)
    risk_codes = {risk.code for risk in score.risks}

    assert "non_seoul_region" in risk_codes
    assert "recent_performance_required" in risk_codes
    assert "single_contract_amount_required" in risk_codes
