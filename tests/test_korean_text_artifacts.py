from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIRS = ("app", "data/fixtures")
MOJIBAKE_FRAGMENTS = (
    "\uc11c\uc11c\uc6b8\uc6b8",
    "\ubd80\ubd80\uc0b0\uc0b0",
    "\uc9c0\uc9c0\uc5ed\uc5ed",
    "\uc2dc\uc2dc\uc2a4\uc2a4\ud15c\ud15c",
    "\ubd80\ubd80\ud569\ud569\ud569\ub2c8\ub2c8\ub2e4\ub2e4",
    "\uf9e4",
    "\u6028",
    "\uc496",
    "\ub6b0",
    "\u5a9b",
    "\u907a\ub34a\ubfc0",
)


def test_app_and_fixture_sources_do_not_contain_korean_artifact_fragments() -> None:
    scanned_files = []
    for source_dir in SOURCE_DIRS:
        for path in (PROJECT_ROOT / source_dir).rglob("*"):
            if path.is_file() and path.suffix in {".py", ".json", ".txt", ".md", ".html", ".js"}:
                scanned_files.append(path)
                content = path.read_text(encoding="utf-8")
                for fragment in MOJIBAKE_FRAGMENTS:
                    assert fragment not in content, f"{fragment!r} found in {path}"

    assert scanned_files
