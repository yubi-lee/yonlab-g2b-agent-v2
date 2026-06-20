from enum import StrEnum

from pydantic import BaseModel, Field

from app.domain.bid_notice import BidNotice
from app.domain.recommendation import CompactDemoRecommendation, DemoRecommendation


class G2BSearchMode(StrEnum):
    FIXTURE = "fixture"
    REAL = "real"


class G2BSearchRequest(BaseModel):
    mode: G2BSearchMode = G2BSearchMode.FIXTURE
    keyword: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    page_no: int | None = Field(default=None, ge=1)
    num_rows: int | None = Field(default=None, ge=1, le=100)
    business_type: str | None = None
    region: str | None = None
    confirm_real_api_call: bool = False


class G2BSearchResponse(BaseModel):
    ok: bool
    mode: G2BSearchMode
    source: str
    notices: list[BidNotice] = Field(default_factory=list)
    raw_count: int = 0
    message: str = ""
    error_code: str | None = None


class G2BRecommendationRequest(G2BSearchRequest):
    include_reports: bool = False


class G2BRecommendationResponse(BaseModel):
    ok: bool
    mode: G2BSearchMode
    source: str
    include_reports: bool
    recommendations: list[DemoRecommendation | CompactDemoRecommendation] = Field(
        default_factory=list
    )
    ranked_order: list[str] = Field(default_factory=list)
    source_count: int = 0
    message: str = ""
    error_code: str | None = None


class G2BConfigResponse(BaseModel):
    real_api_enabled: bool
    base_url_configured: bool
    service_key_configured: bool
    default_num_rows: int
    default_page_no: int
    endpoint_path_configured: bool
    fixture_mode: bool
