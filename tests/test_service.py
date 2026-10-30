import unittest
import tempfile
import os
from pathlib import Path
from omidaemon.service import DaemonService


class TestDaemonService(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.pid_file = os.path.join(self.temp_dir.name, "test.pid")
        self.log_file = os.path.join(self.temp_dir.name, "test.log")
        self.service = DaemonService(pid_file=self.pid_file, log_file=self.log_file)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_not_running_initially(self):
        running, pid = self.service.is_running()
        self.assertFalse(running)
        self.assertIsNone(pid)

    def test_stale_pid_cleanup(self):
        # Write a non-existent PID
        Path(self.pid_file).write_text("999999", encoding="utf-8")
        running, pid = self.service.is_running()
        self.assertFalse(running)
        self.assertFalse(os.path.exists(self.pid_file))


if __name__ == "__main__":
    unittest.main()
