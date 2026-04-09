from fastapi import APIRouter

from backend.app.models.diagnosis import ChatRequest, DiagnosisRequest, DiagnosisResponse
from backend.app.services.diagnosis_service import build_diagnosis
from backend.app.services.retrieval import load_knowledge_bundle


router = APIRouter()


@router.post("/diagnose", response_model=DiagnosisResponse)
def diagnose(payload: DiagnosisRequest) -> DiagnosisResponse:
    return build_diagnosis(payload)


@router.post("/chat", response_model=DiagnosisResponse)
def chat(payload: ChatRequest) -> DiagnosisResponse:
    diagnosis_payload = DiagnosisRequest(
        farmer_note=payload.message,
        observed_symptoms=payload.observed_symptoms,
        language=payload.language,
        image_urls=payload.image_urls,
        image_base64=payload.image_base64,
        image_path=payload.image_path,
    )
    return build_diagnosis(diagnosis_payload)


@router.get("/knowledge/sources")
def list_knowledge_sources() -> list[dict[str, str]]:
    bundle = load_knowledge_bundle()
    rows: list[dict[str, str]] = []
    for source in bundle.sources_by_id.values():
        rows.append(
            {
                "source_id": source.id,
                "title": source.title,
                "url": source.url,
                "publisher": source.publisher,
                "accessed_on": source.accessed_on,
                "trust_level": source.trust_level,
            }
        )
    rows.sort(key=lambda x: x["source_id"])
    return rows
