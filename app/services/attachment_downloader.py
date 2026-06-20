from urllib.parse import urlsplit

from app.domain.document_analysis import AttachmentDownloadPlanItem
from app.domain.search import G2BDetailAnalysisQueueItem

ALLOWED_ATTACHMENT_EXTENSIONS = {".pdf", ".hwp", ".hwpx"}
G2B_HOST_SUFFIX = "g2b.go.kr"


def build_attachment_download_plan_items(
    queue: list[G2BDetailAnalysisQueueItem],
    *,
    download_enabled: bool,
    confirm_attachment_download: bool,
) -> list[AttachmentDownloadPlanItem]:
    items = []
    for queue_item in queue:
        for attachment in queue_item.attachments:
            extension = _extension(attachment.file_name)
            allowed, reason = _download_decision(
                attachment.url,
                extension,
                download_enabled=download_enabled,
                confirm_attachment_download=confirm_attachment_download,
            )
            items.append(
                AttachmentDownloadPlanItem(
                    notice_id=queue_item.notice_id,
                    file_name=attachment.file_name,
                    url=attachment.url,
                    extension=extension,
                    download_allowed=allowed,
                    download_blocked_reason=reason,
                    service_key_exposed=False,
                )
            )
    return items


def _download_decision(
    url: str,
    extension: str,
    *,
    download_enabled: bool,
    confirm_attachment_download: bool,
) -> tuple[bool, str]:
    if not download_enabled:
        return False, "Attachment download is disabled by configuration."
    if not confirm_attachment_download:
        return False, "Attachment download requires confirm_attachment_download=true."
    if not _is_g2b_url(url):
        return False, "Attachment URL is not an allowed G2B domain."
    if extension not in ALLOWED_ATTACHMENT_EXTENSIONS:
        return False, "Attachment extension is not allowed."
    return True, ""


def _is_g2b_url(url: str) -> bool:
    hostname = urlsplit(url).hostname or ""
    return hostname == G2B_HOST_SUFFIX or hostname.endswith(f".{G2B_HOST_SUFFIX}")


def _extension(file_name: str) -> str:
    dot_index = file_name.rfind(".")
    if dot_index < 0:
        return ""
    return file_name[dot_index:].casefold()
