from app.core.config import Settings

PACKAGE_ROUTES = [
    "/",
    "/ui",
    "/docs",
    "/health",
    "/g2b/config",
    "/g2b/real-readiness",
    "/g2b/search",
    "/g2b/recommendations",
    "/g2b/document-risk-analysis",
    "/g2b/pdf-analysis-candidates",
    "/g2b/pdf-text-analysis",
    "/ops/package-info",
    "/ops/run-recommendations",
    "/ops/runs",
    "/ops/recommendations",
    "/ops/reports/{run_id}",
    "/ops/report-content/{run_id}/{notice_id}",
]

PACKAGE_SCRIPTS = [
    "scripts/start_local_ops.ps1",
    "scripts/validate_local.ps1",
    "scripts/validate_ops_package.ps1",
    "scripts/run_ops_fixture.ps1",
    "scripts/show_ops_runs.ps1",
    "scripts/show_ops_recommendations.ps1",
    "scripts/open_latest_report_dir.ps1",
    "scripts/reset_local_ops_data.ps1",
]

PACKAGE_CAPABILITIES = [
    "FastAPI server and Swagger API",
    "Browser dashboard at /ui",
    "Fixture-based recommendation run",
    "Guarded real G2B API path",
    "Recommendation scoring and Korean markdown reports",
    "Document/PDF risk planning layer",
    "Local SQLite operations storage",
    "Saved report content endpoint",
]


def build_local_ops_package_info(settings: Settings) -> dict[str, object]:
    return {
        "package_name": settings.yonlab_local_ops_package_name,
        "package_version": settings.yonlab_local_ops_package_version,
        "app_name": settings.app_name,
        "app_version": settings.app_version,
        "runtime_mode": "local_operations",
        "default_run_mode": settings.yonlab_default_run_mode,
        "default_keyword": settings.yonlab_default_keyword,
        "default_num_rows": settings.yonlab_default_num_rows,
        "fixture_mode": settings.g2b_fixture_mode,
        "real_api_enabled": settings.g2b_enable_real_api,
        "auto_real_api_run_enabled": settings.yonlab_auto_run_real_api,
        "service_key_configured": bool(settings.g2b_api_service_key),
        "service_key_exposed": False,
        "storage": {
            "backend": "sqlite",
            "db_path_configured": bool(settings.yonlab_storage_db_path),
            "report_dir_configured": bool(settings.yonlab_report_dir),
            "db_path": _safe_local_path(settings.yonlab_storage_db_path),
            "report_dir": _safe_local_path(settings.yonlab_report_dir),
        },
        "ui": {
            "dashboard_route": "/ui",
            "static_assets_route": "/ui/static",
        },
        "routes": PACKAGE_ROUTES,
        "scripts": PACKAGE_SCRIPTS,
        "capabilities": PACKAGE_CAPABILITIES,
        "validation": {
            "pytest": "python -m pytest -q",
            "local": "scripts/validate_local.ps1",
            "package": "scripts/validate_ops_package.ps1",
        },
        "safety": {
            "real_api_default": "disabled",
            "real_api_requires_confirmation": True,
            "tests_call_real_api": False,
            "secrets_returned": False,
        },
    }


def _safe_local_path(path: str) -> str:
    normalized = path.replace("\\", "/").strip()
    if normalized.startswith(("data/", "./data/")):
        return normalized.lstrip("./")
    return "configured"
