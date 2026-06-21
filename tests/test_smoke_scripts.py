from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SMOKE_SCRIPT_NAMES = (
    "smoke_demo.ps1",
    "smoke_report.ps1",
    "smoke_g2b_config.ps1",
    "smoke_g2b_search_fixture.ps1",
    "smoke_g2b_recommend_fixture.ps1",
    "smoke_g2b_endpoint_presets.ps1",
    "smoke_g2b_real_readiness.ps1",
    "smoke_g2b_real_guard_blocked.ps1",
    "smoke_g2b_document_risk_analysis.ps1",
    "smoke_g2b_pdf_analysis_candidates_fixture.ps1",
    "smoke_g2b_pdf_text_analysis_fixture.ps1",
    "smoke_g2b_real_confirmed_template.ps1",
    "smoke_g2b_real_recommend_template.ps1",
    "run_ops_fixture.ps1",
    "run_ops_real_template.ps1",
    "show_ops_runs.ps1",
    "show_ops_recommendations.ps1",
    "smoke_ui_health.ps1",
    "smoke_ops_package_info.ps1",
    "smoke_ops_real_readiness.ps1",
    "smoke_ops_ui_flow.ps1",
)
OPS_SCRIPT_NAMES = (
    "start_local_ops.ps1",
    "validate_ops_package.ps1",
    "validate_g2b_real_ops_readiness.ps1",
    "open_latest_report_dir.ps1",
    "run_daily_fixture.ps1",
    "register_daily_task_template.ps1",
    "reset_local_ops_data.ps1",
)
VALIDATION_SCRIPT_NAME = "validate_local.ps1"
REAL_READINESS_SCRIPT_NAME = "validate_g2b_real_readiness.ps1"
NO_SECRET_SCRIPT_NAME = "check_no_secrets.ps1"
CREATE_ENV_TEMPLATE_SCRIPT_NAME = "create_env_template.ps1"
SHOW_REAL_ENV_STATUS_SCRIPT_NAME = "show_g2b_real_env_status.ps1"


def test_smoke_scripts_exist() -> None:
    for script_name in SMOKE_SCRIPT_NAMES:
        assert (PROJECT_ROOT / "scripts" / script_name).is_file()
    for script_name in OPS_SCRIPT_NAMES:
        assert (PROJECT_ROOT / "scripts" / script_name).is_file()
    assert (PROJECT_ROOT / "scripts" / VALIDATION_SCRIPT_NAME).is_file()
    assert (PROJECT_ROOT / "scripts" / REAL_READINESS_SCRIPT_NAME).is_file()
    assert (PROJECT_ROOT / "scripts" / NO_SECRET_SCRIPT_NAME).is_file()
    assert (PROJECT_ROOT / "scripts" / CREATE_ENV_TEMPLATE_SCRIPT_NAME).is_file()
    assert (PROJECT_ROOT / "scripts" / SHOW_REAL_ENV_STATUS_SCRIPT_NAME).is_file()


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
    for mojibake_fragment in ("\u6028", "\uc496", "\ub6b0", "\u5a9b"):
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
    assert "check_no_secrets.ps1" in content
    assert "smoke_g2b_config.ps1" in content
    assert "smoke_g2b_endpoint_presets.ps1" in content
    assert "smoke_g2b_real_readiness.ps1" in content
    assert "smoke_g2b_search_fixture.ps1" in content
    assert "smoke_g2b_recommend_fixture.ps1" in content
    assert "smoke_ui_health.ps1" in content
    assert "run_ops_fixture.ps1" in content
    assert "smoke_ops_real_readiness.ps1" in content
    assert "smoke_ops_ui_flow.ps1" in content
    assert "show_ops_runs.ps1" in content
    assert "show_ops_recommendations.ps1" in content
    assert "smoke_g2b_document_risk_analysis.ps1" in content
    assert "smoke_g2b_pdf_analysis_candidates_fixture.ps1" in content
    assert "smoke_g2b_pdf_text_analysis_fixture.ps1" in content
    assert "smoke_g2b_real_guard_blocked.ps1" in content
    assert "smoke_report.ps1" in content
    assert "Stop-Job" in content


def test_real_readiness_script_runs_offline_validation_steps() -> None:
    content = (PROJECT_ROOT / "scripts" / REAL_READINESS_SCRIPT_NAME).read_text(encoding="utf-8")

    assert "System.Text.UTF8Encoding($false)" in content
    assert "check_no_secrets.ps1" in content
    assert "tests\\test_g2b_endpoint_presets.py" in content
    assert "tests\\test_g2b_readiness.py" in content
    assert "-m app.integrations.g2b.readiness" in content
    assert "Invoke-WebRequest" not in content
    assert "smoke_g2b_real_confirmed_template.ps1" not in content
    assert "smoke_g2b_real_recommend_template.ps1" not in content


def test_no_secret_script_validates_placeholders_and_ignored_paths() -> None:
    content = (PROJECT_ROOT / "scripts" / NO_SECRET_SCRIPT_NAME).read_text(encoding="utf-8")

    assert "G2B_API_SERVICE_KEY" in content
    assert "serviceKey" in content
    assert "git ls-files --cached --others --exclude-standard" in content
    assert "<your local key>" in content


def test_create_env_template_does_not_overwrite_env_or_print_key() -> None:
    content = (PROJECT_ROOT / "scripts" / CREATE_ENV_TEMPLATE_SCRIPT_NAME).read_text(
        encoding="utf-8"
    )

    assert "Test-Path -LiteralPath $EnvPath" in content
    assert "It was not overwritten" in content
    assert "Copy-Item" in content
    assert "Set G2B_API_SERVICE_KEY manually in .env only" in content
    assert "SECRET-KEY" not in content


def test_show_real_env_status_prints_only_safe_fields() -> None:
    content = (PROJECT_ROOT / "scripts" / SHOW_REAL_ENV_STATUS_SCRIPT_NAME).read_text(
        encoding="utf-8"
    )

    assert "service_key_configured" in content
    assert "current_endpoint_path" in content
    assert "recommended_endpoint_path" in content
    assert "G2B_API_SERVICE_KEY" in content
    assert "SECRET-KEY" not in content


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
        assert "start_date = \"2026-06-01\"" in content
        assert "end_date = \"2026-06-20\"" in content
        assert "getBidPblancListInfoServcPPSSrch" in content

    recommend_content = (
        PROJECT_ROOT / "scripts" / "smoke_g2b_real_recommend_template.ps1"
    ).read_text(encoding="utf-8")
    assert "active_only = $false" in recommend_content
    assert "Select-Object rank, notice_id, title, agency" in recommend_content


def test_gitattributes_contains_line_ending_policy() -> None:
    content = (PROJECT_ROOT / ".gitattributes").read_text(encoding="utf-8")

    assert "*.py text eol=lf" in content
    assert "*.ps1 text eol=crlf" in content
