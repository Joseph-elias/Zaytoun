from fastapi import APIRouter
from fastapi import HTTPException

from backend.app.models.diagnosis import ChatRequest, DiagnosisRequest, DiagnosisResponse
from backend.app.services.chat_memory import (
    delete_session,
    ensure_session,
    get_conversation_history,
    list_sessions,
    normalize_session_id,
)
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
        session_id=payload.session_id,
        image_urls=payload.image_urls,
        image_base64=payload.image_base64,
        image_path=payload.image_path,
    )
    return build_diagnosis(diagnosis_payload)


@router.post("/chat/sessions")
def create_chat_session() -> dict[str, str]:
    session_id = ensure_session(None)
    return {"session_id": session_id}


@router.get("/chat/sessions")
def get_chat_sessions() -> list[dict[str, str]]:
    return list_sessions()


@router.get("/chat/sessions/{session_id}/history")
def get_chat_session_history(session_id: str) -> dict[str, object]:
    key = normalize_session_id(session_id)
    if not key:
        raise HTTPException(status_code=404, detail="Session not found")
    history = get_conversation_history(key)
    if not history:
        rows = list_sessions()
        if not any(row.get("session_id") == key for row in rows):
            raise HTTPException(status_code=404, detail="Session not found")
    return {"session_id": key, "history": history}


@router.delete("/chat/sessions/{session_id}")
def remove_chat_session(session_id: str) -> dict[str, object]:
    key = normalize_session_id(session_id)
    if not key:
        raise HTTPException(status_code=404, detail="Session not found")
    removed = delete_session(key)
    if not removed:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"ok": True, "session_id": key}


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
