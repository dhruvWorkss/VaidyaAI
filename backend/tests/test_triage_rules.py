import unittest

from app.agent.triage_rules import (
    build_fallback_response,
    build_intake_response,
    evaluate_triage,
    should_ask_follow_up,
)


class TriageRulesTests(unittest.TestCase):
    def test_explicit_emergency_red_flags_escalate(self):
        cases = [
            "I have crushing chest pressure",
            "I have chest pain with shortness of breath",
            "I can't breathe",
            "sudden severe headache",
            "my tongue is swelling",
            "I want to kill myself",
            "pregnant and heavy bleeding",
            "sudden vision loss",
        ]
        for message in cases:
            with self.subTest(message=message):
                self.assertEqual(evaluate_triage(message).risk_level, "emergency")

    def test_isolated_chest_pain_gets_questions_before_assessment(self):
        message = "I have chest pain"
        triage = evaluate_triage(message)

        self.assertEqual(triage.category, "cardiac")
        self.assertEqual(triage.risk_level, "high")
        self.assertTrue(triage.provisional)
        self.assertTrue(should_ask_follow_up(message, triage, []))

        response = build_intake_response(message, triage)
        self.assertIn("shortness of breath", response)
        self.assertIn("pain spreading", response)
        self.assertNotIn("Risk Level:", response)

    def test_ambiguous_isolated_symptoms_get_screened_before_emergency(self):
        for message in ("I have neck stiffness", "My lips are swollen"):
            with self.subTest(message=message):
                triage = evaluate_triage(message)
                self.assertEqual(triage.risk_level, "high")
                self.assertTrue(should_ask_follow_up(message, triage, []))

    def test_concerning_symptom_combinations_still_escalate(self):
        self.assertEqual(
            evaluate_triage("I have fever and neck stiffness").risk_level,
            "emergency",
        )
        self.assertEqual(
            evaluate_triage("My lips are swollen and I cannot breathe").risk_level,
            "emergency",
        )

    def test_negated_red_flag_does_not_escalate(self):
        result = evaluate_triage("I have a cough but no chest pain and no difficulty breathing")
        self.assertNotEqual(result.risk_level, "emergency")

    def test_categories_receive_relevant_questions(self):
        cases = {
            "burning urination": ("urinary", "back or side pain"),
            "itchy skin rash": ("skin_allergy", "swelling of the face"),
            "stomach pain and vomiting": ("digestive", "keep fluids down"),
            "pain in my eye": ("eye", "vision loss"),
        }
        for message, (category, question_text) in cases.items():
            with self.subTest(message=message):
                result = evaluate_triage(message)
                self.assertEqual(result.category, category)
                self.assertIn(question_text, result.question)

    def test_specialist_is_conservative_first_contact(self):
        headache = evaluate_triage("headache and fever")
        self.assertEqual(headache.risk_level, "medium")
        self.assertIn("General Physician", headache.specialist)
        self.assertNotIn("Neurologist", headache.specialist)

    def test_fallback_discloses_uncertainty(self):
        result = evaluate_triage("persistent cough")
        response = build_fallback_response("persistent cough", result)
        self.assertIn("provisional", response)
        self.assertIn("not a diagnosis", response)

    def test_initial_vague_symptoms_trigger_intake_before_risk(self):
        message = "I have a headache and fever"
        triage = evaluate_triage(message)
        self.assertTrue(should_ask_follow_up(message, triage, []))
        response = build_intake_response(message, triage)
        self.assertIn("measured temperature", response)
        self.assertIn("When did it start", response)
        self.assertNotIn("Risk Level:", response)

    def test_detailed_initial_message_does_not_over_question(self):
        message = "Mild headache for 2 days with no vomiting or neck stiffness"
        triage = evaluate_triage(message)
        self.assertFalse(should_ask_follow_up(message, triage, []))

    def test_follow_up_answer_allows_assessment(self):
        triage = evaluate_triage("headache and fever 101 F for 2 days, moderate")
        self.assertFalse(should_ask_follow_up("101 F for 2 days, moderate", triage, ["headache and fever"]))

    def test_risk_level_is_at_end_of_fallback_assessment(self):
        triage = evaluate_triage("persistent cough for 4 days, moderate")
        response = build_fallback_response("persistent cough for 4 days, moderate", triage)
        self.assertGreater(response.index("**Risk Level:**"), response.index("**Who to Contact**"))


if __name__ == "__main__":
    unittest.main()
