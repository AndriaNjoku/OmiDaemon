"""Calendar dispatcher generating standard iCalendar (.ics) event files."""

import re
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional
from ..models import AnalysisResult, TranscriptDocument
from ..config import CalendarConfig


class CalendarDispatcher:
    def __init__(self, config: CalendarConfig):
        self.config = config

    @staticmethod
    def sanitize_filename(name: str) -> str:
        sanitized = re.sub(r'[\\/*?:"<>|]', "", name)
        sanitized = re.sub(r"\s+", " ", sanitized).strip()
        return sanitized[:60] or "Followup"

    def dispatch(self, result: AnalysisResult, doc: TranscriptDocument) -> List[str]:
        """Generate .ics files for proposed calendar follow-ups."""
        if not self.config.enabled or not result.calendar_events:
            return []

        out_dir = Path(self.config.output_dir).resolve()
        out_dir.mkdir(parents=True, exist_ok=True)

        created_files = []
        now_utc = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")

        for idx, ev in enumerate(result.calendar_events, 1):
            safe_title = self.sanitize_filename(ev.title)
            ics_file = out_dir / f"{safe_title}_{idx}.ics"

            # Estimate start / end if not strictly formatted
            start_dt = datetime.utcnow() + timedelta(days=1, hours=9)
            end_dt = start_dt + timedelta(minutes=ev.duration_minutes)

            start_str = start_dt.strftime("%Y%m%dT%H%M%SZ")
            end_str = end_dt.strftime("%Y%m%dT%H%M%SZ")
            uid = f"{uuid.uuid4()}@omidaemon.local"

            ics_content = (
                "BEGIN:VCALENDAR\n"
                "VERSION:2.0\n"
                "PRODID:-//OmiDaemon//Executive Calendar Followup//EN\n"
                "CALSCALE:GREGORIAN\n"
                "METHOD:REQUEST\n"
                "BEGIN:VEVENT\n"
                f"UID:{uid}\n"
                f"DTSTAMP:{now_utc}\n"
                f"DTSTART:{start_str}\n"
                f"DTEND:{end_str}\n"
                f"SUMMARY:{ev.title}\n"
                f"DESCRIPTION:{ev.description} (Origin: {doc.file_name})\n"
                "STATUS:CONFIRMED\n"
                "END:VEVENT\n"
                "END:VCALENDAR\n"
            )

            ics_file.write_text(ics_content, encoding="utf-8")
            created_files.append(str(ics_file.resolve()))

        return created_files
