"""Export dated proposals and queue source-backed Google Calendar candidates."""

import hashlib
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List
from ..models import AnalysisResult, TranscriptDocument
from ..config import CalendarConfig


class CalendarDispatcher:
    def __init__(self, config: CalendarConfig):
        self.config = config

    @staticmethod
    def parse_start(value):
        if not isinstance(value, str):
            return None
        try:
            start = datetime.fromisoformat(value.replace('Z', '+00:00'))
        except ValueError:
            return None
        return start if 'T' in value and start.utcoffset() is not None else None

    @staticmethod
    def escape(value):
        return str(value).replace('\\', '\\\\').replace('\r\n', '\n').replace('\r', '\n').replace('\n', '\\n').replace(';', '\\;').replace(',', '\\,')

    @staticmethod
    def write_json(path, value):
        temp = path.with_suffix('.tmp')
        temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        os.replace(temp, path)

    def dispatch(self, result: AnalysisResult, doc: TranscriptDocument) -> List[str]:
        if not self.config.enabled or not result.calendar_events:
            return []
        now = datetime.now(timezone.utc)
        created = []
        for event in result.calendar_events:
            start = self.parse_start(event.start_time)
            valid_duration = isinstance(event.duration_minutes, int) and not isinstance(event.duration_minutes, bool) and 0 < event.duration_minutes <= 1440
            end = start + timedelta(minutes=event.duration_minutes) if start and valid_duration else None
            canonical = json.dumps([event.title.strip().casefold(), start.astimezone(timezone.utc).isoformat() if start else event.start_time, event.duration_minutes], ensure_ascii=False)
            identity = hashlib.sha256(canonical.encode()).hexdigest()
            evidence = ' '.join(event.evidence.split())
            backed = bool(evidence) and evidence in ' '.join(doc.content.split())
            status, reason = 'pending', ''
            if not start or not end:
                status, reason = 'needs_review', 'Missing exact time, timezone or valid duration'
            elif start <= now:
                status, reason = 'expired', 'Historical event; do not import'
            elif not event.confirmed or not backed:
                status, reason = 'needs_review', 'Commitment requires confirmation and a matching transcript quote'

            if self.config.google_sync_enabled:
                outbox = Path(self.config.outbox_dir).resolve()
                outbox.mkdir(parents=True, exist_ok=True)
                queue_file = outbox / f'{identity}.json'
                # Do not erase connector results or review decisions on retry.
                if not queue_file.exists():
                    self.write_json(queue_file, {
                        'schema_version': 1, 'id': identity, 'status': status, 'reason': reason,
                        'calendar_id': self.config.calendar_id,
                        'title': event.title, 'description': event.description,
                        'start_time': start.isoformat() if start else event.start_time,
                        'end_time': end.isoformat() if end else None,
                        'duration_minutes': event.duration_minutes,
                        'evidence': event.evidence, 'confirmed': event.confirmed,
                        'source_file': doc.file_name, 'source_path': doc.file_path,
                        'source_sha256': doc.sha256, 'created_at': now.isoformat(),
                        'mentioned_attendees': event.attendees,
                    })

            if status != 'pending':
                continue
            output = Path(self.config.output_dir).resolve()
            output.mkdir(parents=True, exist_ok=True)
            path = output / f'{identity}.ics'
            text = '\r\n'.join([
                'BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//OmiDaemon//Calendar proposal//EN',
                'CALSCALE:GREGORIAN', 'METHOD:PUBLISH', 'BEGIN:VEVENT',
                f'UID:{identity}@omidaemon.local',
                f'DTSTAMP:{now.strftime("%Y%m%dT%H%M%SZ")}',
                f'DTSTART:{start.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")}',
                f'DTEND:{end.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")}',
                f'SUMMARY:{self.escape(event.title)}',
                f'DESCRIPTION:{self.escape(event.description + " (Source: " + doc.file_name + ")")}',
                'STATUS:TENTATIVE', 'END:VEVENT', 'END:VCALENDAR', '',
            ])
            path.write_bytes(text.encode('utf-8'))
            created.append(str(path))
        return created
