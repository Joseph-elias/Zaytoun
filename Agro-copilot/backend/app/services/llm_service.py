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
CONVERSATIONAL_ONLY = str(os.getenv("LLM_CONVERSATIONAL_ONLY", "true")).strip().lower() in {"1", "true", "yes", "on"}


def llm_is_available() -> bool:
    return bool(str(os.getenv("OPENAI_API_KEY", "")).strip())


def _as_str_list(value: Any, fallback: list[str]) -> list[str]:
    if isinstance(value, list):
        rows: list[str] = []
        for item in value:
            text = str(item).strip()
            if text:
                rows.append(text)
        return rows if rows else list(fallback)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return list(fallback)
        return [text]
    return list(fallback)


def _looks_label_like(text: str, fallback_label: str) -> bool:
    value = " ".join(text.strip().lower().split())
    base = " ".join((fallback_label or "").strip().lower().split())
    if not value:
        return True
    if base and value == base:
        return True
    starters = ("possible ", "likely ", "probable ", "suspicion ", "suspected ")
    if any(value.startswith(s) for s in starters):
        if len(value.split()) <= 18:
            return True
    return False


def _compose_conversational_reply(
    language: SupportedLanguage,
    label_text: str,
    checks: list[str],
    actions: list[str],
    call_text: str,
) -> str:
    check = checks[0] if checks else ""
    action = actions[0] if actions else ""
    call = (call_text or "").strip()
    if language == "fr":
        msg = f"D'accord. Sur la base de vos informations, il s'agit probablement de: {label_text}."
        if check:
            msg += f" Commencez par {check.lower() if check else check}."
        if action:
            msg += f" Ensuite, {action.lower() if action else action}."
        if call:
            msg += f" Si la situation s'aggrave: {call}"
        return msg
    if language == "ar":
        msg = f"تمام. بناء على المعطيات الحالية، الاحتمال الأقرب هو: {label_text}."
        if check:
            msg += f" ابدأ ب {check}."
        if action:
            msg += f" ثم {action}."
        if call:
            msg += f" وإذا ساءت الحالة: {call}"
        return msg
    msg = f"Based on what you shared, this is most likely: {label_text}."
    if check:
        msg += f" Start with {check}."
    if action:
        msg += f" Then {action}."
    if call:
        msg += f" If it gets worse: {call}"
    return msg


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
    conversation_history: list[dict[str, str]] | None = None,
) -> DiagnosisResponse:
    history = list(conversation_history or [])
    is_followup = len(history) > 0

    serializable_sources: list[dict[str, str]] = []
    for item in evidence_sources:
        if isinstance(item, dict):
            serializable_sources.append({k: str(v) for k, v in item.items()})
            continue
        dumped = getattr(item, "model_dump", None)
        if callable(dumped):
            serializable_sources.append({k: str(v) for k, v in dumped().items()})
            continue
        serializable_sources.append({"source_id": str(item)})

    context = {
        "user_input": {
            "farmer_note": payload.farmer_note,
            "observed_symptoms": payload.observed_symptoms,
            "language": language,
        },
        "is_followup_turn": is_followup,
        "fallback_diagnosis": fallback.model_dump(),
        "classifier_trace": classifier_trace or "",
        "conversation_history": history,
        "knowledge_entry_top1": _build_knowledge_context(retrieved[:1], language),
        "evidence_sources": serializable_sources,
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
        "You are an olive agronomy chatbot speaking to a real farmer. "
        "Use ONLY the provided grounded context. "
        "Do not hallucinate, do not claim certainty, be conservative and safety-first. "
        "Return JSON only with the required keys. Keep language exactly as requested (ar, fr, en). "
        "You MAY include brief bilingual glosses when useful, but keep the main response in requested language. "
        "Set low confidence if evidence is weak or conflicting. "
        "Do not change diagnosis ranking: the selected diagnosis is already fixed from top-1 retrieval/classifier logic. "
        "If is_followup_turn is true, DO NOT reprint a full diagnosis template; answer the latest user message directly. "
        "For follow-up turns: keep probable_issue conversational (2-4 sentences), acknowledge prior context, and focus on next practical steps. "
        "For follow-up turns: keep list fields short and non-redundant (0-3 items each), and avoid repeating the same follow-up questions unless truly needed. "
        "probable_issue must contain the main human-style reply the user should read in chat. "
        "If not necessary, leave non-chat fields brief or empty instead of repeating boilerplate. "
        "Reformulate in natural, empathetic chatbot style while staying concise and actionable. "
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
        return fallback.model_copy(update={"response_source": "fallback", "fallback_reason": "llm_no_content"})

    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        return fallback.model_copy(update={"response_source": "fallback", "fallback_reason": "llm_invalid_json"})

    try:
        default_alt = [] if CONVERSATIONAL_ONLY else fallback.alternative_causes
        default_why = [] if CONVERSATIONAL_ONLY else fallback.why_it_thinks_that
        default_check = [] if CONVERSATIONAL_ONLY else fallback.what_to_check_next
        default_safe = [] if CONVERSATIONAL_ONLY else fallback.safe_actions
        default_followups = [] if CONVERSATIONAL_ONLY else fallback.recommended_followup_questions
        default_call = "" if CONVERSATIONAL_ONLY else fallback.when_to_call_agronomist
        probable_issue = str(parsed.get("probable_issue", fallback.probable_issue))
        final_checks = _as_str_list(parsed.get("what_to_check_next"), default_check)
        final_actions = _as_str_list(parsed.get("safe_actions"), default_safe)
        final_call = str(parsed.get("when_to_call_agronomist", default_call))

        if CONVERSATIONAL_ONLY and _looks_label_like(probable_issue, fallback.probable_issue):
            probable_issue = _compose_conversational_reply(
                language=language,
                label_text=str(fallback.probable_issue),
                checks=final_checks,
                actions=final_actions,
                call_text=final_call,
            )
        return DiagnosisResponse(
            probable_issue=probable_issue,
            confidence_band=parsed.get("confidence_band", fallback.confidence_band),
            alternative_causes=_as_str_list(parsed.get("alternative_causes"), default_alt),
            why_it_thinks_that=_as_str_list(parsed.get("why_it_thinks_that"), default_why),
            what_to_check_next=final_checks,
            urgency=parsed.get("urgency", fallback.urgency),
            safe_actions=final_actions,
            when_to_call_agronomist=final_call,
            recommended_followup_questions=_as_str_list(
                parsed.get("recommended_followup_questions"), default_followups
            ),
            language=language,
            model_trace_summary=str(parsed.get("model_trace_summary", fallback.model_trace_summary)),
            matched_category=fallback.matched_category,
            matched_subcategory=fallback.matched_subcategory,
            session_id=fallback.session_id,
            response_source="llm",
            fallback_reason=None,
            evidence_sources=evidence_sources,
            classifier_debug=fallback.classifier_debug,
        )
    except Exception:
        return fallback.model_copy(update={"response_source": "fallback", "fallback_reason": "llm_schema_error"})
