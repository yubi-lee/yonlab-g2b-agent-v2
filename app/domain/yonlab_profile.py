from pydantic import BaseModel, Field


class YOnLabProfile(BaseModel):
    company_name: str
    english_name: str
    ceo: str
    location: str
    company_size: list[str] = Field(default_factory=list)
    startup_status: list[str] = Field(default_factory=list)
    core_qualifications: list[str] = Field(default_factory=list)
    procurement_categories: list[str] = Field(default_factory=list)
    technical_keywords: list[str] = Field(default_factory=list)
    region_priority: list[str] = Field(default_factory=list)

    @property
    def core_qualification(self) -> str:
        return self.core_qualifications[0] if self.core_qualifications else ""


def default_yonlab_profile() -> YOnLabProfile:
    return YOnLabProfile(
        company_name="주식회사 와이온랩",
        english_name="YOnLab",
        ceo="이근영",
        location="서울특별시 강남구",
        company_size=["소기업", "소상공인"],
        startup_status=["초기창업기업"],
        core_qualifications=[
            "소프트웨어사업자",
            "패키지소프트웨어개발 공급사업",
            "컴퓨터관련서비스사업",
        ],
        procurement_categories=[
            "인공지능소프트웨어",
            "정보시스템개발서비스",
            "패키지소프트웨어개발및도입서비스",
            "클라우드소프트웨어",
            "시스템관리소프트웨어",
        ],
        technical_keywords=[
            "온디바이스 AI",
            "Device Farm",
            "AI/SW 원격 검증",
            "로봇 AI",
            "산업용 AI",
            "AI Agent",
            "클라우드 시스템",
            "NPU",
            "AI 소프트웨어 개발",
        ],
        region_priority=["서울", "수도권", "전국"],
    )
