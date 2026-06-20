from pathlib import Path
from typing import Any

from app.domain.document_analysis import PdfTextExtractionResult


def extract_pdf_text_from_file(
    file_path: str,
    *,
    max_bytes: int,
    source: str = "local_file",
) -> PdfTextExtractionResult:
    path = Path(file_path)
    file_name = path.name
    if path.suffix.casefold() != ".pdf":
        return _blocked(file_name, source, "Only local PDF files are supported.")
    if not path.is_file():
        return _blocked(file_name, source, "PDF file does not exist.")

    try:
        file_size = path.stat().st_size
    except OSError:
        return _blocked(file_name, source, "PDF file metadata could not be read.")
    if file_size > max_bytes:
        return _blocked(file_name, source, "PDF file exceeds the configured maximum size.")

    try:
        from pypdf import PdfReader  # type: ignore[import-not-found]
    except ImportError:
        return _blocked(file_name, source, "PDF text extraction dependency is not available.")

    try:
        reader = PdfReader(str(path))
        page_text = [_safe_page_text(page) for page in reader.pages]
    except Exception:
        return _blocked(file_name, source, "PDF text extraction failed.")

    text = "\n".join(part for part in page_text if part).strip()
    return PdfTextExtractionResult(
        file_name=file_name,
        source=source,
        page_count=len(reader.pages),
        text=text,
        text_length=len(text),
        extraction_ok=True,
        message="PDF text extracted.",
    )


def _safe_page_text(page: Any) -> str:
    try:
        return page.extract_text() or ""
    except Exception:
        return ""


def _blocked(file_name: str, source: str, message: str) -> PdfTextExtractionResult:
    return PdfTextExtractionResult(
        file_name=file_name,
        source=source,
        page_count=0,
        text="",
        text_length=0,
        extraction_ok=False,
        message=message,
    )
