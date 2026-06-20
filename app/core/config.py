from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    app_env: str = "local"
    app_name: str = "YOnLab G2B Agent v2"

    g2b_enable_real_api: bool = False
    g2b_api_base_url: str = "https://apis.data.go.kr"
    g2b_api_service_key: str = ""
    g2b_request_timeout_seconds: int = 15
    g2b_default_num_rows: int = 10
    g2b_default_page_no: int = 1
    g2b_list_endpoint_path: str = ""
    g2b_fixture_mode: bool = True
    g2b_capture_real_responses: bool = False
    g2b_capture_dir: str = "data/captured/g2b"

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
