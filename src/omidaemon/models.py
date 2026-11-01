"""Core data models and domain types for OmiDaemon."""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum


class MeetingCategory(str, Enum):
    EXECUTIVE_STRATEGIC = "executive_strategic"
    ONE_ON_ONE = "one_on_one"
    ENGINEERING_SYNC = "engineering_sync"
    PARTNER_SYNC = "partner_sync"
    PITCH_OR_PRESENTATION = "pitch_or_presentation"
    CASUAL_BRAINSTORM = "casual_brainstorm"
    OTHER = "other"


@dataclass
class ActionItem:
    task: str
    assignee: str = "Unassigned"
    priority: str = "medium"  # high, medium, low
    due_date: Optional[str] = None
    context: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task": self.task,
            "assignee": self.assignee,
            "priority": self.priority,
            "due_date": self.due_date,
            "context": self.context,
        }


@dataclass
class RoutingDecision:
    save_obsidian: bool = True
    send_email: bool = False
    email_recipients: List[str] = field(default_factory=list)  # "partner", "staff", "self"
    draft_slides: bool = False
    update_calendar: bool = False
    reasoning: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "save_obsidian": self.save_obsidian,
            "send_email": self.send_email,
            "email_recipients": self.email_recipients,
            "draft_slides": self.draft_slides,
            "update_calendar": self.update_calendar,
            "reasoning": self.reasoning,
        }


@dataclass
class EmailDraft:
    subject: str
    body_markdown: str
    recipients: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "subject": self.subject,
            "body_markdown": self.body_markdown,
            "recipients": self.recipients,
        }


@dataclass
class SlideDeckDraft:
    title: str
    slides: List[Dict[str, str]] = field(default_factory=list)  # list of {"title": ..., "content": ...}
    theme: str = "gaia"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "slides": self.slides,
            "theme": self.theme,
        }


@dataclass
class CalendarEventProposal:
    title: str
    description: str
    start_time: Optional[str] = None
    duration_minutes: int = 30
    attendees: List[str] = field(default_factory=list)
    evidence: str = ""
    confirmed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "description": self.description,
            "start_time": self.start_time,
            "duration_minutes": self.duration_minutes,
            "attendees": self.attendees,
            "evidence": self.evidence,
            "confirmed": self.confirmed,
        }


@dataclass
class AnalysisResult:
    title: str
    category: MeetingCategory
    summary: str
    key_decisions: List[str] = field(default_factory=list)
    action_items: List[ActionItem] = field(default_factory=list)
    routing: RoutingDecision = field(default_factory=RoutingDecision)
    email_draft: Optional[EmailDraft] = None
    slides_draft: Optional[SlideDeckDraft] = None
    calendar_events: List[CalendarEventProposal] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    raw_snippet: str = ""
    keep: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "category": self.category.value if isinstance(self.category, MeetingCategory) else str(self.category),
            "summary": self.summary,
            "key_decisions": self.key_decisions,
            "action_items": [a.to_dict() for a in self.action_items],
            "routing": self.routing.to_dict(),
            "email_draft": self.email_draft.to_dict() if self.email_draft else None,
            "slides_draft": self.slides_draft.to_dict() if self.slides_draft else None,
            "calendar_events": [c.to_dict() for c in self.calendar_events],
            "tags": self.tags,
            "raw_snippet": self.raw_snippet,
            "keep": self.keep,
        }


@dataclass
class TranscriptDocument:
    file_path: str
    file_name: str
    sha256: str
    content: str
    modified_time: float
    detected_speakers: List[str] = field(default_factory=list)
