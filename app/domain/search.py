from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.bid_notice import BidNotice
from app.domain.recommendation import CompactDemoRecommendation, DemoRecommendation
from app.domain.request_validation import optional_filter_value


class G2BSearchMode(StrEnum):
    FIXTURE = "fixture"
    REAL = "real"


class G2BSearchRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "mode": "fixture",
                    "keyword": "AI",
                    "num_rows": 3,
                    "active_only": False,
                    "confirm_real_api_call": False,
                }
            ]
        }
    )

    mode: G2BSearchMode = G2BSearchMode.FIXTURE
    keyword: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    page_no: int | None = Field(default=None, ge=1)
    num_rows: int | None = Field(default=None, ge=1, le=100)
    business_type: str | None = None
    region: str | None = None
    active_only: bool | None = None
    confirm_real_api_call: bool = False

    @model_validator(mode="after")
    def normalize_placeholder_search_values(self) -> "G2BSearchRequest":
        self.keyword = optional_filter_value(self.keyword)
        self.start_date = optional_filter_value(self.start_date)
        self.end_date = optional_filter_value(self.end_date)
        self.business_type = optional_filter_value(self.business_type)
        self.region = optional_filter_value(self.region)
        return self


class G2BAttachmentCandidate(BaseModel):
    sequence: int
    file_name: str = ""
    url: str = ""
    source_url_field: str
    source_file_name_field: str
    download_attempted: bool = False


class G2BDetailAnalysisQueueItem(BaseModel):
    notice_id: str
    title: str
    detail_url: str = ""
    notice_url: str = ""
    attachments: list[G2BAttachmentCandidate] = Field(default_factory=list)
    risk_metadata: dict[str, Any] = Field(default_factory=dict)
    analysis_status: str = "queued"
    download_attempted: bool = False


class G2BSearchResponse(BaseModel):
    ok: bool
    mode: G2BSearchMode
    source: str
    notices: list[BidNotice] = Field(default_factory=list)
    detail_analysis_queue: list[G2BDetailAnalysisQueueItem] = Field(default_factory=list)
    raw_count: int = 0
    message: str = ""
    error_code: str | None = None
    status_code: int | None = None
    safe_endpoint_path: str | None = None
    service_key_exposed: bool = False


class G2BRecommendationRequest(G2BSearchRequest):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "mode": "fixture",
                    "keyword": "AI",
                    "include_reports": False,
                    "active_only": False,
                    "confirm_real_api_call": False,
                }
            ]
        }
    )

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
    detail_analysis_queue: list[G2BDetailAnalysisQueueItem] = Field(default_factory=list)
    source_count: int = 0
    message: str = ""
    error_code: str | None = None
    status_code: int | None = None
    safe_endpoint_path: str | None = None
    service_key_exposed: bool = False


class G2BConfigResponse(BaseModel):
    real_api_enabled: bool
    base_url_configured: bool
    service_key_configured: bool
    default_num_rows: int
    default_page_no: int
    endpoint_path_configured: bool
    endpoint_preset: str | None = None
    endpoint_path_source: str
    fixture_mode: bool
    capture_real_responses: bool


class G2BEndpointPresetResponse(BaseModel):
    name: str
    path: str
    description: str


class G2BEndpointPresetListResponse(BaseModel):
    presets: list[G2BEndpointPresetResponse]
    message: str


class G2BRealReadinessResponse(BaseModel):
    ready: bool
    checks: dict[str, bool]
    missing: list[str]
    next_steps: list[str]
