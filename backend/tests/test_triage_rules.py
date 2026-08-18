import unittest

from app.agent.triage_rules import build_fallback_response, evaluate_triage


class TriageRulesTests(unittest.TestCase):
    def test_explicit_emergency_red_flags_escalate(self):
        cases = [
            "I have chest pain",
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
        self.assertIn("One Important Safety Question", response)
        self.assertIn("not a diagnosis", response)


if __name__ == "__main__":
    unittest.main()
