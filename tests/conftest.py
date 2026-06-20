from collections.abc import Generator

import pytest

from app.core.config import get_settings


@pytest.fixture(autouse=True)
def safe_g2b_test_environment(monkeypatch: pytest.MonkeyPatch) -> Generator[None]:
    get_settings.cache_clear()
    monkeypatch.setenv("G2B_ENABLE_REAL_API", "false")
    monkeypatch.setenv("G2B_API_SERVICE_KEY", "")
    monkeypatch.setenv("G2B_LIST_ENDPOINT_PATH", "")
    monkeypatch.setenv("G2B_ENDPOINT_PRESET", "")
    monkeypatch.setenv("G2B_CAPTURE_REAL_RESPONSES", "false")
    yield
    get_settings.cache_clear()
