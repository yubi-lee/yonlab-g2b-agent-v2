from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_smoke_scripts_exist() -> None:
    assert (PROJECT_ROOT / "scripts" / "smoke_demo.ps1").is_file()
    assert (PROJECT_ROOT / "scripts" / "smoke_report.ps1").is_file()


def test_gitattributes_contains_line_ending_policy() -> None:
    content = (PROJECT_ROOT / ".gitattributes").read_text(encoding="utf-8")

    assert "*.py text eol=lf" in content
    assert "*.ps1 text eol=crlf" in content
