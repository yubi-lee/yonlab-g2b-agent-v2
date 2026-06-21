from collections.abc import Generator
from pathlib import Path

import pytest

from app.core.config import get_settings


def pytest_configure(config: pytest.Config) -> None:
    requested_basetemp = getattr(config.option, "basetemp", None)
    candidates = [
        Path(requested_basetemp) if requested_basetemp else Path.cwd() / ".pytest_tmp",
        Path.home() / "OneDrive" / "문서" / "YOnLab G2B Agent v2" / ".pytest_tmp",
    ]
    for candidate in candidates:
        if _can_use_basetemp(candidate):
            config.option.basetemp = str(candidate)
            return


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


def _can_use_basetemp(path: Path) -> bool:
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".write_probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
    except OSError:
        return False
    return True
