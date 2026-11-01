import unittest
import os
from unittest.mock import patch
from omidaemon.config import AppConfig


class TestConfig(unittest.TestCase):
    def test_default_config(self):
        cfg = AppConfig.load()
        self.assertIsNotNone(cfg.llm)
        self.assertIsNotNone(cfg.source)
        self.assertIsNotNone(cfg.obsidian)
        self.assertEqual(cfg.obsidian.subdir, "Executive Briefs")

    def test_env_override(self):
        os.environ["OMIDAEMON_LLM_PROVIDER"] = "mock"
        os.environ["OMIDAEMON_OBSIDIAN_SUBDIR"] = "CustomNotes"
        cfg = AppConfig.load()
        self.assertEqual(cfg.llm.provider, "mock")
        self.assertEqual(cfg.obsidian.subdir, "CustomNotes")
        del os.environ["OMIDAEMON_LLM_PROVIDER"]
        del os.environ["OMIDAEMON_OBSIDIAN_SUBDIR"]


    def test_calendar_sync_env_override(self):
        with patch.dict(os.environ, {'OMIDAEMON_GOOGLE_CALENDAR_ENABLED': 'true', 'OMIDAEMON_CALENDAR_OUTBOX': 'custom/outbox', 'OMIDAEMON_CALENDAR_ID': 'primary'}):
            cfg = AppConfig.load()
        self.assertTrue(cfg.calendar.google_sync_enabled)
        self.assertEqual(cfg.calendar.outbox_dir, 'custom/outbox')


if __name__ == "__main__":
    unittest.main()
