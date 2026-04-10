import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.models.diagnosis import DiagnosisResponse
from backend.app.services.chat_memory import clear_memory
from backend.app.services.retrieval import RetrievedCase
from backend.tests.test_agro_copilot_qa import _sample_entry


class AgroCopilotApiIntegrationTests(unittest.TestCase):
    def setUp(self):
        clear_memory()
        self._old_key = os.environ.get("INTERNAL_API_KEY")
        os.environ["INTERNAL_API_KEY"] = "qa-secret"
        self.client = TestClient(app)
        self.headers = {"x-internal-api-key": "qa-secret"}

    def tearDown(self):
        if self._old_key is None:
            os.environ.pop("INTERNAL_API_KEY", None)
        else:
            os.environ["INTERNAL_API_KEY"] = self._old_key

    def test_chat_requires_internal_api_key(self):
        response = self.client.post(
            "/api/v1/chat",
            json={"message": "olive leaves have spots", "language": "en"},
        )
        self.assertEqual(response.status_code, 401)

    def test_sessions_create_list_and_history(self):
        create_resp = self.client.post("/api/v1/chat/sessions", headers=self.headers)
        self.assertEqual(create_resp.status_code, 200)
        session_id = create_resp.json().get("session_id")
        self.assertTrue(session_id)

        list_resp = self.client.get("/api/v1/chat/sessions", headers=self.headers)
        self.assertEqual(list_resp.status_code, 200)
        rows = list_resp.json()
        self.assertTrue(any(row.get("session_id") == session_id for row in rows))

        history_resp = self.client.get(f"/api/v1/chat/sessions/{session_id}/history", headers=self.headers)
        self.assertEqual(history_resp.status_code, 200)
        self.assertEqual(history_resp.json().get("session_id"), session_id)
        self.assertIsInstance(history_resp.json().get("history"), list)

        delete_resp = self.client.delete(f"/api/v1/chat/sessions/{session_id}", headers=self.headers)
        self.assertEqual(delete_resp.status_code, 200)
        self.assertEqual(delete_resp.json().get("ok"), True)

        history_after_delete = self.client.get(f"/api/v1/chat/sessions/{session_id}/history", headers=self.headers)
        self.assertEqual(history_after_delete.status_code, 404)

    @patch("backend.app.services.diagnosis_service.llm_is_available", return_value=False)
    @patch("backend.app.services.diagnosis_service.retrieve_cases")
    def test_text_only_without_llm_returns_service_unavailable_via_api(self, mock_retrieve, _mock_llm_available):
        mock_retrieve.return_value = [RetrievedCase(entry=_sample_entry("olive__top1"), score=5)]
        response = self.client.post(
            "/api/v1/chat",
            headers=self.headers,
            json={"message": "olive leaves have spots", "language": "en"},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("temporarily unavailable", payload["probable_issue"].lower())
        self.assertEqual(payload["confidence_band"], "low")

    @patch("backend.app.services.diagnosis_service.llm_is_available", return_value=True)
    @patch("backend.app.services.diagnosis_service.retrieve_cases")
    @patch("backend.app.services.diagnosis_service.maybe_generate_grounded_response")
    def test_chat_returns_llm_style_output_via_api(self, mock_maybe, mock_retrieve, _mock_llm_available):
        entry = _sample_entry("olive__top1")
        mock_retrieve.return_value = [RetrievedCase(entry=entry, score=5)]

        llm_style = DiagnosisResponse(
            probable_issue="It looks like peacock spot; I know this is stressful, and we can handle it step by step.",
            confidence_band="medium",
            alternative_causes=["Nutrient stress can look similar."],
            why_it_thinks_that=["The pattern and grounded entry match typical olive leaf spotting."],
            what_to_check_next=["Check 20 leaves across different trees and note spread."],
            urgency="medium",
            safe_actions=["Avoid aggressive spraying before confirming spread severity."],
            when_to_call_agronomist="Call an agronomist if lesions spread rapidly in 3-5 days.",
            recommended_followup_questions=["Would you like a simple 48-hour field check plan?"],
            language="en",
            model_trace_summary="grounded_llm_top1",
            matched_category="disease",
            matched_subcategory="fungal",
            evidence_sources=[],
            classifier_debug=None,
        )
        mock_maybe.return_value = llm_style

        response = self.client.post(
            "/api/v1/chat",
            headers=self.headers,
            json={"message": "my olive leaves have circular dark spots", "language": "en"},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("step by step", payload["probable_issue"].lower())
        self.assertIn("would you like", " ".join(payload["recommended_followup_questions"]).lower())
        self.assertTrue(payload.get("session_id"))


if __name__ == "__main__":
    unittest.main()
