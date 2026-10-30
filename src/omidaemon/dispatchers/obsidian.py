"""Obsidian vault dispatcher writing formatted markdown meeting notes."""

import re
from datetime import datetime
from pathlib import Path
from typing import Optional
from ..models import AnalysisResult, TranscriptDocument
from ..config import ObsidianConfig


class ObsidianDispatcher:
    def __init__(self, config: ObsidianConfig):
        self.config = config

    @staticmethod
    def sanitize_filename(name: str) -> str:
        """Sanitize title for cross-platform filenames."""
        sanitized = re.sub(r'[\\/*?:"<>|]', "", name)
        sanitized = re.sub(r"\s+", " ", sanitized).strip()
        return sanitized[:80] or "Executive Note"

    def dispatch(self, result: AnalysisResult, doc: TranscriptDocument) -> Optional[str]:
        """Format markdown note and write to the configured Obsidian vault."""
        if not self.config.enabled:
            return None

        vault_path = Path(self.config.vault_path).resolve() if self.config.vault_path else Path("output/obsidian")
        target_dir = vault_path / self.config.subdir
        target_dir.mkdir(parents=True, exist_ok=True)

        date_str = datetime.fromtimestamp(doc.modified_time).strftime("%Y-%m-%d")
        safe_title = self.sanitize_filename(result.title)
        file_name = f"{date_str} - {safe_title}.md"
        output_file = target_dir / file_name

        content = self._format_markdown(result, doc, date_str)
        output_file.write_text(content, encoding="utf-8")
        return str(output_file.resolve())

    def _format_markdown(self, result: AnalysisResult, doc: TranscriptDocument, date_str: str) -> str:
        # Frontmatter tags
        merged_tags = list(dict.fromkeys(self.config.tags + result.tags))
        tags_yaml = "\n".join(f"  - {t}" for t in merged_tags)

        lines = [
            "---",
            f"title: \"{result.title}\"",
            f"date: {date_str}",
            f"category: {result.category.value if hasattr(result.category, 'value') else result.category}",
            f"source_file: \"{doc.file_name}\"",
            "tags:",
            tags_yaml,
            "---\n",
            f"# {result.title}\n",
            f"*Recorded via Wearable Audio on {date_str}* | Source: `{doc.file_name}`\n",
            "## 📋 Executive Summary\n",
            f"{result.summary}\n",
        ]

        # Key Decisions
        if result.key_decisions:
            lines.append("## 🎯 Key Decisions\n")
            for d in result.key_decisions:
                lines.append(f"- **Decision:** {d}")
            lines.append("")

        # Action Items
        if result.action_items:
            lines.append("## ✅ Action Items\n")
            for a in result.action_items:
                pri_badge = f"[{a.priority.upper()}]" if a.priority else ""
                due_badge = f"📅 Due: {a.due_date}" if a.due_date else ""
                owner = f"@{a.assignee}" if a.assignee else "@unassigned"
                lines.append(f"- [ ] {pri_badge} **{a.task}** ({owner}) {due_badge}".strip())
                if a.context:
                    lines.append(f"  - *Context:* {a.context}")
            lines.append("")

        # Email Draft Callout
        if result.email_draft:
            lines.append("> [!note] 📧 Draft Executive Briefing")
            lines.append(f"> **Subject:** {result.email_draft.subject}")
            recips = ", ".join(result.email_draft.recipients) if result.email_draft.recipients else "Team"
            lines.append(f"> **Recipients:** {recips}\n>")
            for b_line in result.email_draft.body_markdown.splitlines():
                lines.append(f"> {b_line}")
            lines.append("\n")

        # Slide Outline Callout
        if result.slides_draft:
            lines.append("> [!tip] 📊 Presentation Draft Outline")
            lines.append(f"> **Title:** {result.slides_draft.title}\n>")
            for idx, s in enumerate(result.slides_draft.slides, 1):
                lines.append(f"> **Slide {idx}: {s.get('title', 'Slide')}**")
                for c_line in s.get("content", "").splitlines():
                    lines.append(f"> {c_line}")
                lines.append(">")
            lines.append("\n")

        # Calendar Follow-ups
        if result.calendar_events:
            lines.append("## 📅 Calendar Follow-ups\n")
            for ev in result.calendar_events:
                dur = f"({ev.duration_minutes} mins)" if ev.duration_minutes else ""
                lines.append(f"- **{ev.title}** {dur}")
                if ev.start_time:
                    lines.append(f"  - Suggested Time: `{ev.start_time}`")
                if ev.description:
                    lines.append(f"  - Details: {ev.description}")
            lines.append("")

        # Routing metadata
        lines.append("## 🧭 Routing & Context")
        lines.append(f"- **Obsidian Vault:** Saved to `{self.config.subdir}`")
        lines.append(f"- **Email Dispatch:** {'Triggered' if result.routing.send_email else 'Not triggered'}")
        if result.routing.reasoning:
            lines.append(f"- **Reasoning:** {result.routing.reasoning}")

        return "\n".join(lines)
