import unittest
import tempfile
import os
from pathlib import Path
from omidaemon.config import SlidesConfig
from omidaemon.models import AnalysisResult, TranscriptDocument, MeetingCategory, SlideDeckDraft, RoutingDecision
from omidaemon.dispatchers.slides import SlidesDispatcher


class TestSlidesDispatcher(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config = SlidesConfig(
            enabled=True,
            output_dir=self.temp_dir.name,
            theme="gaia",
        )
        self.dispatcher = SlidesDispatcher(self.config)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_slides_generation(self):
        doc = TranscriptDocument(
            file_path="mock/pitch.txt",
            file_name="pitch.txt",
            sha256="hash456",
            content="Pitch discussion...",
            modified_time=1700000000.0,
        )
        deck = SlideDeckDraft(
            title="Next Gen Architecture",
            slides=[
                {"title": "The Problem", "content": "- High latency\n- Complexity"},
                {"title": "The Solution", "content": "- Streamlined pipelines\n- Instant sync"},
            ],
            theme="gaia",
        )
        result = AnalysisResult(
            title="Next Gen Architecture",
            category=MeetingCategory.PITCH_OR_PRESENTATION,
            summary="Deck outline for investors.",
            routing=RoutingDecision(draft_slides=True),
            slides_draft=deck,
        )

        output_path = self.dispatcher.dispatch(result, doc)
        self.assertIsNotNone(output_path)
        self.assertTrue(os.path.exists(output_path))

        content = Path(output_path).read_text(encoding="utf-8")
        self.assertIn("marp: true", content)
        self.assertIn("theme: gaia", content)
        self.assertIn("## The Problem", content)
        self.assertIn("## The Solution", content)


if __name__ == "__main__":
    unittest.main()
