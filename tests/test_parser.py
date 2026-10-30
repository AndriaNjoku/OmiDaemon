import unittest
import json
from omidaemon.processor.parser import TranscriptParser


class TestParser(unittest.TestCase):
    def test_parse_plain_text(self):
        raw = "Speaker 1: We need to ship the feature by Friday.\nSpeaker 2: Agreed, I'll take care of the PR."
        text, speakers = TranscriptParser.parse(raw)
        self.assertIn("Speaker 1", speakers)
        self.assertIn("Speaker 2", speakers)
        self.assertIn("We need to ship the feature", text)

    def test_parse_timestamped_text(self):
        raw = "[00:15] Alice: Good morning everyone.\n[00:20] Bob: Morning Alice."
        text, speakers = TranscriptParser.parse(raw)
        self.assertIn("Alice", speakers)
        self.assertIn("Bob", speakers)
        self.assertIn("Good morning everyone", text)

    def test_parse_omi_json_segments(self):
        omi_data = {
            "transcript": "Hello world",
            "segments": [
                {"speaker": "Speaker 0", "text": "Let's review the budget.", "start": 0.0, "end": 2.1},
                {"speaker": "Speaker 1", "text": "The budget looks healthy.", "start": 2.2, "end": 4.5},
            ],
        }
        text, speakers = TranscriptParser.parse(json.dumps(omi_data))
        self.assertIn("Speaker 0", speakers)
        self.assertIn("Speaker 1", speakers)
        self.assertIn("Speaker 0: Let's review the budget.", text)
        self.assertIn("Speaker 1: The budget looks healthy.", text)

    def test_empty_transcript(self):
        text, speakers = TranscriptParser.parse("   ")
        self.assertEqual(text, "")
        self.assertEqual(speakers, [])


if __name__ == "__main__":
    unittest.main()
