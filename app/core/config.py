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
