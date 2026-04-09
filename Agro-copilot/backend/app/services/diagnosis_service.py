import logging

from backend.app.core.language import resolve_language
from backend.app.models.diagnosis import DiagnosisRequest, DiagnosisResponse
from backend.app.services.classifier_service import predict_from_request
from backend.app.services.llm_service import describe_leaf_image
from backend.app.services.retrieval import (
    KnowledgeEntry,
    RetrievedCase,
    build_evidence_sources,
    get_classifier_mapping,
    get_classifier_policies,
    load_knowledge_bundle,
    localize_map_list,
    localize_map_text,
    retrieve_cases,
)


logger = logging.getLogger(__name__)

POLICIES = get_classifier_policies()
PEACOCK_MIN_SCORE = float(POLICIES.get("peacock_min_score", 0.85))
PEACOCK_MIN_MARGIN = float(POLICIES.get("peacock_min_margin", 0.15))
LOW_CONF_THRESHOLD = float(POLICIES.get("low_conf_threshold", 0.60))
HEALTHY_HIGH_CONF_THRESHOLD = float(POLICIES.get("healthy_high_conf_threshold", 0.80))


def _confidence_from_retrieval_score(score: int, hint: str) -> str:
    if score >= 4:
        return "high" if hint == "high" else "medium"
    if score >= 2:
        return "medium" if hint in {"medium", "high"} else "low"
    return "low"


def _top1_top2_margin(top_k: list[dict]) -> float | None:
    if len(top_k) < 2:
        return None
    try:
        return float(top_k[0]["score"]) - float(top_k[1]["score"])
    except Exception:
        return None


def _gate_label(label: str, score: float, margin: float | None) -> tuple[str, str | None]:
    if label != "peacock_spot":
        return label, None
    if score < PEACOCK_MIN_SCORE:
        return "uncertain", f"peacock_gate:score<{PEACOCK_MIN_SCORE:.2f}"
    if margin is not None and margin < PEACOCK_MIN_MARGIN:
        return "uncertain", f"peacock_gate:margin<{PEACOCK_MIN_MARGIN:.2f}"
    return label, None


def _build_classifier_debug(prediction) -> dict | None:
    if prediction is None:
        return None
    margin = _top1_top2_margin(prediction.top_k)
    gated_label, gate_reason = _gate_label(prediction.label, prediction.score, margin)
    return {
        "predicted_label": prediction.label,
        "gated_label": gated_label,
        "score": prediction.score,
        "top1_top2_margin": margin,
        "gate_reason": gate_reason,
        "confidence_band": prediction.confidence_band,
        "source": prediction.source,
        "top_k": prediction.top_k,
        "trace": prediction.trace,
    }


def _select_cases_from_prefixes(prefixes: tuple[str, ...], top_k: int = 3) -> list[RetrievedCase]:
    bundle = load_knowledge_bundle()
    matched: list[RetrievedCase] = []

    def _score(entry: KnowledgeEntry, prefix: str) -> int:
        if entry.id == prefix:
            return 100
        if entry.id.startswith(f"{prefix}__"):
            return 80
        return 0

    for entry in bundle.entries:
        best = 0
        for prefix in prefixes:
            best = max(best, _score(entry, prefix))
        if best > 0:
            matched.append(RetrievedCase(entry=entry, score=best))

    matched.sort(key=lambda r: r.score, reverse=True)
    return matched[:top_k]


def _clarify_probable_issue(probable_issue: str, language: str, classifier_debug: dict | None) -> str:
    if not classifier_debug:
        return probable_issue
    literal_label = str(classifier_debug.get("predicted_label") or "")
    gated_label = str(classifier_debug.get("gated_label") or "")
    if not literal_label:
        return probable_issue
    if gated_label == "uncertain":
        literal_label = f"{literal_label} (uncertain)"
    templates = {
        "en": f"{probable_issue} (model signal: {literal_label})",
        "fr": f"{probable_issue} (signal du modele: {literal_label})",
        "ar": f"{probable_issue} (اشارة النموذج: {literal_label})",
    }
    return templates.get(language, templates["en"])


def _clarify_probable_issue_dual_name(probable_issue: str, language: str, classifier_debug: dict | None) -> str:
    if not classifier_debug:
        return probable_issue
    literal_label = str(classifier_debug.get("predicted_label") or "")
    gated_label = str(classifier_debug.get("gated_label") or "")
    if not literal_label:
        return probable_issue

    lookup_label = gated_label if gated_label and gated_label != "uncertain" else literal_label
    mapping = get_classifier_mapping(lookup_label) or {}
    display_map = mapping.get("display", {})
    friendly_label = str(display_map.get(language) or display_map.get("en") or lookup_label)

    if gated_label == "uncertain":
        literal_label = f"{literal_label} (uncertain)"
        friendly_label = f"{friendly_label} (uncertain)"

    combined_signal = f"{friendly_label} = {literal_label}"
    templates = {
        "en": f"{probable_issue} (model signal: {combined_signal})",
        "fr": f"{probable_issue} (signal du modele: {combined_signal})",
        "ar": f"{probable_issue} (اشارة النموذج: {combined_signal})",
    }
    return templates.get(language, templates["en"])


def _healthy_response(language: str, classifier_trace: str, classifier_debug: dict | None) -> DiagnosisResponse:
    data = {
        "en": {
            "issue": "Likely healthy leaf (no clear disease signs in the image)",
            "why": [
                "Image model predicted healthy with high confidence.",
                "No strong visual disease evidence was found from the uploaded photo.",
            ],
            "check": [
                "Inspect 15-20 leaves from different trees and canopy levels.",
                "Retake close photos in natural light if symptoms appear later.",
                "Monitor weekly, especially after humid or rainy days.",
            ],
            "safe": [
                "No immediate disease spray from this signal alone.",
                "Keep regular sanitation and balanced irrigation.",
                "Repeat diagnosis if new lesions or rapid spread appear.",
            ],
            "call": "Call an agronomist if new spots spread fast, defoliation starts, or fruit symptoms appear.",
        },
        "fr": {
            "issue": "Feuille probablement saine (pas de signe clair de maladie sur l'image)",
            "why": [
                "Le modele image predit sain avec forte confiance.",
                "Aucun signe visuel fort de maladie sur la photo envoyee.",
            ],
            "check": [
                "Verifier 15-20 feuilles sur differents arbres et niveaux de canopee.",
                "Reprendre des photos nettes en lumiere naturelle si de nouveaux signes apparaissent.",
                "Surveiller chaque semaine, surtout apres humidite ou pluie.",
            ],
            "safe": [
                "Pas de traitement maladie immediat sur ce seul signal.",
                "Maintenir hygiene culturale et irrigation equilibree.",
                "Relancer le diagnostic si lesions nouvelles ou propagation rapide.",
            ],
            "call": "Contacter un agronome si nouvelles taches en progression rapide, defoliation, ou symptomes sur fruits.",
        },
        "ar": {
            "issue": "الورقة على الارجح سليمة (لا توجد مؤشرات مرض واضحة في الصورة)",
            "why": [
                "نموذج الصورة توقع حالة سليمة بثقة عالية.",
                "لا توجد دلائل بصرية قوية على مرض في الصورة المرسلة.",
            ],
            "check": [
                "افحص 15-20 ورقة من اشجار ومستويات تاج مختلفة.",
                "اعد تصوير لقطات قريبة بضوء طبيعي اذا ظهرت اعراض لاحقا.",
                "راقب اسبوعيا خاصة بعد الرطوبة او المطر.",
            ],
            "safe": [
                "لا تبدأ رشا مرضيا فوريا اعتمادا على هذه الاشارة وحدها.",
                "حافظ على النظافة الزراعية وري متوازن.",
                "اعد التشخيص اذا ظهرت بقع جديدة او انتشار سريع.",
            ],
            "call": "تواصل مع مهندس زراعي اذا ظهرت بقع جديدة بسرعة او بدأ تساقط اوراق او ظهرت اعراض على الثمار.",
        },
    }[language]

    return DiagnosisResponse(
        probable_issue=data["issue"],
        confidence_band="high",
        alternative_causes=[],
        why_it_thinks_that=data["why"],
        what_to_check_next=data["check"],
        urgency="low",
        safe_actions=data["safe"],
        when_to_call_agronomist=data["call"],
        recommended_followup_questions=[],
        language=language,
        model_trace_summary=f"classifier-first healthy decision. {classifier_trace}",
        matched_category="monitoring",
        matched_subcategory="healthy_visual",
        evidence_sources=[],
        classifier_debug=classifier_debug,
    )


def _fallback_response(language: str, classifier_trace: str, classifier_debug: dict | None, note: str = "") -> DiagnosisResponse:
    data = {
        "en": "Unclear from current evidence",
        "fr": "Cause non claire avec les informations actuelles",
        "ar": "السبب غير واضح بالمعطيات الحالية",
    }[language]
    return DiagnosisResponse(
        probable_issue=data,
        confidence_band="low",
        alternative_causes=[],
        why_it_thinks_that=[],
        what_to_check_next=[],
        urgency="low",
        safe_actions=[],
        when_to_call_agronomist="",
        recommended_followup_questions=[],
        language=language,
        model_trace_summary=f"{note} {classifier_trace}".strip(),
        matched_category=None,
        matched_subcategory=None,
        evidence_sources=[],
        classifier_debug=classifier_debug,
    )


def _build_entry_response(
    entry: KnowledgeEntry,
    retrieved: list[RetrievedCase],
    language: str,
    classifier_trace: str,
    classifier_debug: dict | None,
) -> DiagnosisResponse:
    confidence_band = _confidence_from_retrieval_score(retrieved[0].score, entry.confidence_hint)
    evidence_sources = build_evidence_sources(retrieved)
    source_ids = [s["source_id"] for s in evidence_sources]
    why = localize_map_list(entry.why_it_thinks_that, language)
    if source_ids:
        why = [*why, f"Grounded sources: {', '.join(source_ids)}"]

    localized_issue = localize_map_text(entry.probable_issue, language)
    clear_issue = _clarify_probable_issue_dual_name(localized_issue, language, classifier_debug)

    return DiagnosisResponse(
        probable_issue=clear_issue,
        confidence_band=confidence_band,
        alternative_causes=localize_map_list(entry.alternative_causes, language),
        why_it_thinks_that=why,
        what_to_check_next=localize_map_list(entry.what_to_check_next, language),
        urgency=entry.urgency_hint,
        safe_actions=localize_map_list(entry.safe_actions, language),
        when_to_call_agronomist=localize_map_text(entry.when_to_call_agronomist, language),
        recommended_followup_questions=localize_map_list(entry.recommended_followup_questions, language),
        language=language,
        model_trace_summary=(
            f"classifier/description guided retrieval -> entry='{entry.id}', "
            f"category={entry.category}, score={retrieved[0].score}. {classifier_trace}"
        ),
        matched_category=entry.category,
        matched_subcategory=entry.subcategory,
        evidence_sources=evidence_sources,
        classifier_debug=classifier_debug,
    )


def build_diagnosis(payload: DiagnosisRequest) -> DiagnosisResponse:
    language = resolve_language(payload.language)
    has_image = bool(payload.image_base64 or payload.image_path or payload.image_urls)
    base_text = " ".join([payload.farmer_note, *payload.observed_symptoms]).strip()

    if has_image:
        prediction = predict_from_request(payload)
        classifier_debug = _build_classifier_debug(prediction)
        logger.info("classifier_debug=%s", classifier_debug)

        if prediction is not None and classifier_debug is not None:
            gated_label = str(classifier_debug["gated_label"])
            trace = (
                f"{prediction.trace} gated_label={gated_label}; "
                f"gate_reason={classifier_debug.get('gate_reason') or 'none'}; "
                f"margin={classifier_debug.get('top1_top2_margin') if classifier_debug.get('top1_top2_margin') is not None else 'n/a'}."
            )

            if gated_label == "healthy" and prediction.score >= HEALTHY_HIGH_CONF_THRESHOLD:
                return _healthy_response(language, trace, classifier_debug)

            mapping = get_classifier_mapping(gated_label) or {}
            prefixes = tuple(mapping.get("knowledge_prefixes", []))
            if prefixes and prediction.score >= LOW_CONF_THRESHOLD:
                direct = _select_cases_from_prefixes(prefixes, top_k=3)
                if direct:
                    return _build_entry_response(direct[0].entry, direct, language, trace, classifier_debug)

            vision_desc = describe_leaf_image(payload, language)
            desc_query = f"{base_text} {vision_desc or ''}".strip()
            retrieved = retrieve_cases(desc_query)
            if retrieved:
                return _build_entry_response(
                    retrieved[0].entry,
                    retrieved,
                    language,
                    f"{trace} fallback=vision_description_retrieval; vision_description={vision_desc or 'none'}.",
                    classifier_debug,
                )
            return _fallback_response(
                language,
                f"{trace} fallback=vision_description_retrieval_no_match; vision_description={vision_desc or 'none'}.",
                classifier_debug,
                note="No knowledge match.",
            )

    retrieved = retrieve_cases(base_text)
    if retrieved:
        return _build_entry_response(retrieved[0].entry, retrieved, language, "text-only retrieval path.", None)
    return _fallback_response(language, "text-only retrieval path; no match.", None)
