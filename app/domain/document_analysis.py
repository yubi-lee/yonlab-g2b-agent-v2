from pydantic import BaseModel, Field

from app.domain.search import G2BSearchRequest


class RiskKeywordHit(BaseModel):
    code: str
    label: str
    severity: str
    matched_terms: list[str] = Field(default_factory=list)
    evidence: str = ""
    recommendation: str = ""


class DocumentRiskAnalysisResult(BaseModel):
    source_name: str
    analysis_mode: str
    text_length: int
    risk_hits: list[RiskKeywordHit] = Field(default_factory=list)
    positive_hits: list[RiskKeywordHit] = Field(default_factory=list)
    summary: str
    service_key_exposed: bool = False


class PdfTextExtractionResult(BaseModel):
    file_name: str
    source: str
    page_count: int = 0
    text: str = ""
    text_length: int = 0
    extraction_ok: bool = False
    message: str = ""


class PdfAnalysisCandidate(BaseModel):
    notice_id: str
    title: str
    agency: str
    file_name: str
    url: str
    extension: str
    analysis_allowed: bool
    analysis_mode: str
    priority: int
    reason: str
    risk_hints: list[str] = Field(default_factory=list)


class DocumentRiskAnalysisRequest(BaseModel):
    source_name: str = "sample-rfp-text"
    text: str
    include_positive_signals: bool = True


class PdfAnalysisCandidatesRequest(G2BSearchRequest):
    pass


class PdfAnalysisCandidatesResponse(BaseModel):
    ok: bool
    mode: str
    source: str
    candidates: list[PdfAnalysisCandidate] = Field(default_factory=list)
    source_count: int = 0
    message: str = ""
    service_key_exposed: bool = False


class PdfTextAnalysisRequest(BaseModel):
    file_path: str
    source_name: str = ""
    confirm_pdf_analysis: bool = False


class PdfTextAnalysisResponse(BaseModel):
    ok: bool
    extraction: PdfTextExtractionResult
    risk_analysis: DocumentRiskAnalysisResult | None = None
    message: str
    service_key_exposed: bool = False


class AttachmentDownloadPlanItem(BaseModel):
    notice_id: str
    file_name: str
    url: str
    extension: str
    download_allowed: bool
    download_blocked_reason: str
    service_key_exposed: bool = False


class AttachmentDownloadPlanResponse(BaseModel):
    ok: bool
    mode: str
    source: str
    download_enabled: bool
    confirm_attachment_download: bool
    items: list[AttachmentDownloadPlanItem] = Field(default_factory=list)
    message: str
    service_key_exposed: bool = False


class AttachmentDownloadPlanRequest(G2BSearchRequest):
    confirm_attachment_download: bool = False


class AttachmentAnalysisPlanItem(BaseModel):
    notice_id: str
    file_name: str
    url: str
    extension: str
    analysis_mode: str
    analysis_allowed: bool
    reason: str


class AttachmentAnalysisPlanResponse(BaseModel):
    ok: bool
    mode: str
    source: str
    items: list[AttachmentAnalysisPlanItem] = Field(default_factory=list)
    pdf_candidates: list[PdfAnalysisCandidate] = Field(default_factory=list)
    message: str
    service_key_exposed: bool = False
