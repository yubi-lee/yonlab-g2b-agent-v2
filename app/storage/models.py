from typing import Any

from pydantic import BaseModel, Field

from app.domain.search import G2BSearchMode


class OpsRunRequest(BaseModel):
    mode: G2BSearchMode | None = None
    keyword: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    page_no: int | None = Field(default=None, ge=1)
    num_rows: int | None = Field(default=None, ge=1, le=100)
    include_reports: bool = True
    active_only: bool | None = None
    confirm_real_api_call: bool = False


class OperationsRunSummary(BaseModel):
    run_id: str
    status: str
    mode: str
    keyword: str | None = None
    source_count: int = 0
    recommendation_count: int = 0
    report_count: int = 0
    message: str = ""
    error_code: str | None = None
    service_key_exposed: bool = False


class StoredSearchRun(BaseModel):
    run_id: str
    created_at: str
    mode: str
    keyword: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    num_rows: int | None = None
    source_count: int = 0
    status: str
    message: str = ""
    error_code: str | None = None
    service_key_exposed: bool = False


class StoredRecommendation(BaseModel):
    run_id: str
    rank: int
    notice_id: str
    title: str
    agency: str
    budget_amount: int | None = None
    deadline: str | None = None
    total_score: int
    recommendation_label: str
    risk_count: int
    top_reasons: list[str] = Field(default_factory=list)
    risk_summaries: list[str] = Field(default_factory=list)
    detail_url: str = ""
    report_path: str = ""
    raw_json_path: str = ""
    created_at: str


class StoredReport(BaseModel):
    run_id: str
    notice_id: str
    title: str
    report_path: str
    created_at: str


class OperationsRunDetail(BaseModel):
    run: dict[str, Any] | None
    recommendations: list[dict[str, Any]] = Field(default_factory=list)
    reports: list[dict[str, Any]] = Field(default_factory=list)

