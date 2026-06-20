from app.domain.yonlab_profile import default_yonlab_profile


def test_default_yonlab_profile_contains_required_baseline() -> None:
    profile = default_yonlab_profile()

    assert profile.company_name == "주식회사 와이온랩"
    assert profile.ceo == "이근영"
    assert profile.location == "서울특별시 강남구"
    assert "소기업" in profile.company_size
    assert "소상공인" in profile.company_size
    assert "초기창업기업" in profile.startup_status
    assert "소프트웨어사업자" in profile.core_qualifications
    assert "패키지소프트웨어개발 공급사업" in profile.core_qualifications
    assert "컴퓨터관련서비스사업" in profile.core_qualifications
    assert "인공지능소프트웨어" in profile.procurement_categories
    assert "AI Agent" in profile.technical_keywords
    assert "NPU" in profile.technical_keywords
