# OmiDaemon

Autonomous executive intelligence daemon for wearable audio transcripts (Omi / Friend / wearable hardware syncing to Google Drive).

Supervised under **Notch Standard 1.0** with **Nudge**.

---

## 🌟 Overview

When you wear your AI audio hardware (Omi / Based Hardware / open-source wearable), conversations are transcribed and saved to Google Drive.

**OmiDaemon** runs continuously in the background to:
1. **Watch**: Detect new or updated transcript files in your Google Drive folder.
2. **Contextualize & Reason**: Process the conversation with an LLM (Gemini, OpenAI, or Anthropic) acting as an elite Chief of Staff to a CEO/CTO.
3. **Extract Intelligence**:
   - Meeting categorization (Executive Strategic, 1-on-1, Engineering Sync, Partner Update, Pitch, etc.)
   - High-level executive summaries
   - Action items with priority, deadlines, and assignees
   - Key decisions agreed upon
4. **Autonomous Multi-Destination Routing**:
   - 📓 **Obsidian Vault**: Creates formatted markdown notes with YAML frontmatter, tags, action checklists, and backlinks.
   - 📧 **Executive Email Updates**: Drafts or automatically sends executive briefings to your partner, staff, or self.
   - 📊 **Presentation Slides**: Generates Marp-compatible markdown presentation drafts when strategic topics or pitches are discussed.
   - 📅 **Calendar Follow-ups**: Creates `.ics` calendar invitation files for scheduled commitments.
5. **Idempotency**: SQLite state tracker (`omidaemon_state.db`) ensures zero duplicate processing.

---

## 🚀 Quick Start

### 1. Configuration
Copy `.env.example` to `.env` and fill in your settings:
```bash
copy .env.example .env
```

Key variables:
- `OMIDAEMON_LLM_PROVIDER`: `gemini` (default), `openai`, or `anthropic`
- `OMIDAEMON_LLM_API_KEY`: Your LLM API key
- `OMIDAEMON_DRIVE_PATH`: Path to your synced Google Drive folder (e.g. `G:\My Drive\Transcripts`)
- `OMIDAEMON_OBSIDIAN_VAULT`: Local path to your Obsidian vault

### 2. Manual Test / Single File Process
Process any transcript file directly:
```bash
python -m omidaemon.cli process path/to/transcript.txt
```

### 3. Start Continuous Background Monitoring
```bash
python -m omidaemon.cli start
```

### 4. Inspect Processing History
```bash
python -m omidaemon.cli status
```

---

## 🧪 Testing

Run the automated test suite:
```powershell
$env:PYTHONPATH="src"
python -m unittest discover tests -v
```

---

## 🛡️ Notch Standard 1.0 & Nudge Supervision

- **Project ID**: `OmiDaemon`
- **Supervisor**: Nudge by Notch (port 8765)
- **Status**: Enrolled with native hooks and active workspace monitoring
- **Allowed Boundaries**: `src/**`, `tests/**`, `config/**`, `docs/**`, `pyproject.toml`, `README.md`, `.gitignore`, `.env.example`
- **Protected Paths**: `.git/**`, `.env`, and production credentials
