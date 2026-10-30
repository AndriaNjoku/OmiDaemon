"""Central router orchestrating all action dispatchers."""

from typing import Dict, Any
from ..models import AnalysisResult, TranscriptDocument
from ..config import AppConfig
from .obsidian import ObsidianDispatcher
from .email_dispatcher import EmailDispatcher
from .slides import SlidesDispatcher
from .calendar import CalendarDispatcher


class ActionRouter:
    def __init__(self, config: AppConfig):
        self.config = config
        self.obsidian = ObsidianDispatcher(config.obsidian)
        self.email = EmailDispatcher(config.email)
        self.slides = SlidesDispatcher(config.slides)
        self.calendar = CalendarDispatcher(config.calendar)

    def route(self, result: AnalysisResult, doc: TranscriptDocument) -> Dict[str, Any]:
        """Dispatch analysis results to all active, appropriate destinations."""
        report: Dict[str, Any] = {
            "obsidian": None,
            "email": None,
            "slides": None,
            "calendar": [],
        }

        # 1. Obsidian Vault
        if result.routing.save_obsidian:
            report["obsidian"] = self.obsidian.dispatch(result, doc)

        # 2. Email Notification / Draft
        if result.routing.send_email or result.email_draft:
            report["email"] = self.email.dispatch(result, doc)

        # 3. Slide Presentation
        if result.routing.draft_slides or result.slides_draft:
            report["slides"] = self.slides.dispatch(result, doc)

        # 4. Calendar Follow-ups
        if result.routing.update_calendar or result.calendar_events:
            report["calendar"] = self.calendar.dispatch(result, doc)

        return report
