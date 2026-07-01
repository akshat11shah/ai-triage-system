from django.test import TestCase
from .models import CustomerMessage, TriageResult, GroundTruth
from .triage_engine import TriageEngine
from .evaluator import seed_database

class TriageModelTest(TestCase):
    def test_message_creation(self):
        msg = CustomerMessage.objects.create(text="Test message", source="Unit Test")
        self.assertEqual(msg.text, "Test message")
        self.assertEqual(msg.source, "Unit Test")
        self.assertIn("Test message", str(msg))

    def test_triage_result_creation(self):
        msg = CustomerMessage.objects.create(text="Need a password reset")
        triage = TriageResult.objects.create(
            message=msg,
            category="Account Query",
            priority="P2",
            summary="User needs a password reset",
            suggested_action="Send reset link",
            needs_human=False,
            confidence=0.9
        )
        self.assertEqual(triage.message, msg)
        self.assertEqual(triage.final_category, "Account Query")
        self.assertEqual(triage.final_priority, "P2")
        self.assertFalse(triage.final_needs_human)

    def test_human_override(self):
        msg = CustomerMessage.objects.create(text="Angry support request")
        triage = TriageResult.objects.create(
            message=msg,
            category="Support Request",
            priority="P2",
            summary="Angry request",
            suggested_action="Resolve",
            needs_human=False,
            confidence=0.8
        )
        
        # Apply override
        triage.is_overridden = True
        triage.overridden_category = "Complaint"
        triage.overridden_priority = "P0"
        triage.overridden_needs_human = True
        triage.save()
        
        self.assertEqual(triage.final_category, "Complaint")
        self.assertEqual(triage.final_priority, "P0")
        self.assertTrue(triage.final_needs_human)

class TriageEngineTest(TestCase):
    def test_engine_fallback_mechanics(self):
        engine = TriageEngine()
        # Test short/vague message fallback triggers high needs_human and low confidence
        result = engine.triage_message("Hi")
        self.assertTrue(result["needs_human"])
        self.assertLess(result["confidence"], 0.7)

        # Test billing query heuristic fallback
        result_billing = engine.triage_message("I paid yesterday but it is still pending.")
        self.assertEqual(result_billing["category"], "Support Request")
        self.assertEqual(result_billing["priority"], "P1")

        # Test out-of-scope heuristic fallback
        result_oos = engine.triage_message("What is the weather in Paris?")
        self.assertEqual(result_oos["category"], "Out of Scope")
        self.assertEqual(result_oos["priority"], "P3")

class SeederTest(TestCase):
    def test_seeding_function(self):
        created_msg, created_gt = seed_database()
        self.assertEqual(created_msg, 40)
        self.assertEqual(created_gt, 10)
        self.assertEqual(CustomerMessage.objects.filter(source="Dataset").count(), 40)
        self.assertEqual(GroundTruth.objects.count(), 10)
