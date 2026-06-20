from dataclasses import dataclass, field


@dataclass(frozen=True)
class YOnLabProfile:
    company_name: str
    location: str
    company_size: str
    startup_status: str
    core_qualification: str
    procurement_categories: tuple[str, ...] = field(default_factory=tuple)
    technical_keywords: tuple[str, ...] = field(default_factory=tuple)


def default_yonlab_profile() -> YOnLabProfile:
    return YOnLabProfile(
        company_name="주식회사 와이온랩",
        location="서울특별시 강남구",
        company_size="소기업 / 소상공인",
        startup_status="초기창업기업",
        core_qualification="소프트웨어사업자",
        procurement_categories=(
            "인공지능소프트웨어",
            "정보시스템개발서비스",
            "패키지소프트웨어개발및도입서비스",
            "클라우드소프트웨어",
            "시스템관리소프트웨어",
        ),
        technical_keywords=(
            "온디바이스 AI",
            "Device Farm",
            "AI/SW 원격 검증",
            "로봇 AI",
            "AI Agent",
            "클라우드 시스템",
        ),
    )
