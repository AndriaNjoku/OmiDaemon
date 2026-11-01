import unittest
from omidaemon.config import LLMConfig
from omidaemon.models import TranscriptDocument, MeetingCategory
from omidaemon.processor.llm_client import LLMClient
from omidaemon.processor.engine import ContextEngine


class TestContextEngine(unittest.TestCase):
    def setUp(self):
        # Use mock LLM client for deterministic testing
        cfg = LLMConfig(provider="mock")
        self.client = LLMClient(cfg)
        self.engine = ContextEngine(self.client)

    def test_engine_processing_mock(self):
        doc = TranscriptDocument(
            file_path="C:/dummy/test_meeting.txt",
            file_name="test_meeting.txt",
            sha256="mock_sha256",
            content="Alice: Let's confirm the architecture roadmap.",
            modified_time=1700000000.0,
        )
        result = self.engine.process(doc)

        self.assertEqual(result.title, "Executive Strategy & Roadmap Sync")
        self.assertEqual(result.category, MeetingCategory.EXECUTIVE_STRATEGIC)
        self.assertTrue(len(result.key_decisions) >= 1)
        self.assertTrue(len(result.action_items) >= 1)
        self.assertTrue(result.routing.save_obsidian)
        self.assertTrue(result.routing.send_email)
        self.assertIsNotNone(result.email_draft)
        self.assertIn("partner", result.routing.email_recipients)


    def test_builds_filter_and_calendar_evidence(self):
        result = ContextEngine._build_result({'keep': False, 'calendar_events': [{'title': 'Review', 'evidence': 'Agreed review', 'confirmed': True}]}, '')
        self.assertFalse(result.keep)
        self.assertEqual(result.calendar_events[0].evidence, 'Agreed review')
        self.assertTrue(result.calendar_events[0].confirmed)

    def test_calendar_confirmation_defaults_to_false(self):
        result = ContextEngine._build_result({'calendar_events': [{'title': 'Review'}]}, '')
        self.assertFalse(result.calendar_events[0].confirmed)


if __name__ == "__main__":
    unittest.main()
