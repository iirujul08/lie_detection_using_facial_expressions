"""
Automated Integration & Verification Test Suite
Tests:
1. ML trained model loading & prediction logic.
2. Personal baseline profile calculation & deviation scoring.
3. Full session flow via FastAPI TestClient:
   - Baseline calibration (3 samples) -> Baseline finalization
   - Multiple question evaluation (Q1, Q2, Q3)
4. Verification of output fields:
   - deception_probability (float 0.0 - 1.0)
   - baseline_deviation (float 0.0 - 1.0)
   - risk_score (float 0.0 - 100.0)
   - risk_level ("Low" | "Medium" | "High")
   - meter & bucket (for UI)
   - warnings & disclaimer
"""

import unittest
from unittest.mock import patch
import numpy as np
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.scoring import (
    get_model,
    build_baseline_profile,
    score_against_baseline,
    AU_COLUMNS,
)


class TestLieDetectorPipeline(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app)
        # Create a sample synthetic baseline (3 calm vectors)
        np.random.seed(42)
        self.sample_baseline_1 = np.full(len(AU_COLUMNS), 0.1)
        self.sample_baseline_2 = np.full(len(AU_COLUMNS), 0.12)
        self.sample_baseline_3 = np.full(len(AU_COLUMNS), 0.08)

        # Baseline profile
        self.profile = build_baseline_profile(
            [self.sample_baseline_1, self.sample_baseline_2, self.sample_baseline_3]
        )

    def test_model_loading_and_prediction(self):
        """Verify model loads successfully and outputs class probabilities."""
        model = get_model()
        self.assertIsNotNone(model)

        dummy_vector = np.zeros(len(AU_COLUMNS)).reshape(1, -1)
        proba = model.predict_proba(dummy_vector)[0]
        self.assertEqual(len(proba), 2)
        self.assertTrue(0.0 <= proba[1] <= 1.0)

    def test_scoring_against_baseline(self):
        """Verify score_against_baseline returns all required fields and correct ranges."""
        question_vector = np.full(len(AU_COLUMNS), 0.4) # Higher AU intensity -> drift
        res = score_against_baseline(question_vector, self.profile)

        # Check required keys
        self.assertIn("deception_probability", res)
        self.assertIn("baseline_deviation", res)
        self.assertIn("risk_score", res)
        self.assertIn("risk_level", res)
        self.assertIn("meter", res)
        self.assertIn("bucket", res)
        self.assertIn("warnings", res)
        self.assertIn("disclaimer", res)

        # Check ranges
        self.assertTrue(0.0 <= res["deception_probability"] <= 1.0)
        self.assertTrue(0.0 <= res["baseline_deviation"] <= 1.0)
        self.assertTrue(0.0 <= res["risk_score"] <= 100.0)
        self.assertIn(res["risk_level"], ["Low", "Medium", "High"])
        self.assertIn("disclaimer", res["disclaimer"].lower())

    @patch("backend.app.main.extract_au_vector")
    def test_full_fastapi_session_flow(self, mock_extract):
        """Test full flow: start session -> 3 baseline clips -> finalize -> 3 questions."""
        # 1. Start session
        resp = self.client.post("/session")
        self.assertEqual(resp.status_code, 200)
        session_id = resp.json()["session_id"]
        self.assertTrue(session_id)

        # 2. Upload 3 baseline clips
        mock_extract.side_effect = [
            self.sample_baseline_1,
            self.sample_baseline_2,
            self.sample_baseline_3,
        ]

        for i in range(1, 4):
            b_resp = self.client.post(
                f"/session/{session_id}/baseline",
                files={"clip": (f"baseline_{i}.webm", b"fake_webm_bytes", "video/webm")},
            )
            self.assertEqual(b_resp.status_code, 200)
            data = b_resp.json()
            self.assertEqual(data["samples_collected"], i)

        # 3. Finalize baseline
        fin_resp = self.client.post(f"/session/{session_id}/baseline/finalize")
        self.assertEqual(fin_resp.status_code, 200)
        fin_data = fin_resp.json()
        self.assertEqual(fin_data["n_samples"], 3)

        # 4. Test Multiple Questions (Q1, Q2, Q3)
        questions = [
            ("Did you break the cup?", np.full(len(AU_COLUMNS), 0.11)),   # Low drift (calm/truth)
            ("Where were you yesterday at 9 PM?", np.full(len(AU_COLUMNS), 0.35)), # Moderate drift
            ("Did you take the money?", np.full(len(AU_COLUMNS), 0.75)),  # High drift
        ]

        scored_results = []
        for q_id, dummy_vec in questions:
            mock_extract.side_effect = [dummy_vec]
            q_resp = self.client.post(
                f"/session/{session_id}/question?question_id={q_id}",
                files={"clip": ("question.webm", b"fake_webm_bytes", "video/webm")},
            )
            self.assertEqual(q_resp.status_code, 200)
            result = q_resp.json()

            # Verify response schema fields
            self.assertEqual(result["session_id"], session_id)
            self.assertEqual(result["question_id"], q_id)
            self.assertIn("deception_probability", result)
            self.assertIn("baseline_deviation", result)
            self.assertIn("risk_score", result)
            self.assertIn("risk_level", result)
            self.assertIn("disclaimer", result)
            self.assertIn("warnings", result)

            scored_results.append(result)

        # Assert multiple questions were successfully scored
        self.assertEqual(len(scored_results), 3)

        # 5. Check Session Summary Endpoint
        sum_resp = self.client.get(f"/session/{session_id}")
        self.assertEqual(sum_resp.status_code, 200)
        summary = sum_resp.json()
        self.assertEqual(summary["n_baseline_samples"], 3)
        self.assertEqual(len(summary["results"]), 3)

        print("\n[OK] FULL API FLOW VERIFICATION SUCCESSFUL!")
        print(f"Scored {len(scored_results)} questions with probability, deviation, risk & disclaimer.")


if __name__ == "__main__":
    unittest.main()
