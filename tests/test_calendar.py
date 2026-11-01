import json
import tempfile
import unittest
from pathlib import Path
from omidaemon.config import CalendarConfig
from omidaemon.dispatchers.calendar import CalendarDispatcher
from omidaemon.models import AnalysisResult, CalendarEventProposal, MeetingCategory, TranscriptDocument


class TestCalendarDispatcher(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.config = CalendarConfig(output_dir=str(self.root / 'ics'), google_sync_enabled=True, outbox_dir=str(self.root / 'outbox'))
        self.dispatcher = CalendarDispatcher(self.config)
        self.doc = TranscriptDocument('example.txt', 'example.txt', 'hash', 'I confirm the review on 5 January 2099 at 10:00 UTC for 45 minutes.', 0)
        self.event = CalendarEventProposal('Review', 'Agreed review', '2099-01-05T10:00:00+00:00', 45, evidence=self.doc.content, confirmed=True)

    def dispatch(self):
        return self.dispatcher.dispatch(AnalysisResult('Meeting', MeetingCategory.ONE_ON_ONE, 'Review', calendar_events=[self.event]), self.doc)

    def queued(self):
        paths = list((self.root / 'outbox').glob('*.json'))
        self.assertEqual(len(paths), 1)
        return paths[0], json.loads(paths[0].read_text(encoding='utf-8'))

    def test_preserves_exact_event_time_and_duration(self):
        paths = self.dispatch()
        self.assertEqual(len(paths), 1)
        text = Path(paths[0]).read_text()
        self.assertIn('DTSTART:20990105T100000Z', text)
        self.assertIn('DTEND:20990105T104500Z', text)
        self.assertEqual(self.queued()[1]['status'], 'pending')

    def test_ambiguous_date_requires_review_without_invented_event(self):
        for value in [None, 'next Tuesday', '2099-01-05', '2099-01-05T10:00:00']:
            with self.subTest(value=value):
                self.event.start_time = value
                self.assertEqual(self.dispatch(), [])
        for path in (self.root / 'outbox').glob('*.json'):
            self.assertEqual(json.loads(path.read_text())['status'], 'needs_review')

    def test_past_event_not_exported(self):
        self.event.start_time = '2000-01-01T10:00:00Z'
        self.assertEqual(self.dispatch(), [])
        self.assertEqual(self.queued()[1]['status'], 'expired')

    def test_unconfirmed_or_unsupported_quote_not_exported(self):
        self.event.confirmed = False
        self.assertEqual(self.dispatch(), [])
        self.assertEqual(self.queued()[1]['status'], 'needs_review')
        self.event.title = 'Another event'
        self.event.confirmed = True
        self.event.evidence = 'This quote was not spoken.'
        self.assertEqual(self.dispatch(), [])

    def test_repeat_preserves_synced_record_and_normalises_timezone(self):
        self.dispatch()
        path, record = self.queued()
        record.update(status='synced', event_id='actual-id')
        path.write_text(json.dumps(record), encoding='utf-8')
        self.event.start_time = '2099-01-05T11:00:00+01:00'
        self.dispatch()
        self.assertEqual(self.queued()[1]['event_id'], 'actual-id')
        self.assertEqual(self.queued()[1]['status'], 'synced')

    def test_disabled_sync_does_not_queue(self):
        self.config.google_sync_enabled = False
        self.dispatch()
        self.assertFalse((self.root / 'outbox').exists())

    def test_ics_description_cannot_inject_fields(self):
        self.event.description = 'line\nATTENDEE:someone@example.com; other, detail'
        text = Path(self.dispatch()[0]).read_text()
        self.assertNotIn('\nATTENDEE:', text)
        self.assertIn('line\\nATTENDEE:', text)

    def test_invalid_duration_held_for_review(self):
        self.event.duration_minutes = -30
        self.assertEqual(self.dispatch(), [])
        self.assertEqual(self.queued()[1]['status'], 'needs_review')
