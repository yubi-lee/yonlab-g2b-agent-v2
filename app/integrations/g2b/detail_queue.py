from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from app.domain.bid_notice import BidNotice
from app.domain.search import G2BAttachmentCandidate, G2BDetailAnalysisQueueItem

ATTACHMENT_SLOT_COUNT = 10
SECRET_QUERY_KEYS = {"servicekey", "service_key", "apikey", "api_key"}


def build_detail_analysis_queue(notices: list[BidNotice]) -> list[G2BDetailAnalysisQueueItem]:
    return [build_detail_analysis_queue_item(notice) for notice in notices]


def build_detail_analysis_queue_item(notice: BidNotice) -> G2BDetailAnalysisQueueItem:
    raw_source = notice.raw_source or {}
    return G2BDetailAnalysisQueueItem(
        notice_id=notice.notice_id,
        title=notice.title,
        detail_url=_safe_url(raw_source.get("bidNtceDtlUrl")),
        notice_url=_safe_url(raw_source.get("bidNtceUrl")),
        attachments=_extract_attachments(raw_source),
        risk_metadata=_build_risk_metadata(notice, raw_source),
    )


def _extract_attachments(raw_source: dict[str, Any]) -> list[G2BAttachmentCandidate]:
    attachments = []
    for sequence in range(1, ATTACHMENT_SLOT_COUNT + 1):
        url_field = f"ntceSpecDocUrl{sequence}"
        file_name_field = f"ntceSpecFileNm{sequence}"
        url = _safe_url(raw_source.get(url_field))
        file_name = _safe_text(raw_source.get(file_name_field))
        if not url and not file_name:
            continue

        attachments.append(
            G2BAttachmentCandidate(
                sequence=sequence,
                file_name=file_name,
                url=url,
                source_url_field=url_field,
                source_file_name_field=file_name_field,
            )
        )
    return attachments


def _build_risk_metadata(notice: BidNotice, raw_source: dict[str, Any]) -> dict[str, Any]:
    joint_supply_method = _safe_text(raw_source.get("cmmnSpldmdMethdNm"))
    metadata: dict[str, Any] = {
        "contract_method": _safe_text(raw_source.get("cntrctCnclsMthdNm")),
        "successful_bid_method": _safe_text(raw_source.get("sucsfbidMthdNm")),
        "bid_method": _safe_text(raw_source.get("bidMethdNm")),
        "joint_supply_method": joint_supply_method,
        "joint_supply_region_limited": raw_source.get("cmmnSpldmdCorpRgnLmtYn") == "Y",
        "bid_participation_limited": raw_source.get("bidPrtcptLmtYn") == "Y",
        "industry_limited": raw_source.get("indstrytyLmtYn") == "Y",
        "product_classification_limited": raw_source.get("prdctClsfcLmtYn") == "Y",
        "technical_evaluation_rate": _safe_text(raw_source.get("techAbltEvlRt")),
        "price_evaluation_rate": _safe_text(raw_source.get("bidPrceEvlRt")),
        "qualification_registration_deadline": _safe_text(raw_source.get("bidQlfctRgstDt")),
        "bid_begin_at": _safe_text(raw_source.get("bidBeginDt")),
        "bid_close_at": notice.deadline or "",
        "opening_at": _safe_text(raw_source.get("opengDt")),
    }
    metadata["risk_flags"] = _risk_flags(notice, joint_supply_method, metadata)
    return metadata


def _risk_flags(
    notice: BidNotice,
    joint_supply_method: str,
    metadata: dict[str, Any],
) -> list[str]:
    flags = []
    if not metadata["bid_close_at"]:
        flags.append("missing_deadline")
    if _has_joint_supply_block(joint_supply_method):
        flags.append("joint_supply_not_allowed")
    if metadata["joint_supply_region_limited"]:
        flags.append("joint_supply_region_limited")
    if metadata["bid_participation_limited"]:
        flags.append("bid_participation_limited")
    if metadata["industry_limited"]:
        flags.append("industry_limited")
    if metadata["product_classification_limited"]:
        flags.append("product_classification_limited")
    if _numeric_rate(metadata["technical_evaluation_rate"]) >= 80:
        flags.append("high_technical_evaluation_weight")
    if not notice.raw_source.get("bidNtceDtlUrl"):
        flags.append("missing_detail_url")
    if not any(notice.raw_source.get(f"ntceSpecDocUrl{index}") for index in range(1, 11)):
        flags.append("missing_attachment_url")
    return flags


def _has_joint_supply_block(value: str) -> bool:
    value_casefolded = value.casefold()
    return any(
        token.casefold() in value_casefolded
        for token in ("joint_supply_not_allowed", "공동수급불허", "불허", "遺덊뿀")
    )


def _numeric_rate(value: Any) -> int:
    digits = "".join(character for character in str(value) if character.isdigit())
    return int(digits) if digits else 0


def _safe_text(value: Any) -> str:
    if value in (None, ""):
        return ""
    return str(value).strip()


def _safe_url(value: Any) -> str:
    url = _safe_text(value)
    if not url:
        return ""

    parsed = urlsplit(url)
    if not parsed.query:
        return url

    safe_query = [
        (key, query_value)
        for key, query_value in parse_qsl(parsed.query, keep_blank_values=True)
        if key.casefold() not in SECRET_QUERY_KEYS
    ]
    return urlunsplit(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            urlencode(safe_query, doseq=True),
            parsed.fragment,
        )
    )
