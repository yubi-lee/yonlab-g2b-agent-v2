from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SMOKE_SCRIPT_NAMES = (
    "smoke_demo.ps1",
    "smoke_report.ps1",
    "smoke_g2b_config.ps1",
    "smoke_g2b_search_fixture.ps1",
    "smoke_g2b_recommend_fixture.ps1",
    "smoke_g2b_real_guard_blocked.ps1",
    "smoke_g2b_real_confirmed_template.ps1",
    "smoke_g2b_real_recommend_template.ps1",
)
VALIDATION_SCRIPT_NAME = "validate_local.ps1"


def test_smoke_scripts_exist() -> None:
    for script_name in SMOKE_SCRIPT_NAMES:
        assert (PROJECT_ROOT / "scripts" / script_name).is_file()
    assert (PROJECT_ROOT / "scripts" / VALIDATION_SCRIPT_NAME).is_file()


def test_smoke_scripts_use_explicit_utf8_response_handling() -> None:
    for script_name in SMOKE_SCRIPT_NAMES:
        content = (PROJECT_ROOT / "scripts" / script_name).read_text(encoding="utf-8")

        assert "System.Text.UTF8Encoding($false)" in content
        assert "[Console]::OutputEncoding = $Utf8" in content
        assert "$OutputEncoding = $Utf8" in content
        assert "chcp.com 65001" in content
        assert "Invoke-WebRequest" in content
        assert "-UseBasicParsing" in content
        assert "RawContentStream" in content


def test_smoke_report_script_is_ascii_safe_for_windows_powershell_parser() -> None:
    script_bytes = (PROJECT_ROOT / "scripts" / "smoke_report.ps1").read_bytes()
    script_text = script_bytes.decode("ascii")

    assert '"\\uacf5\\uace0\\uba85"' in script_text
    assert "공고명" not in script_text
    for mojibake_fragment in ("怨", "쒖", "뚰", "媛"):
        assert mojibake_fragment not in script_text


def test_validate_local_script_runs_expected_validation_steps() -> None:
    content = (PROJECT_ROOT / "scripts" / VALIDATION_SCRIPT_NAME).read_text(encoding="utf-8")

    assert "System.Text.UTF8Encoding($false)" in content
    assert "Activate.ps1" in content
    assert "python.exe" in content
    assert "-m pytest -q" in content
    assert "Start-Job" in content
    assert "-m uvicorn app.main:app" in content
    assert "Wait-ForHealth" in content
    assert "smoke_g2b_config.ps1" in content
    assert "smoke_g2b_search_fixture.ps1" in content
    assert "smoke_g2b_recommend_fixture.ps1" in content
    assert "smoke_g2b_real_guard_blocked.ps1" in content
    assert "smoke_report.ps1" in content
    assert "Stop-Job" in content


def test_real_smoke_templates_contain_no_service_key() -> None:
    script_names = (
        "smoke_g2b_real_confirmed_template.ps1",
        "smoke_g2b_real_recommend_template.ps1",
    )
    for script_name in script_names:
        content = (PROJECT_ROOT / "scripts" / script_name).read_text(encoding="utf-8")

        assert "G2B_API_SERVICE_KEY=<your local key>" in content
        assert "SECRET-KEY" not in content
        assert "confirm_real_api_call = $true" in content
        assert "mode = \"real\"" in content


def test_gitattributes_contains_line_ending_policy() -> None:
    content = (PROJECT_ROOT / ".gitattributes").read_text(encoding="utf-8")

    assert "*.py text eol=lf" in content
    assert "*.ps1 text eol=crlf" in content
