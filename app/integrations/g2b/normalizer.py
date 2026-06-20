from typing import Any

from app.domain.bid_notice import BidNotice

FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "notice_id": ("notice_id", "bidNtceNo", "공고번호", "입찰공고번호"),
    "title": ("title", "bidNtceNm", "공고명", "입찰공고명"),
    "agency": ("agency", "dminsttNm", "수요기관", "발주처", "기관명"),
    "budget_amount": ("budget_amount", "asignBdgtAmt", "추정가격", "예산", "배정예산"),
    "deadline": ("deadline", "bidClseDt", "입찰마감일시", "마감일", "마감일시"),
    "region": ("region", "지역제한", "지역", "regionRestriction"),
    "contract_type": ("contract_type", "계약유형", "계약방법", "cntrctMthdNm", "cntrctCnclsMthdNm"),
    "business_type": ("business_type", "업무구분", "사업유형", "bsnsDivNm", "srvceDivNm"),
    "qualification_text": ("qualification_text", "참가자격", "입찰참가자격", "qualification"),
    "description": ("description", "과업내용", "세부내용", "descriptionText", "ntceInsttOfcl"),
    "keywords": ("keywords", "키워드", "검색키워드"),
}


def normalize_g2b_notice(raw_notice: dict[str, Any] | BidNotice) -> BidNotice:
    if isinstance(raw_notice, BidNotice):
        return raw_notice

    normalized: dict[str, Any] = {}
    for target, aliases in FIELD_ALIASES.items():
        value = _first_present(raw_notice, aliases)
        if value is not None:
            normalized[target] = value

    normalized["budget_amount"] = _parse_budget(normalized.get("budget_amount"))
    normalized["keywords"] = _normalize_keywords(normalized.get("keywords"), raw_notice)
    normalized["categories"] = _build_categories(raw_notice)
    normalized["requirements"] = _build_requirements(raw_notice)
    normalized["restrictions"] = _build_restrictions(raw_notice)
    normalized["description"] = _build_description(normalized.get("description"), raw_notice)
    normalized["qualification_text"] = _build_qualification_text(
        normalized.get("qualification_text"),
        normalized["requirements"],
        normalized["restrictions"],
    )
    normalized["raw_source"] = raw_notice

    return BidNotice(**normalized)


def _first_present(raw_notice: dict[str, Any], aliases: tuple[str, ...]) -> Any:
    for alias in aliases:
        if alias in raw_notice and raw_notice[alias] not in (None, ""):
            return raw_notice[alias]
    return None


def _parse_budget(value: Any) -> int | None:
    if value in (None, ""):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)

    digits = "".join(character for character in str(value) if character.isdigit())
    return int(digits) if digits else None


def _normalize_keywords(value: Any, raw_notice: dict[str, Any]) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        separator = "," if "," in value else " "
        return [item.strip() for item in value.split(separator) if item.strip()]

    text = " ".join(
        str(raw_notice.get(key, ""))
        for key in ("공고명", "bidNtceNm", "title", "과업내용", "description", "참가자격")
    )
    inferred = []
    for keyword in ("AI", "인공지능", "소프트웨어", "정보시스템", "클라우드", "Device Farm", "NPU"):
        if keyword.casefold() in text.casefold():
            inferred.append(keyword)
    return inferred


def _build_categories(raw_notice: dict[str, Any]) -> list[str]:
    categories = []
    for key in (
        "pubPrcrmntLrgClsfcNm",
        "pubPrcrmntMidClsfcNm",
        "pubPrcrmntClsfcNo",
        "pubPrcrmntClsfcNm",
        "purchsObjPrdctList",
    ):
        value = raw_notice.get(key)
        if value not in (None, ""):
            categories.append(str(value).strip())
    return _dedupe(categories)


def _build_requirements(raw_notice: dict[str, Any]) -> list[str]:
    requirements = []
    for key in ("cntrctCnclsMthdNm", "sucsfbidMthdNm", "bidMethdNm"):
        value = raw_notice.get(key)
        if value not in (None, ""):
            requirements.append(str(value).strip())

    tech_rate = raw_notice.get("techAbltEvlRt")
    if tech_rate not in (None, ""):
        requirements.append(f"기술평가비율 {tech_rate}")
    price_rate = raw_notice.get("bidPrceEvlRt")
    if price_rate not in (None, ""):
        requirements.append(f"가격평가비율 {price_rate}")
    return _dedupe(requirements)


def _build_restrictions(raw_notice: dict[str, Any]) -> list[str]:
    restrictions = []
    joint_supply = str(raw_notice.get("cmmnSpldmdMethdNm", "")).strip()
    if joint_supply:
        restrictions.append(joint_supply)
    if "공동수급불허" in joint_supply:
        restrictions.append("공동수급불허")
    if raw_notice.get("cmmnSpldmdCorpRgnLmtYn") == "Y":
        restrictions.append("공동수급 지역제한 있음")
    if raw_notice.get("bidPrtcptLmtYn") == "Y":
        restrictions.append("입찰참가제한 있음")
    if raw_notice.get("indstrytyLmtYn") == "Y":
        restrictions.append("업종제한 있음")
    if raw_notice.get("prdctClsfcLmtYn") == "Y":
        restrictions.append("물품분류제한 있음")
    return _dedupe(restrictions)


def _build_description(current_description: Any, raw_notice: dict[str, Any]) -> str:
    parts = []
    if current_description not in (None, ""):
        parts.append(str(current_description).strip())
    for key in (
        "cntrctCnclsMthdNm",
        "srvceDivNm",
        "bidMethdNm",
        "sucsfbidMthdNm",
        "pubPrcrmntLrgClsfcNm",
        "pubPrcrmntMidClsfcNm",
        "pubPrcrmntClsfcNm",
        "purchsObjPrdctList",
    ):
        value = raw_notice.get(key)
        if value not in (None, ""):
            parts.append(str(value).strip())
    return " ".join(_dedupe(parts))


def _build_qualification_text(
    current_qualification: Any,
    requirements: list[str],
    restrictions: list[str],
) -> str:
    parts = []
    if current_qualification not in (None, ""):
        parts.append(str(current_qualification).strip())
    parts.extend(requirements)
    parts.extend(restrictions)
    return " ".join(_dedupe(parts))


def _dedupe(values: list[str]) -> list[str]:
    deduped = []
    seen = set()
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        deduped.append(value)
    return deduped
