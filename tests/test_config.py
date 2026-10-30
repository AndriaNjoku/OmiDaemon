import unittest
import os
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


if __name__ == "__main__":
    unittest.main()
