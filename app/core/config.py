from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    app_env: str = "local"
    app_name: str = "YOnLab G2B Agent v2"
    app_version: str = "1.0.0-local"

    g2b_enable_real_api: bool = False
    g2b_api_base_url: str = "https://apis.data.go.kr"
    g2b_api_service_key: str = ""
    g2b_request_timeout_seconds: int = 15
    g2b_default_num_rows: int = 10
    g2b_default_page_no: int = 1
    g2b_list_endpoint_path: str = ""
    g2b_endpoint_preset: str = ""
    g2b_fixture_mode: bool = True
    g2b_capture_real_responses: bool = False
    g2b_capture_dir: str = "data/captured/g2b"
    g2b_enable_pdf_text_extraction: bool = False
    g2b_pdf_max_bytes: int = 20_000_000
    g2b_pdf_extracted_text_dir: str = "data/extracted/g2b"
    g2b_enable_attachment_download: bool = False
    g2b_attachment_max_bytes: int = 20_000_000

    yonlab_storage_db_path: str = "data/ops/yonlab_g2b_agent.sqlite3"
    yonlab_report_dir: str = "data/reports/g2b"
    yonlab_default_run_mode: str = "fixture"
    yonlab_default_keyword: str = "AI"
    yonlab_default_num_rows: int = 10
    yonlab_auto_run_real_api: bool = False
    yonlab_local_ops_package_name: str = "YOnLab G2B Agent v2 Local Operations"
    yonlab_local_ops_package_version: str = "1.0"

    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
