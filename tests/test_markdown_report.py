from app.integrations.g2b.fixtures import load_normalized_sample_notices
from app.reports.markdown_report import generate_markdown_report


def test_markdown_report_contains_required_sections_and_yonlab_strategy() -> None:
    notice = load_normalized_sample_notices()[0]

    report = generate_markdown_report(notice)
    markdown = report.markdown

    assert "## 🎯 와이온랩 맞춤 추천 공고" in markdown
    assert "매칭 점수" in markdown
    assert "입찰 준비 전략" in markdown
    assert "제출 필요 서류" in markdown
    assert "리스크" in markdown
    assert "예비창업패키지 기반 AI/Device Farm/AI 검증 플랫폼 경험" in markdown
    assert "온디바이스 AI/NPU/로봇 AI 기술역량" in markdown
    assert "소기업/소상공인 및 창업기업 지위" in markdown
