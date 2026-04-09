import json
import os
from pathlib import Path
from typing import Any
from urllib import error, request

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover
    load_dotenv = None

from backend.app.models.diagnosis import DiagnosisRequest, DiagnosisResponse, SupportedLanguage
from backend.app.services.retrieval import RetrievedCase, localize_map_list, localize_map_text

if load_dotenv is not None:
    load_dotenv()
    load_dotenv("backend/.env")


OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
OPENAI_TIMEOUT_SECONDS = float(os.getenv("OPENAI_TIMEOUT_SECONDS", "45"))


def _build_image_data_url(payload: DiagnosisRequest) -> str | None:
    if payload.image_base64:
        raw = payload.image_base64.strip()
        if raw.startswith("data:image/"):
            return raw
        return f"data:image/jpeg;base64,{raw}"

    if payload.image_path:
        p = Path(payload.image_path)
        if p.exists() and p.is_file():
            import base64

            return "data:image/jpeg;base64," + base64.b64encode(p.read_bytes()).decode("ascii")
    return None


def _build_knowledge_context(retrieved: list[RetrievedCase], language: SupportedLanguage) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in retrieved:
        entry = item.entry
        rows.append(
            {
                "id": entry.id,
                "score": item.score,
                "category": entry.category,
                "subcategory": entry.subcategory,
                "probable_issue": localize_map_text(entry.probable_issue, language),
                "confidence_hint": entry.confidence_hint,
                "urgency_hint": entry.urgency_hint,
                "alternative_causes": localize_map_list(entry.alternative_causes, language),
                "why_it_thinks_that": localize_map_list(entry.why_it_thinks_that, language),
                "what_to_check_next": localize_map_list(entry.what_to_check_next, language),
                "safe_actions": localize_map_list(entry.safe_actions, language),
                "when_to_call_agronomist": localize_map_text(entry.when_to_call_agronomist, language),
                "recommended_followup_questions": localize_map_list(entry.recommended_followup_questions, language),
                "source_ids": list(entry.source_ids),
            }
        )
    return rows


def _chat_completion(messages: list[dict[str, str]]) -> str | None:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None

    body = {
        "model": OPENAI_MODEL,
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
        "messages": messages,
    }
    data = json.dumps(body).encode("utf-8")
    req = request.Request(
        f"{OPENAI_BASE_URL}/chat/completions",
        data=data,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
    )
    try:
        with request.urlopen(req, timeout=OPENAI_TIMEOUT_SECONDS) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
            return payload["choices"][0]["message"]["content"]
    except (error.URLError, error.HTTPError, KeyError, IndexError, json.JSONDecodeError):
        return None


def describe_leaf_image(payload: DiagnosisRequest, language: SupportedLanguage) -> str | None:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None

    image_data_url = _build_image_data_url(payload)
    if not image_data_url:
        return None

    lang_map = {"en": "English", "fr": "French", "ar": "Arabic"}
    out_lang = lang_map.get(language, "English")

    body = {
        "model": OPENAI_MODEL,
        "temperature": 0.1,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a plant-vision assistant. Describe only visible olive leaf findings. "
                    "Do not diagnose with certainty. Keep it short (max 80 words)."
                ),
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            f"Describe what you see in this olive leaf image in {out_lang}. "
                            "Focus on visible patterns (spots, halo, lesions, color, insect traces)."
                        ),
                    },
                    {"type": "image_url", "image_url": {"url": image_data_url}},
                ],
            },
        ],
    }

    data = json.dumps(body).encode("utf-8")
    req = request.Request(
        f"{OPENAI_BASE_URL}/chat/completions",
        data=data,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
    )
    try:
        with request.urlopen(req, timeout=OPENAI_TIMEOUT_SECONDS) as resp:
            payload_json = json.loads(resp.read().decode("utf-8"))
            return str(payload_json["choices"][0]["message"]["content"]).strip()
    except Exception:
        return None


def maybe_generate_grounded_response(
    payload: DiagnosisRequest,
    fallback: DiagnosisResponse,
    retrieved: list[RetrievedCase],
    evidence_sources: list[dict[str, str]],
    classifier_trace: str | None,
    language: SupportedLanguage,
) -> DiagnosisResponse:
    if not retrieved:
        return fallback

    context = {
        "user_input": {
            "farmer_note": payload.farmer_note,
            "observed_symptoms": payload.observed_symptoms,
            "language": language,
        },
        "classifier_trace": classifier_trace or "",
        "knowledge_entries": _build_knowledge_context(retrieved, language),
        "evidence_sources": evidence_sources,
        "response_schema_keys": [
            "probable_issue",
            "confidence_band",
            "alternative_causes",
            "why_it_thinks_that",
            "what_to_check_next",
            "urgency",
            "safe_actions",
            "when_to_call_agronomist",
            "recommended_followup_questions",
            "language",
            "model_trace_summary",
        ],
    }

    system_prompt = (
        "You are an olive agronomy assistant. Use ONLY the provided grounded context. "
        "Do not hallucinate, do not claim certainty, be conservative and safety-first. "
        "Return JSON only with the required keys. Keep language exactly as requested (ar, fr, en). "
        "Set low confidence if evidence is weak or conflicting. "
        "Include short grounded rationale in model_trace_summary and mention evidence source ids."
    )
    user_prompt = (
        "Build the final diagnosis JSON from this grounded context. "
        "If uncertain, include alternatives and checks before treatment.\n\n"
        f"{json.dumps(context, ensure_ascii=False)}"
    )

    content = _chat_completion(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
    )
    if not content:
        return fallback

    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        return fallback

    try:
        return DiagnosisResponse(
            probable_issue=str(parsed.get("probable_issue", fallback.probable_issue)),
            confidence_band=parsed.get("confidence_band", fallback.confidence_band),
            alternative_causes=list(parsed.get("alternative_causes", fallback.alternative_causes)),
            why_it_thinks_that=list(parsed.get("why_it_thinks_that", fallback.why_it_thinks_that)),
            what_to_check_next=list(parsed.get("what_to_check_next", fallback.what_to_check_next)),
            urgency=parsed.get("urgency", fallback.urgency),
            safe_actions=list(parsed.get("safe_actions", fallback.safe_actions)),
            when_to_call_agronomist=str(parsed.get("when_to_call_agronomist", fallback.when_to_call_agronomist)),
            recommended_followup_questions=list(
                parsed.get("recommended_followup_questions", fallback.recommended_followup_questions)
            ),
            language=language,
            model_trace_summary=str(parsed.get("model_trace_summary", fallback.model_trace_summary)),
            matched_category=fallback.matched_category,
            matched_subcategory=fallback.matched_subcategory,
            evidence_sources=evidence_sources,
            classifier_debug=fallback.classifier_debug,
        )
    except Exception:
        return fallback
