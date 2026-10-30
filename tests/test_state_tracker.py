import unittest
import tempfile
import os
from omidaemon.watcher.state_tracker import StateTracker


class TestStateTracker(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test_state.db")
        self.tracker = StateTracker(self.db_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_unprocessed_file(self):
        self.assertFalse(self.tracker.is_processed("fake_path.txt", "abc123hash"))

    def test_record_success_and_check(self):
        path = os.path.join(self.temp_dir.name, "meeting.txt")
        sha256 = "dummy_sha256_hash"
        self.tracker.record_success(
            file_path=path,
            sha256=sha256,
            file_mtime=1234567.0,
            title="Strategic Review",
            category="executive_strategic",
            routing_data={"obsidian": True},
        )
        self.assertTrue(self.tracker.is_processed(path, sha256))
        # Hash change means it should count as unprocessed
        self.assertFalse(self.tracker.is_processed(path, "different_hash"))

    def test_record_failure(self):
        path = os.path.join(self.temp_dir.name, "failing.txt")
        sha256 = "fail_sha256"
        self.tracker.record_failure(path, sha256, "API timeout")
        self.assertFalse(self.tracker.is_processed(path, sha256))
        recent = self.tracker.list_recent(1)
        self.assertEqual(len(recent), 1)
        self.assertEqual(recent[0]["status"], "error")


if __name__ == "__main__":
    unittest.main()
