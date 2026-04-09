from typing import Literal

from pydantic import BaseModel, Field


SupportedLanguage = Literal["ar", "fr", "en"]
ConfidenceBand = Literal["low", "medium", "high"]
UrgencyLevel = Literal["low", "medium", "high"]


class AgroCopilotDiagnosisRequest(BaseModel):
    farmer_note: str = Field(min_length=1, max_length=2000)
    observed_symptoms: list[str] = Field(default_factory=list, max_length=30)
    language: SupportedLanguage | None = None
    image_urls: list[str] = Field(default_factory=list, max_length=5)
    image_base64: str | None = None
    image_path: str | None = None


class AgroCopilotChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    observed_symptoms: list[str] = Field(default_factory=list, max_length=30)
    language: SupportedLanguage | None = None
    image_urls: list[str] = Field(default_factory=list, max_length=5)
    image_base64: str | None = None
    image_path: str | None = None


class AgroCopilotEvidenceSource(BaseModel):
    source_id: str
    title: str
    url: str
    publisher: str
    accessed_on: str
    trust_level: str


class AgroCopilotClassProbability(BaseModel):
    label: str
    score: float


class AgroCopilotClassifierDebug(BaseModel):
    predicted_label: str
    gated_label: str
    score: float
    top1_top2_margin: float | None = None
    gate_reason: str | None = None
    confidence_band: ConfidenceBand
    source: str
    top_k: list[AgroCopilotClassProbability] = Field(default_factory=list)
    trace: str


class AgroCopilotDiagnosisResponse(BaseModel):
    probable_issue: str
    confidence_band: ConfidenceBand
    alternative_causes: list[str]
    why_it_thinks_that: list[str]
    what_to_check_next: list[str]
    urgency: UrgencyLevel
    safe_actions: list[str]
    when_to_call_agronomist: str
    recommended_followup_questions: list[str]
    language: SupportedLanguage
    model_trace_summary: str
    matched_category: str | None = None
    matched_subcategory: str | None = None
    evidence_sources: list[AgroCopilotEvidenceSource] = Field(default_factory=list)
    classifier_debug: AgroCopilotClassifierDebug | None = None


class AgroCopilotKnowledgeSource(BaseModel):
    source_id: str
    title: str
    url: str
    publisher: str
    accessed_on: str
    trust_level: str
