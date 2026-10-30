# OmiDaemon

Autonomous executive intelligence daemon for wearable audio transcripts (Omi / Friend / wearable hardware syncing to Google Drive).

Supervised under **Notch Standard 1.0** with **Nudge**.

---

## 🌟 Overview

When you wear your AI audio hardware (Omi / Based Hardware / open-source wearable), conversations are transcribed and saved to Google Drive.

**OmiDaemon** runs continuously as a silent background Windows daemon to:
1. **Watch Google Drive**:
   - **Local Sync Watcher**: Watches your Google Drive for Desktop sync folder instantly with zero API overhead.
   - **Drive API Watcher**: Connects directly to Google Drive REST API v3 using credentials/OAuth tokens.
2. **Contextualize & Reason**:
   - Analyzes conversations with your own LLM API key (Gemini, OpenAI, or Anthropic).
   - Categorizes meeting context (Executive Strategic, 1-on-1, Engineering Sync, Partner Update, Pitch, etc.).
   - Extracts executive summaries, concrete decisions, and prioritized action items with assignees and due dates.
3. **Autonomous Multi-Destination Routing**:
   - 📓 **Obsidian Vault**: Creates formatted markdown notes with YAML frontmatter, tags, action checklists, and backlinks.
   - 📧 **Executive Email Updates**: Drafts or automatically sends executive briefings to your partner, staff, or self.
   - 📊 **Presentation Slides**: Generates Marp-compatible markdown presentation drafts when strategic topics or pitches are discussed.
   - 📅 **Calendar Follow-ups**: Creates `.ics` calendar invitation files for scheduled commitments.
4. **Zero Duplicate Processing**: SQLite state tracker (`omidaemon_state.db`) ensures every file is processed idempotently.

---

## 🚀 Running as a Background Daemon on Windows

OmiDaemon is built to run windowless in the background using `pythonw.exe`:

### 1. Launch in the Background (Detached)
```powershell
python -m omidaemon.cli start-bg
```
*Runs completely silently in the background with no open terminal window. Logs are written to `logs/omidaemon.log`.*

### 2. Check Background Daemon Status
```powershell
python -m omidaemon.cli status-bg
```
*Reports whether the process is active, its PID, and log path.*

### 3. Stop the Background Daemon
```powershell
python -m omidaemon.cli stop-bg
```

### 4. Auto-Start on Windows Login
To have OmiDaemon start automatically in the background whenever you log into Windows:
```powershell
python -m omidaemon.cli install-startup
```
*Registers a lightweight Windows Scheduled Task running detached on user logon.*

---

## ⚙️ Configuration

Copy `.env.example` to `.env`:
```powershell
copy .env.example .env
```

Key environment settings:
- `OMIDAEMON_LLM_PROVIDER`: `gemini` (default), `openai`, or `anthropic`
- `OMIDAEMON_LLM_API_KEY`: Your LLM API key
- `OMIDAEMON_DRIVE_PATH`: Path to your local Google Drive transcripts folder (e.g. `G:\My Drive\Transcripts`)
- `OMIDAEMON_OBSIDIAN_VAULT`: Path to your local Obsidian vault (e.g. `C:\Users\andri\Documents\ObsidianVault`)
- `OMIDAEMON_EMAIL_PARTNER`: Partner's email address for briefings
- `OMIDAEMON_EMAIL_STAFF`: Staff mailing list / team address

---

## 🧪 Testing & Verification

Run the test harness:
```powershell
$env:PYTHONPATH="src"
python -m unittest discover tests -v
```

---

## 🛡️ Notch Standard 1.0 & Nudge Supervision

- **Supervisor**: Nudge by Notch (port 8765)
- **Status**: Registered in `desktop.roots` and synced with private bridge
- **Contract Boundaries**: `src/**`, `tests/**`, `config/**`, `pyproject.toml`, `README.md`, `.env.example`, `.gitignore`
