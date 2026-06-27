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
    "smoke_ops_quality_summary.ps1",
    "smoke_ops_report_index.ps1",
    "smoke_ops_ui_flow.ps1",
)
OPS_SCRIPT_NAMES = (
    "start_local_ops.ps1",
    "check_deploy_readiness.ps1",
    "validate_ops_package.ps1",
    "validate_g2b_real_ops_readiness.ps1",
    "validate_real_ops_controlled.ps1",
    "check_real_ops_readiness.ps1",
    "run_ops_real_controlled.ps1",
    "open_latest_report_dir.ps1",
    "run_daily_fixture.ps1",
    "register_daily_task_template.ps1",
    "reset_local_ops_data.ps1",
    "run_release_closeout_harness.ps1",
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
    assert "smoke_ops_quality_summary.ps1" in content
    assert "smoke_ops_report_index.ps1" in content
    assert "smoke_ops_ui_flow.ps1" in content
    assert "show_ops_runs.ps1" in content
    assert "show_ops_recommendations.ps1" in content
    assert "smoke_g2b_document_risk_analysis.ps1" in content
    assert "smoke_g2b_pdf_analysis_candidates_fixture.ps1" in content
    assert "smoke_g2b_pdf_text_analysis_fixture.ps1" in content
    assert "smoke_g2b_real_guard_blocked.ps1" in content
    assert "smoke_report.ps1" in content
    assert "run_ops_real_controlled.ps1 -ConfirmRealApiCall" not in content
    assert "validate_real_ops_controlled.ps1 -ConfirmRealApiCall" not in content
    assert "smoke_g2b_real_confirmed_template.ps1" not in content
    assert "smoke_g2b_real_recommend_template.ps1" not in content
    assert "Stop-Job" in content


def test_controlled_real_ops_scripts_are_guarded_and_secret_safe() -> None:
    run_script = (PROJECT_ROOT / "scripts" / "run_ops_real_controlled.ps1").read_text(
        encoding="utf-8"
    )
    validate_script = (
        PROJECT_ROOT / "scripts" / "validate_real_ops_controlled.ps1"
    ).read_text(encoding="utf-8")

    assert "ConfirmRealApiCall" in run_script
    assert "if (-not $ConfirmRealApiCall)" in run_script
    assert "exit 0" in run_script
    assert "/ops/run-recommendations" in run_script
    assert "-ConfirmRealApiCall" in validate_script
    assert "$BaseUri = [System.Uri] $BaseUrl" in validate_script
    assert "--port $JobPort" in validate_script
    assert "if ($ConfirmRealApiCall)" in validate_script
    assert "run_ops_real_controlled.ps1\") -ConfirmRealApiCall" in validate_script
    assert "/g2b/config" in validate_script
    assert "/g2b/real-readiness" in validate_script
    assert "/ops/real-readiness" in validate_script
    assert "/ops/runs?limit=1" in validate_script
    assert "/ops/recommendations?limit=5" in validate_script
    assert "/ops/quality-summary" in validate_script
    assert "/ops/report-index?limit=20" in validate_script
    assert "ops_runtime_gate_enabled" in validate_script
    assert "controlled_confirm_flag_detected" in validate_script
    assert "real_network_call_attempted" in validate_script
    assert "real_report_created" in validate_script
    assert "safe_next_action" in validate_script
    assert "confirmed_real_step_executed" in validate_script
    assert "real_operation_error_code" in validate_script
    assert "failure_classification" in validate_script
    for secret_marker in ("SECRET-KEY", "G2B_API_SERVICE_KEY=<your local key>"):
        assert secret_marker not in run_script
        assert secret_marker not in validate_script


def test_check_real_ops_readiness_script_is_offline_and_secret_safe() -> None:
    content = (PROJECT_ROOT / "scripts" / "check_real_ops_readiness.ps1").read_text(
        encoding="utf-8"
    )

    assert "System.Text.UTF8Encoding($false)" in content
    assert "-m\", \"app.services.real_ops_runtime_readiness" in content
    assert "ConfirmControlledRealCallIntent" in content
    assert "Invoke-WebRequest" not in content
    assert "run_ops_real_controlled.ps1" not in content
    assert "-ConfirmRealApiCall" not in content
    assert "SECRET-KEY" not in content


def test_check_deploy_readiness_script_is_offline_and_secret_safe() -> None:
    content = (PROJECT_ROOT / "scripts" / "check_deploy_readiness.ps1").read_text(
        encoding="utf-8"
    )

    assert "System.Text.UTF8Encoding($false)" in content
    assert "working_tree_clean" in content
    assert "required_scripts_present" in content
    assert "real_api_settings_presence_as_boolean_only" in content
    assert "Test-ProjectRootLike" in content
    assert 'Split-Path -Leaf $ProjectRoot) -eq "yonlab-g2b-agent-v2"' not in content
    assert "Invoke-WebRequest" not in content
    assert "validate_real_ops_controlled.ps1 -ConfirmRealApiCall" not in content
    assert "YONLAB_AUTO_RUN_REAL_API = \"true\"" not in content
    assert "SECRET-KEY" not in content


def test_release_closeout_harness_is_guarded_and_secret_safe() -> None:
    content = (PROJECT_ROOT / "scripts" / "run_release_closeout_harness.ps1").read_text(
        encoding="utf-8"
    )

    assert "ReleaseTag = \"v0.1.0-rc5\"" in content
    assert "RunControlledRealCall" in content
    assert "ConfirmRealApiCall" in content
    assert "RunSyntheticPersistenceCheck" in content
    assert "SkipPush" in content
    assert "validate_real_ops_controlled.ps1 -ConfirmRealApiCall" in content
    assert "if ($RunControlledRealCall -and $ConfirmRealApiCall)" in content
    assert "base_real_config_ready" in content
    assert "Set-DeploymentRuntimeEnvironment" in content
    assert "app.services.runtime_path_consistency" in content
    assert "storage_path_consistent" in content
    assert "report_path_consistent" in content
    assert "synthetic persistence consistency" in content
    assert "ready_for_final_controlled_real_run" in content
    assert "controlled real call skipped: base real config readiness false" in content
    assert "YONLAB_AUTO_RUN_REAL_API = \"true\"" in content
    assert "Remove-Item Env:\\YONLAB_AUTO_RUN_REAL_API" in content
    assert "yonlab_auto_run_real_api_cleanup_ok" in content
    assert "execution_count = 0" in content
    assert "additional_real_api_call_count = 0" in content
    assert "service_key_exposed" in content
    assert "SECRET-KEY" not in content
    assert "G2B_API_SERVICE_KEY=<your local key>" not in content


def test_reset_local_ops_data_script_only_targets_generated_data() -> None:
    content = (PROJECT_ROOT / "scripts" / "reset_local_ops_data.ps1").read_text(
        encoding="utf-8"
    )

    assert "data\\ops" in content
    assert "data\\reports" in content
    assert "data\\downloaded" in content
    assert "data\\extracted" in content
    assert "source fixtures were not touched" in content
    assert ".env and source fixtures were not touched" in content
    assert "Remove-Item -LiteralPath $Path" in content


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
