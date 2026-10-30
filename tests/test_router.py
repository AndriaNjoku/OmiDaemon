import unittest
import tempfile
import os
from omidaemon.config import AppConfig
from omidaemon.models import AnalysisResult, TranscriptDocument, MeetingCategory, RoutingDecision, EmailDraft, SlideDeckDraft
from omidaemon.dispatchers.router import ActionRouter


class TestActionRouter(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config = AppConfig()
        self.config.obsidian.vault_path = os.path.join(self.temp_dir.name, "obsidian")
        self.config.slides.output_dir = os.path.join(self.temp_dir.name, "slides")
        self.config.calendar.output_dir = os.path.join(self.temp_dir.name, "calendar")
        self.router = ActionRouter(self.config)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_full_routing(self):
        doc = TranscriptDocument(
            file_path="mock/full.txt",
            file_name="full.txt",
            sha256="fullhash",
            content="Full pipeline test.",
            modified_time=1700000000.0,
        )
        result = AnalysisResult(
            title="All Hands & Strategy",
            category=MeetingCategory.EXECUTIVE_STRATEGIC,
            summary="Strategic discussion across company.",
            routing=RoutingDecision(
                save_obsidian=True,
                send_email=True,
                email_recipients=["partner"],
                draft_slides=True,
                update_calendar=False,
            ),
            email_draft=EmailDraft(subject="All Hands Notes", body_markdown="Notes...", recipients=["partner"]),
            slides_draft=SlideDeckDraft(title="All Hands Deck", slides=[{"title": "Overview", "content": "- Progress"}]),
        )

        report = self.router.route(result, doc)
        self.assertIsNotNone(report["obsidian"])
        self.assertIsNotNone(report["email"])
        self.assertIsNotNone(report["slides"])
        self.assertEqual(len(report["calendar"]), 0)


if __name__ == "__main__":
    unittest.main()
