from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SMOKE_SCRIPT_NAMES = (
    "smoke_demo.ps1",
    "smoke_report.ps1",
    "smoke_g2b_config.ps1",
    "smoke_g2b_search_fixture.ps1",
    "smoke_g2b_recommend_fixture.ps1",
)


def test_smoke_scripts_exist() -> None:
    for script_name in SMOKE_SCRIPT_NAMES:
        assert (PROJECT_ROOT / "scripts" / script_name).is_file()


def test_smoke_scripts_use_explicit_utf8_response_handling() -> None:
    for script_name in SMOKE_SCRIPT_NAMES:
        content = (PROJECT_ROOT / "scripts" / script_name).read_text(encoding="utf-8")

        assert "System.Text.UTF8Encoding($false)" in content
        assert "[Console]::OutputEncoding = $Utf8" in content
        assert "$OutputEncoding = $Utf8" in content
        assert "chcp.com 65001" in content
        assert "Invoke-WebRequest" in content
        assert "RawContentStream" in content


def test_gitattributes_contains_line_ending_policy() -> None:
    content = (PROJECT_ROOT / ".gitattributes").read_text(encoding="utf-8")

    assert "*.py text eol=lf" in content
    assert "*.ps1 text eol=crlf" in content
