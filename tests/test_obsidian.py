import unittest
import tempfile
import os
from pathlib import Path
from omidaemon.config import ObsidianConfig
from omidaemon.models import AnalysisResult, TranscriptDocument, MeetingCategory, ActionItem, RoutingDecision
from omidaemon.dispatchers.obsidian import ObsidianDispatcher


class TestObsidianDispatcher(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config = ObsidianConfig(
            enabled=True,
            vault_path=self.temp_dir.name,
            subdir="Executive Notes",
            tags=["meeting", "wearable"],
        )
        self.dispatcher = ObsidianDispatcher(self.config)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_obsidian_dispatch(self):
        doc = TranscriptDocument(
            file_path="mock/path.txt",
            file_name="wearable_rec_01.txt",
            sha256="hash123",
            content="Raw conversation transcript...",
            modified_time=1700000000.0,
        )
        result = AnalysisResult(
            title="Q4 Product Review",
            category=MeetingCategory.EXECUTIVE_STRATEGIC,
            summary="Agreed to expand engineering capacity.",
            key_decisions=["Allocate 2 engineers to mobile."],
            action_items=[ActionItem(task="Draft onboarding plan", assignee="Lead", priority="high")],
            routing=RoutingDecision(save_obsidian=True),
            tags=["product", "q4"],
        )

        output_path = self.dispatcher.dispatch(result, doc)
        self.assertIsNotNone(output_path)
        self.assertTrue(os.path.exists(output_path))

        content = Path(output_path).read_text(encoding="utf-8")
        self.assertIn("title: \"Q4 Product Review\"", content)
        self.assertIn("## 📋 Executive Summary", content)
        self.assertIn("Allocate 2 engineers to mobile.", content)
        self.assertIn("- [ ] [HIGH] **Draft onboarding plan** (@Lead)", content)


if __name__ == "__main__":
    unittest.main()
