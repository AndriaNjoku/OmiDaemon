"""Configuration loader and schema management for OmiDaemon."""

import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
import yaml


@dataclass
class LLMConfig:
    provider: str = "gemini"  # gemini, openai, anthropic
    api_key: str = ""
    model: str = "gemini-3.5-flash-lite"
    temperature: float = 0.2


@dataclass
class SourceConfig:
    drive_path: str = ""
    poll_interval_seconds: int = 15
    file_patterns: List[str] = field(default_factory=lambda: ["*.txt", "*.md", "*.json"])


@dataclass
class ObsidianConfig:
    enabled: bool = True
    vault_path: str = ""
    subdir: str = "Executive Briefs"
    create_daily_link: bool = True
    tags: List[str] = field(default_factory=lambda: ["meeting", "wearable-notes", "executive"])


@dataclass
class EmailConfig:
    enabled: bool = False
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    use_tls: bool = True
    username: str = ""
    password: str = ""
    partner_email: str = ""
    staff_email: str = ""
    self_email: str = ""


@dataclass
class SlidesConfig:
    enabled: bool = True
    output_dir: str = "output/slides"
    theme: str = "gaia"


@dataclass
class CalendarConfig:
    enabled: bool = True
    output_dir: str = "output/calendar"
    google_sync_enabled: bool = False
    outbox_dir: str = "data/calendar-outbox"
    calendar_id: str = "primary"


@dataclass
class AppConfig:
    llm: LLMConfig = field(default_factory=LLMConfig)
    source: SourceConfig = field(default_factory=SourceConfig)
    obsidian: ObsidianConfig = field(default_factory=ObsidianConfig)
    email: EmailConfig = field(default_factory=EmailConfig)
    slides: SlidesConfig = field(default_factory=SlidesConfig)
    calendar: CalendarConfig = field(default_factory=CalendarConfig)
    state_db_path: str = "data/omidaemon_state.db"

    @classmethod
    def _load_dotenv(cls) -> None:
        """Load .env file from CWD or project root into os.environ if not already set."""
        candidates = [
            Path.cwd() / ".env",
            Path(__file__).resolve().parent.parent.parent / ".env",
        ]
        for p in candidates:
            if p.is_file():
                try:
                    for line in p.read_text(encoding="utf-8").splitlines():
                        line = line.strip()
                        if not line or line.startswith("#") or "=" not in line:
                            continue
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip("'\"")
                        if k and k not in os.environ:
                            os.environ[k] = v
                    break
                except Exception:
                    pass

    @classmethod
    def load(cls, config_path: Optional[str] = None) -> "AppConfig":
        """Load configuration merging defaults, YAML file, and environment variables."""
        cls._load_dotenv()
        cfg = cls()

        # 1. Load YAML file if present
        yaml_data: Dict[str, Any] = {}
        target_path = config_path or os.environ.get("OMIDAEMON_CONFIG_PATH") or "config/default_config.yaml"
        p = Path(target_path)
        if p.is_file():
            try:
                with p.open("r", encoding="utf-8") as f:
                    yaml_data = yaml.safe_load(f) or {}
            except Exception as e:
                print(f"[Warning] Failed to load config from {p}: {e}")

        # Apply YAML values
        if "llm" in yaml_data:
            c = yaml_data["llm"]
            cfg.llm.provider = c.get("provider", cfg.llm.provider)
            cfg.llm.model = c.get("model", cfg.llm.model)
            cfg.llm.temperature = float(c.get("temperature", cfg.llm.temperature))
            if "api_key" in c:
                cfg.llm.api_key = c["api_key"]

        if "source" in yaml_data:
            c = yaml_data["source"]
            cfg.source.drive_path = c.get("drive_path", cfg.source.drive_path)
            cfg.source.poll_interval_seconds = int(c.get("poll_interval_seconds", cfg.source.poll_interval_seconds))
            if "file_patterns" in c:
                cfg.source.file_patterns = list(c["file_patterns"])

        if "obsidian" in yaml_data:
            c = yaml_data["obsidian"]
            cfg.obsidian.enabled = bool(c.get("enabled", cfg.obsidian.enabled))
            cfg.obsidian.vault_path = c.get("vault_path", cfg.obsidian.vault_path)
            cfg.obsidian.subdir = c.get("subdir", cfg.obsidian.subdir)
            cfg.obsidian.create_daily_link = bool(c.get("create_daily_link", cfg.obsidian.create_daily_link))
            if "tags" in c:
                cfg.obsidian.tags = list(c["tags"])

        if "email" in yaml_data:
            c = yaml_data["email"]
            cfg.email.enabled = bool(c.get("enabled", cfg.email.enabled))
            cfg.email.smtp_host = c.get("smtp_host", cfg.email.smtp_host)
            cfg.email.smtp_port = int(c.get("smtp_port", cfg.email.smtp_port))
            cfg.email.use_tls = bool(c.get("use_tls", cfg.email.use_tls))
            cfg.email.username = c.get("username", cfg.email.username)
            cfg.email.password = c.get("password", cfg.email.password)
            cfg.email.partner_email = c.get("partner_email", cfg.email.partner_email)
            cfg.email.staff_email = c.get("staff_email", cfg.email.staff_email)
            cfg.email.self_email = c.get("self_email", cfg.email.self_email)

        if "slides" in yaml_data:
            c = yaml_data["slides"]
            cfg.slides.enabled = bool(c.get("enabled", cfg.slides.enabled))
            cfg.slides.output_dir = c.get("output_dir", cfg.slides.output_dir)
            cfg.slides.theme = c.get("theme", cfg.slides.theme)

        if "calendar" in yaml_data:
            c = yaml_data["calendar"]
            cfg.calendar.enabled = bool(c.get("enabled", cfg.calendar.enabled))
            cfg.calendar.output_dir = c.get("output_dir", cfg.calendar.output_dir)
            cfg.calendar.google_sync_enabled = bool(c.get("google_sync_enabled", False))
            cfg.calendar.outbox_dir = c.get("outbox_dir", cfg.calendar.outbox_dir)
            cfg.calendar.calendar_id = c.get("calendar_id", cfg.calendar.calendar_id)

        # 2. Environment Variable Overrides
        env = os.environ
        cfg.llm.provider = env.get("OMIDAEMON_LLM_PROVIDER", cfg.llm.provider)
        cfg.llm.model = env.get("OMIDAEMON_LLM_MODEL", cfg.llm.model)
        api_key = (
            env.get("OMIDAEMON_LLM_API_KEY")
            or env.get("GEMINI_API_KEY")
            or env.get("OPENAI_API_KEY")
            or env.get("ANTHROPIC_API_KEY")
        )
        if api_key:
            cfg.llm.api_key = api_key

        if "OMIDAEMON_DRIVE_PATH" in env:
            cfg.source.drive_path = env["OMIDAEMON_DRIVE_PATH"]

        if "OMIDAEMON_STATE_DB" in env:
            cfg.state_db_path = env["OMIDAEMON_STATE_DB"]

        if "OMIDAEMON_OBSIDIAN_VAULT" in env:
            cfg.obsidian.vault_path = env["OMIDAEMON_OBSIDIAN_VAULT"]

        if "OMIDAEMON_OBSIDIAN_SUBDIR" in env:
            cfg.obsidian.subdir = env["OMIDAEMON_OBSIDIAN_SUBDIR"]

        if "OMIDAEMON_EMAIL_ENABLED" in env:
            cfg.email.enabled = env["OMIDAEMON_EMAIL_ENABLED"].lower() in ("true", "1", "yes")

        if "OMIDAEMON_EMAIL_PARTNER" in env:
            cfg.email.partner_email = env["OMIDAEMON_EMAIL_PARTNER"]

        if "OMIDAEMON_EMAIL_STAFF" in env:
            cfg.email.staff_email = env["OMIDAEMON_EMAIL_STAFF"]

        if "OMIDAEMON_EMAIL_SMTP_HOST" in env:
            cfg.email.smtp_host = env["OMIDAEMON_EMAIL_SMTP_HOST"]

        if "OMIDAEMON_EMAIL_SMTP_PORT" in env:
            try:
                cfg.email.smtp_port = int(env["OMIDAEMON_EMAIL_SMTP_PORT"])
            except ValueError:
                pass

        if "OMIDAEMON_EMAIL_USER" in env:
            cfg.email.username = env["OMIDAEMON_EMAIL_USER"]

        if "OMIDAEMON_EMAIL_PASS" in env:
            cfg.email.password = env["OMIDAEMON_EMAIL_PASS"]

        if "OMIDAEMON_SLIDES_DIR" in env:
            cfg.slides.output_dir = env["OMIDAEMON_SLIDES_DIR"]

        if "OMIDAEMON_CALENDAR_DIR" in env:
            cfg.calendar.output_dir = env["OMIDAEMON_CALENDAR_DIR"]
        if "OMIDAEMON_GOOGLE_CALENDAR_ENABLED" in env:
            cfg.calendar.google_sync_enabled = env["OMIDAEMON_GOOGLE_CALENDAR_ENABLED"].lower() in ("true", "1", "yes")
        if "OMIDAEMON_CALENDAR_OUTBOX" in env:
            cfg.calendar.outbox_dir = env["OMIDAEMON_CALENDAR_OUTBOX"]
        if "OMIDAEMON_CALENDAR_ID" in env:
            cfg.calendar.calendar_id = env["OMIDAEMON_CALENDAR_ID"]

        return cfg
