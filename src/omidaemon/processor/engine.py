"""Context reasoning engine for analyzing conversations and generating structured outputs."""

import json
import re
from typing import Dict, Any, List, Optional
from ..models import (
    AnalysisResult,
    ActionItem,
    RoutingDecision,
    EmailDraft,
    SlideDeckDraft,
    CalendarEventProposal,
    MeetingCategory,
    TranscriptDocument,
)
from .parser import TranscriptParser
from .llm_client import LLMClient


SYSTEM_PROMPT = """You are an elite Chief of Staff and Executive AI Assistant to a CEO/CTO.
Your job is to read raw audio transcripts recorded from the user's wearable AI device (such as Omi / Based Hardware / Friend), analyze the conversation with sharp executive judgment, and produce an intelligent, highly structured output.

You must:
1. Classify the meeting category accurately (executive_strategic, one_on_one, engineering_sync, partner_sync, pitch_or_presentation, casual_brainstorm, other).
2. Write a concise executive summary emphasizing outcomes, strategic alignment, and high-stakes takeaways.
3. Extract clear, concrete Key Decisions that were agreed upon.
4. Extract Action Items with specific assignees, priority (high, medium, low), and deadlines if discussed.
5. Determine where this information should be routed:
   - Always route to Obsidian document repository.
   - If decisions or status affect the partner, leadership, or staff, set send_email=true and draft a professional markdown email ready to send.
   - If the conversation was a pitch, strategy review, or presentation outline, set draft_slides=true and draft an outline for presentation slides.
   - If explicit follow-up meetings or calendar commitments were made, set update_calendar=true and detail the calendar event proposals.
6. Provide relevant searchable tags (e.g., meeting/exec, project/alpha, strategy).

Output MUST be valid JSON adhering exactly to the requested schema. Do not add conversational prelude or postscript.
"""


USER_PROMPT_TEMPLATE = """Please analyze this transcript recorded on {file_name}.

DETECTED SPEAKERS: {speakers}
ESTIMATED WORDS: {word_count}

RAW TRANSCRIPT:
\"\"\"
{transcript}
\"\"\"

Produce a JSON response matching this schema:
{{
  "title": "<Concise descriptive title of the meeting or topic>",
  "category": "executive_strategic" | "one_on_one" | "engineering_sync" | "partner_sync" | "pitch_or_presentation" | "casual_brainstorm" | "other",
  "summary": "<2-4 sentence executive overview of the conversation and core outcomes>",
  "key_decisions": ["<decision 1>", "<decision 2>"],
  "action_items": [
    {{
      "task": "<concrete action item>",
      "assignee": "<person or role responsible>",
      "priority": "high" | "medium" | "low",
      "due_date": "<YYYY-MM-DD or null>",
      "context": "<brief rationale>"
    }}
  ],
  "routing": {{
    "save_obsidian": true,
    "send_email": <true if partner/staff should be updated>,
    "email_recipients": ["partner", "staff", "self"],
    "draft_slides": <true if pitch or deck needed>,
    "update_calendar": <true if meeting follow-up scheduled>,
    "reasoning": "<why you made these routing choices>"
  }},
  "email_draft": {{
    "subject": "<Subject line>",
    "body_markdown": "<Complete, professional draft email body in markdown>",
    "recipients": ["partner", "staff"]
  }} or null,
  "slides_draft": {{
    "title": "<Deck Title>",
    "theme": "gaia",
    "slides": [
      {{"title": "<Slide 1 Title>", "content": "<Bullet points in markdown>"}}
    ]
  }} or null,
  "calendar_events": [
    {{
      "title": "<Meeting Title>",
      "description": "<Agenda>",
      "start_time": "<ISO timestamp or relative description>",
      "duration_minutes": 30,
      "attendees": ["<email or name>"]
    }}
  ],
  "tags": ["meeting/...", "topic/..."]
}}
"""


class ContextEngine:
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client

    def process(self, doc: TranscriptDocument) -> AnalysisResult:
        """Parse transcript, run LLM analysis, and return structured AnalysisResult."""
        clean_text, speakers = TranscriptParser.parse(doc.content)
        word_count = TranscriptParser.estimate_word_count(clean_text)

        prompt = USER_PROMPT_TEMPLATE.format(
            file_name=doc.file_name,
            speakers=", ".join(speakers) if speakers else "Unknown",
            word_count=word_count,
            transcript=clean_text if clean_text else doc.content,
        )

        response_text = self.llm_client.complete(prompt, system_prompt=SYSTEM_PROMPT)
        data = self._clean_and_parse_json(response_text)

        return self._build_result(data, clean_text[:500])

    @staticmethod
    def _clean_and_parse_json(raw: str) -> Dict[str, Any]:
        """Strip markdown fences if present and parse JSON."""
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)
            cleaned = cleaned.strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            # Fallback regex extraction if there are leading/trailing characters
            match = re.search(r"(\{.*\})", cleaned, re.DOTALL)
            if match:
                return json.loads(match.group(1))
            raise ValueError(f"Failed to parse LLM response as JSON: {raw[:300]}") from e

    @staticmethod
    def _build_result(data: Dict[str, Any], raw_snippet: str) -> AnalysisResult:
        # Category
        raw_cat = data.get("category", "other").lower()
        try:
            category = MeetingCategory(raw_cat)
        except ValueError:
            category = MeetingCategory.OTHER

        # Action Items
        action_items = []
        for a in data.get("action_items", []):
            if isinstance(a, dict):
                action_items.append(
                    ActionItem(
                        task=a.get("task", ""),
                        assignee=a.get("assignee", "Unassigned"),
                        priority=a.get("priority", "medium"),
                        due_date=a.get("due_date"),
                        context=a.get("context", ""),
                    )
                )

        # Routing
        r_data = data.get("routing", {})
        routing = RoutingDecision(
            save_obsidian=bool(r_data.get("save_obsidian", True)),
            send_email=bool(r_data.get("send_email", False)),
            email_recipients=list(r_data.get("email_recipients", [])),
            draft_slides=bool(r_data.get("draft_slides", False)),
            update_calendar=bool(r_data.get("update_calendar", False)),
            reasoning=r_data.get("reasoning", ""),
        )

        # Email Draft
        email_draft = None
        if data.get("email_draft") and isinstance(data["email_draft"], dict):
            ed = data["email_draft"]
            email_draft = EmailDraft(
                subject=ed.get("subject", "Meeting Notes & Update"),
                body_markdown=ed.get("body_markdown", ""),
                recipients=list(ed.get("recipients", [])),
            )

        # Slides Draft
        slides_draft = None
        if data.get("slides_draft") and isinstance(data["slides_draft"], dict):
            sd = data["slides_draft"]
            slides_draft = SlideDeckDraft(
                title=sd.get("title", "Presentation Outline"),
                slides=list(sd.get("slides", [])),
                theme=sd.get("theme", "gaia"),
            )

        # Calendar Events
        calendar_events = []
        for ce in data.get("calendar_events", []):
            if isinstance(ce, dict):
                calendar_events.append(
                    CalendarEventProposal(
                        title=ce.get("title", "Meeting"),
                        description=ce.get("description", ""),
                        start_time=ce.get("start_time"),
                        duration_minutes=int(ce.get("duration_minutes", 30)),
                        attendees=list(ce.get("attendees", [])),
                    )
                )

        return AnalysisResult(
            title=data.get("title", "Executive Sync"),
            category=category,
            summary=data.get("summary", ""),
            key_decisions=list(data.get("key_decisions", [])),
            action_items=action_items,
            routing=routing,
            email_draft=email_draft,
            slides_draft=slides_draft,
            calendar_events=calendar_events,
            tags=list(data.get("tags", [])),
            raw_snippet=raw_snippet,
        )
