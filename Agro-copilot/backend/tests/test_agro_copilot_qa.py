import unittest
from unittest.mock import patch

from backend.app.models.diagnosis import DiagnosisRequest, DiagnosisResponse, EvidenceSource
from backend.app.services.chat_memory import clear_memory
from backend.app.services.classifier_service import ClassifierPrediction
from backend.app.services.diagnosis_service import build_diagnosis
from backend.app.services.llm_service import maybe_generate_grounded_response
from backend.app.services.retrieval import KnowledgeEntry, RetrievedCase


def _sample_entry(entry_id: str = "olive__qa_case") -> KnowledgeEntry:
    return KnowledgeEntry(
        id=entry_id,
        keywords=("spot", "leaf"),
        category="disease",
        subcategory="fungal",
        probable_issue={"en": "Probable issue from knowledge"},
        confidence_hint="high",
        urgency_hint="medium",
        alternative_causes={"en": ["alt-1"]},
        why_it_thinks_that={"en": ["why-1"]},
        what_to_check_next={"en": ["check-1"]},
        safe_actions={"en": ["safe-1"]},
        when_to_call_agronomist={"en": "call agronomist if spread increases"},
        recommended_followup_questions={"en": ["follow-up-1"]},
        source_ids=("SRC-1",),
    )


class AgroCopilotQATests(unittest.TestCase):
    def setUp(self):
        clear_memory()

    @patch("backend.app.services.diagnosis_service.llm_is_available", return_value=False)
    @patch("backend.app.services.diagnosis_service.retrieve_cases")
    def test_text_only_without_llm_returns_service_unavailable(self, mock_retrieve, _mock_llm_available):
        mock_retrieve.return_value = [RetrievedCase(entry=_sample_entry(), score=4)]

        payload = DiagnosisRequest(farmer_note="I see spots on olive leaves", language="en")
        response = build_diagnosis(payload)

        self.assertIn("temporarily unavailable", response.probable_issue.lower())
        self.assertEqual(response.confidence_band, "low")

    @patch("backend.app.services.diagnosis_service.llm_is_available", return_value=False)
    @patch("backend.app.services.diagnosis_service.predict_from_request")
    def test_image_without_llm_uses_non_llm_fallback(self, mock_predict, _mock_llm_available):
        mock_predict.return_value = ClassifierPrediction(
            label="healthy",
            score=0.96,
            confidence_band="high",
            source="image_base64",
            top_k=[
                {"label": "healthy", "score": 0.96},
                {"label": "peacock_spot", "score": 0.02},
            ],
            trace="qa-trace",
        )

        payload = DiagnosisRequest(
            farmer_note="Check this leaf",
            language="en",
            image_base64="dummy",
        )
        response = build_diagnosis(payload)

        self.assertIn("healthy leaf", response.probable_issue.lower())
        self.assertEqual(response.model_trace_summary, "")
        self.assertIsNone(response.classifier_debug)

    @patch("backend.app.services.diagnosis_service.llm_is_available", return_value=True)
    @patch("backend.app.services.diagnosis_service.maybe_generate_grounded_response")
    @patch("backend.app.services.diagnosis_service.retrieve_cases")
    def test_llm_finalization_gets_top1_only(self, mock_retrieve, mock_maybe, _mock_llm_available):
        entry1 = _sample_entry("olive__top1")
        entry2 = _sample_entry("olive__top2")
        mock_retrieve.return_value = [
            RetrievedCase(entry=entry1, score=5),
            RetrievedCase(entry=entry2, score=4),
        ]

        def _fake_llm(**kwargs):
            retrieved = kwargs["retrieved"]
            self.assertEqual(len(retrieved), 1)
            self.assertEqual(retrieved[0].entry.id, "olive__top1")
            fallback = kwargs["fallback"]
            return fallback.model_copy(update={"probable_issue": "LLM reformulated answer"})

        mock_maybe.side_effect = _fake_llm

        payload = DiagnosisRequest(farmer_note="olive leaf spots", language="en")
        response = build_diagnosis(payload)

        self.assertEqual(response.probable_issue, "LLM reformulated answer")
        self.assertIsNone(response.classifier_debug)

    @patch("backend.app.services.llm_service._chat_completion")
    def test_llm_grounding_serializes_evidence_sources(self, mock_chat):
        mock_chat.return_value = (
            '{"probable_issue":"Grounded","confidence_band":"medium","alternative_causes":[],"why_it_thinks_that":[],'  # noqa: E501
            '"what_to_check_next":[],"urgency":"low","safe_actions":[],"when_to_call_agronomist":"",'
            '"recommended_followup_questions":[],"model_trace_summary":"ok"}'
        )

        payload = DiagnosisRequest(farmer_note="olive symptoms", language="en")
        fallback = DiagnosisResponse(
            probable_issue="Fallback",
            confidence_band="low",
            alternative_causes=[],
            why_it_thinks_that=[],
            what_to_check_next=[],
            urgency="low",
            safe_actions=[],
            when_to_call_agronomist="",
            recommended_followup_questions=[],
            language="en",
            model_trace_summary="fallback-trace",
            matched_category="disease",
            matched_subcategory="fungal",
            evidence_sources=[
                EvidenceSource(
                    source_id="SRC-1",
                    title="Source",
                    url="https://example.com",
                    publisher="Publisher",
                    accessed_on="2026-01-01",
                    trust_level="high",
                )
            ],
            classifier_debug=None,
        )
        retrieved = [RetrievedCase(entry=_sample_entry("olive__top1"), score=5)]
        evidence = fallback.evidence_sources

        response = maybe_generate_grounded_response(
            payload=payload,
            fallback=fallback,
            retrieved=retrieved,
            evidence_sources=evidence,
            classifier_trace="trace",
            language="en",
        )

        self.assertEqual(response.probable_issue, "Grounded")

    @patch("backend.app.services.llm_service._chat_completion")
    def test_llm_string_list_fields_are_not_split_into_characters(self, mock_chat):
        mock_chat.return_value = (
            '{"probable_issue":"Peacock spot likely","confidence_band":"medium",'
            '"alternative_causes":"Nutrient stress",'
            '"why_it_thinks_that":"Dark circular spots and humidity pattern",'
            '"what_to_check_next":"Inspect upper/lower surfaces on multiple trees",'
            '"urgency":"medium","safe_actions":"Prune for airflow",'
            '"when_to_call_agronomist":"If rapid spread within a week",'
            '"recommended_followup_questions":"Did symptoms increase after rain?",'
            '"model_trace_summary":"ok"}'
        )

        payload = DiagnosisRequest(farmer_note="leaf spots", language="en")
        fallback = DiagnosisResponse(
            probable_issue="Fallback",
            confidence_band="low",
            alternative_causes=[],
            why_it_thinks_that=[],
            what_to_check_next=[],
            urgency="low",
            safe_actions=[],
            when_to_call_agronomist="",
            recommended_followup_questions=[],
            language="en",
            model_trace_summary="fallback-trace",
            matched_category="disease",
            matched_subcategory="fungal",
            evidence_sources=[],
            classifier_debug=None,
        )
        retrieved = [RetrievedCase(entry=_sample_entry("olive__top1"), score=5)]

        response = maybe_generate_grounded_response(
            payload=payload,
            fallback=fallback,
            retrieved=retrieved,
            evidence_sources=[],
            classifier_trace="trace",
            language="en",
        )

        self.assertEqual(response.why_it_thinks_that, ["Dark circular spots and humidity pattern"])
        self.assertEqual(response.what_to_check_next, ["Inspect upper/lower surfaces on multiple trees"])
        self.assertEqual(response.safe_actions, ["Prune for airflow"])

    @patch("backend.app.services.llm_service._chat_completion")
    def test_label_like_llm_output_is_rewritten_to_conversational_reply(self, mock_chat):
        mock_chat.return_value = (
            '{"probable_issue":"Possible peacock spot (Spilocaea oleaginea)",'
            '"confidence_band":"medium","alternative_causes":[],"why_it_thinks_that":[],'
            '"what_to_check_next":["Inspect both leaf surfaces on multiple trees"],'
            '"urgency":"medium","safe_actions":["Improve canopy airflow by pruning"],'
            '"when_to_call_agronomist":"Call if spread accelerates in one week",'
            '"recommended_followup_questions":[],"model_trace_summary":"ok"}'
        )

        payload = DiagnosisRequest(farmer_note="how to solve it?", language="en")
        fallback = DiagnosisResponse(
            probable_issue="Possible peacock spot (Spilocaea oleaginea) (Early-stage pattern, lower severity context)",
            confidence_band="medium",
            alternative_causes=[],
            why_it_thinks_that=[],
            what_to_check_next=["Inspect both leaf surfaces on multiple trees"],
            urgency="medium",
            safe_actions=["Improve canopy airflow by pruning"],
            when_to_call_agronomist="Call if spread accelerates in one week",
            recommended_followup_questions=[],
            language="en",
            model_trace_summary="fallback",
            matched_category="disease",
            matched_subcategory="fungal_leaf",
            evidence_sources=[],
            classifier_debug=None,
        )
        retrieved = [RetrievedCase(entry=_sample_entry("peacock_spot__early__low"), score=5)]

        response = maybe_generate_grounded_response(
            payload=payload,
            fallback=fallback,
            retrieved=retrieved,
            evidence_sources=[],
            classifier_trace="trace",
            language="en",
        )
        self.assertIn("Start with", response.probable_issue)
        self.assertIn("Then", response.probable_issue)

    @patch("backend.app.services.diagnosis_service.llm_is_available", return_value=True)
    @patch("backend.app.services.diagnosis_service.retrieve_cases")
    @patch("backend.app.services.diagnosis_service.maybe_generate_grounded_response")
    def test_session_memory_passes_history_to_llm(self, mock_maybe, mock_retrieve, _mock_llm_available):
        entry = _sample_entry("olive__top1")
        mock_retrieve.return_value = [RetrievedCase(entry=entry, score=5)]
        seen_history_lengths: list[int] = []

        def _fake_llm(**kwargs):
            seen_history_lengths.append(len(kwargs.get("conversation_history") or []))
            fallback = kwargs["fallback"]
            return fallback.model_copy(update={"probable_issue": "Memory-aware answer"})

        mock_maybe.side_effect = _fake_llm
        session_id = "qa-session-memory"

        first = build_diagnosis(DiagnosisRequest(farmer_note="What is this leaf problem?", language="en", session_id=session_id))
        second = build_diagnosis(DiagnosisRequest(farmer_note="is it peacock?", language="en", session_id=session_id))

        self.assertEqual(first.probable_issue, "Memory-aware answer")
        self.assertEqual(second.probable_issue, "Memory-aware answer")
        self.assertEqual(seen_history_lengths, [0, 1])

    @patch("backend.app.services.diagnosis_service.llm_is_available", return_value=True)
    @patch("backend.app.services.diagnosis_service.maybe_generate_grounded_response")
    @patch("backend.app.services.diagnosis_service.retrieve_cases")
    def test_followup_text_stays_anchored_to_previous_entry(self, mock_retrieve, mock_maybe, _mock_llm_available):
        entry_a = _sample_entry("olive__peacock_anchor")
        entry_b = _sample_entry("soil__ph_salinity")
        mock_retrieve.side_effect = [
            [RetrievedCase(entry=entry_a, score=5)],  # first user turn
            [RetrievedCase(entry=entry_b, score=5)],  # should be ignored by anchored follow-up
        ]
        mock_maybe.side_effect = lambda **kwargs: kwargs["fallback"]
        session_id = "qa-anchor-followup"

        first = build_diagnosis(
            DiagnosisRequest(farmer_note="what is the problem with this leaf?", language="en", session_id=session_id)
        )
        second = build_diagnosis(
            DiagnosisRequest(farmer_note="so how to solve it now?", language="en", session_id=session_id)
        )

        self.assertEqual(first.matched_category, "disease")
        self.assertEqual(first.matched_subcategory, "fungal")
        self.assertEqual(second.matched_subcategory, first.matched_subcategory)


if __name__ == "__main__":
    unittest.main()
