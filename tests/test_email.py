import unittest
import tempfile
import os
from pathlib import Path
from omidaemon.config import EmailConfig
from omidaemon.models import AnalysisResult, TranscriptDocument, MeetingCategory, EmailDraft, RoutingDecision
from omidaemon.dispatchers.email_dispatcher import EmailDispatcher


class TestEmailDispatcher(unittest.TestCase):
    def setUp(self):
        self.config = EmailConfig(
            enabled=False,  # Offline draft mode
            partner_email="partner@company.com",
            staff_email="all@company.com",
            self_email="me@company.com",
        )
        self.dispatcher = EmailDispatcher(self.config)

    def test_recipient_resolution(self):
        resolved = self.dispatcher.resolve_recipients(["partner", "staff", "custom@external.com"])
        self.assertIn("partner@company.com", resolved)
        self.assertIn("all@company.com", resolved)
        self.assertIn("custom@external.com", resolved)

    def test_save_draft_when_offline(self):
        doc = TranscriptDocument(
            file_path="mock/sync.txt",
            file_name="sync.txt",
            sha256="hash789",
            content="Team sync notes...",
            modified_time=1700000000.0,
        )
        draft = EmailDraft(
            subject="Weekly Executive Update",
            body_markdown="Hi everyone, here is the update for this week.",
            recipients=["partner", "staff"],
        )
        result = AnalysisResult(
            title="Weekly Update",
            category=MeetingCategory.EXECUTIVE_STRATEGIC,
            summary="Update summary.",
            routing=RoutingDecision(send_email=True, email_recipients=["partner", "staff"]),
            email_draft=draft,
        )

        res = self.dispatcher.dispatch(result, doc)
        self.assertEqual(res["status"], "draft_saved")
        self.assertTrue(os.path.exists(res["saved_path"]))
        content = Path(res["saved_path"]).read_text(encoding="utf-8")
        self.assertIn("Weekly Executive Update", content)
        self.assertIn("partner@company.com", content)


if __name__ == "__main__":
    unittest.main()
