from app.domain.document_analysis import AttachmentAnalysisPlanItem, PdfAnalysisCandidate
from app.domain.search import G2BDetailAnalysisQueueItem


def build_pdf_analysis_candidates(
    queue: list[G2BDetailAnalysisQueueItem],
) -> list[PdfAnalysisCandidate]:
    candidates = []
    for queue_item in queue:
        for attachment in queue_item.attachments:
            extension = _extension(attachment.file_name)
            if extension != ".pdf":
                continue
            candidates.append(
                PdfAnalysisCandidate(
                    notice_id=queue_item.notice_id,
                    title=queue_item.title,
                    agency=str(queue_item.risk_metadata.get("agency", "")),
                    file_name=attachment.file_name,
                    url=attachment.url,
                    extension=extension,
                    analysis_allowed=True,
                    analysis_mode="metadata_only_until_downloaded",
                    priority=_priority(queue_item.risk_metadata.get("risk_flags", [])),
                    reason=(
                        "PDF attachment metadata can be queued for controlled local text "
                        "analysis."
                    ),
                    risk_hints=list(queue_item.risk_metadata.get("risk_flags", [])),
                )
            )
    return candidates


def build_attachment_analysis_plan_items(
    queue: list[G2BDetailAnalysisQueueItem],
) -> list[AttachmentAnalysisPlanItem]:
    items = []
    for queue_item in queue:
        for attachment in queue_item.attachments:
            extension = _extension(attachment.file_name)
            analysis_allowed = extension == ".pdf"
            reason = "PDF can be analyzed after controlled local extraction."
            analysis_mode = "pdf_text_candidate"
            if extension in {".hwp", ".hwpx"}:
                reason = "HWP/HWPX content extraction is not implemented; manual review required."
                analysis_mode = "manual_review_required"
            elif extension != ".pdf":
                reason = "Unsupported attachment type for automatic analysis."
                analysis_mode = "unsupported"
            items.append(
                AttachmentAnalysisPlanItem(
                    notice_id=queue_item.notice_id,
                    file_name=attachment.file_name,
                    url=attachment.url,
                    extension=extension,
                    analysis_mode=analysis_mode,
                    analysis_allowed=analysis_allowed,
                    reason=reason,
                )
            )
    return items


def _extension(file_name: str) -> str:
    dot_index = file_name.rfind(".")
    if dot_index < 0:
        return ""
    return file_name[dot_index:].casefold()


def _priority(risk_flags: object) -> int:
    if not isinstance(risk_flags, list):
        return 3
    high_priority_flags = {
        "missing_deadline",
        "joint_supply_not_allowed",
        "industry_limited",
        "high_technical_evaluation_weight",
    }
    return 1 if any(flag in high_priority_flags for flag in risk_flags) else 3
