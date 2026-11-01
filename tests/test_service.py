import unittest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
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
        if os.name == "nt":
            with patch("omidaemon.service.subprocess.run", return_value=MagicMock(returncode=0, stdout="INFO: No tasks are running which match the specified criteria.")):
                running, pid = self.service.is_running()
        else:
            running, pid = self.service.is_running()
        self.assertFalse(running)
        self.assertFalse(os.path.exists(self.pid_file))

    def test_background_uses_project_directory_and_global_config_option(self):
        proc = MagicMock(pid=12345)
        config = str(Path(self.temp_dir.name) / "custom.yaml")
        with patch("omidaemon.service.subprocess.Popen", return_value=proc) as launch:
            result = self.service.start_background(config)
        self.assertEqual(result["status"], "started")
        args, kwargs = launch.call_args
        command = args[0]
        self.assertLess(command.index("--config"), command.index("start"))
        self.assertEqual(command[command.index("--config") + 1], config)
        self.assertEqual(kwargs["cwd"], str(Path(__file__).resolve().parents[1]))
        self.assertTrue(kwargs["stdout"].closed)
        self.assertEqual(Path(self.pid_file).read_text(), "12345")

    @unittest.skipUnless(os.name == "nt", "Windows startup registration")
    def test_startup_task_tracks_daemon_and_sets_working_directory(self):
        with patch("omidaemon.service.subprocess.run", return_value=MagicMock(returncode=0)) as run:
            self.assertEqual(self.service.install_startup_task()["status"], "installed")
        command = run.call_args.args[0]
        self.assertIn("-WorkingDirectory", command[-1])
        self.assertIn("-m omidaemon.cli start-bg", command[-1])
        self.assertIn(str(Path(__file__).resolve().parents[1]), command[-1])

    @unittest.skipUnless(os.name == "nt", "Windows process visibility")
    def test_process_query_failure_preserves_pid(self):
        Path(self.pid_file).write_text("12345")
        with patch("omidaemon.service.subprocess.run", return_value=MagicMock(returncode=1, stdout="")):
            self.assertEqual(self.service.is_running(), (False, None))
        self.assertEqual(Path(self.pid_file).read_text(), "12345")


if __name__ == "__main__":
    unittest.main()
