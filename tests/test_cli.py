import unittest
from omidaemon.cli import rate_limit_delay


class TestRateLimitDelay(unittest.TestCase):
    def test_minute_quota_pauses_whole_queue(self):
        self.assertEqual(rate_limit_delay(RuntimeError('Gemini API error (429): {"retryDelay":"45s"}')), 60)

    def test_long_retry_is_respected(self):
        self.assertEqual(rate_limit_delay(RuntimeError('Gemini API error (429): {"retryDelay":"9565s"}')), 9566)

    def test_other_errors_do_not_pause_queue(self):
        self.assertEqual(rate_limit_delay(RuntimeError('Gemini API error (400)')), 0)
