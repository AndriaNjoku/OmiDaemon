"""Email dispatcher for sending executive updates or saving drafts."""

import smtplib
import re
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from typing import Dict, Any, List, Optional
from ..models import AnalysisResult, TranscriptDocument
from ..config import EmailConfig


class EmailDispatcher:
    def __init__(self, config: EmailConfig):
        self.config = config

    def resolve_recipients(self, target_keys: List[str]) -> List[str]:
        """Map target groups (partner, staff, self) to configured email addresses."""
        addresses = []
        for target in target_keys:
            t = target.strip().lower()
            if t == "partner" and self.config.partner_email:
                addresses.append(self.config.partner_email)
            elif t == "staff" and self.config.staff_email:
                addresses.append(self.config.staff_email)
            elif t == "self" and self.config.self_email:
                addresses.append(self.config.self_email)
            elif "@" in target:
                addresses.append(target)
        return list(dict.fromkeys(addresses))

    def dispatch(self, result: AnalysisResult, doc: TranscriptDocument) -> Dict[str, Any]:
        """Dispatch email draft or save offline draft file."""
        if not result.routing.send_email or not result.email_draft:
            return {"status": "skipped", "reason": "No email required by routing decision"}

        draft = result.email_draft
        recipients = self.resolve_recipients(draft.recipients or result.routing.email_recipients)

        # If live SMTP sending is enabled and configured
        if self.config.enabled and self.config.username and self.config.password and recipients:
            try:
                self._send_smtp(draft.subject, draft.body_markdown, recipients)
                return {"status": "sent", "recipients": recipients, "subject": draft.subject}
            except Exception as e:
                print(f"[EmailDispatcher] Failed to send email: {e}")
                saved_path = self._save_draft_file(draft.subject, draft.body_markdown, recipients, doc)
                return {"status": "error_saved_draft", "error": str(e), "saved_path": saved_path}

        # Otherwise, save draft offline
        saved_path = self._save_draft_file(draft.subject, draft.body_markdown, recipients, doc)
        return {"status": "draft_saved", "saved_path": saved_path, "recipients": recipients}

    def _send_smtp(self, subject: str, body: str, recipients: List[str]) -> None:
        msg = MIMEMultipart()
        msg["From"] = self.config.username
        msg["To"] = ", ".join(recipients)
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain", "utf-8"))

        server = smtplib.SMTP(self.config.smtp_host, self.config.smtp_port, timeout=15)
        if self.config.use_tls:
            server.starttls()
        server.login(self.config.username, self.config.password)
        server.sendmail(self.config.username, recipients, msg.as_string())
        server.quit()

    def _save_draft_file(self, subject: str, body: str, recipients: List[str], doc: TranscriptDocument) -> str:
        out_dir = Path("output/emails")
        out_dir.mkdir(parents=True, exist_ok=True)
        date_str = datetime.fromtimestamp(doc.modified_time).strftime("%Y-%m-%d")
        safe_subj = re.sub(r'[\\/*?:"<>|]', "", subject)[:50].strip()
        file_path = out_dir / f"{date_str} - {safe_subj}.md"

        recipients_str = ", ".join(recipients) if recipients else "No email addresses configured"
        content = (
            f"# Email Draft: {subject}\n"
            f"**To:** {recipients_str}\n"
            f"**Generated:** {datetime.now().isoformat()}\n"
            f"**Source Transcript:** `{doc.file_name}`\n\n"
            "---\n\n"
            f"{body}\n"
        )
        file_path.write_text(content, encoding="utf-8")
        return str(file_path.resolve())
