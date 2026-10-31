"""Command-line interface for OmiDaemon."""

import argparse
import sys
import time
from pathlib import Path
from .config import AppConfig
from .models import TranscriptDocument
from .watcher import StateTracker, LocalDriveWatcher
from .processor import LLMClient, ContextEngine
from .dispatchers import ActionRouter
from .service import DaemonService


def process_single_file(file_path: Path, config: AppConfig, force: bool = False) -> None:
    """Process a single transcript file immediately."""
    if not file_path.is_file():
        print(f"[Error] File not found: {file_path}", file=sys.stderr)
        sys.exit(1)

    state_tracker = StateTracker(config.state_db_path)
    sha256 = LocalDriveWatcher.compute_sha256(file_path)

    if not force and state_tracker.is_processed(str(file_path), sha256):
        print(f"[Info] File has already been processed: {file_path.name} (use --force to reprocess)")
        return

    content = file_path.read_text(encoding="utf-8", errors="replace")
    doc = TranscriptDocument(
        file_path=str(file_path.resolve()),
        file_name=file_path.name,
        sha256=sha256,
        content=content,
        modified_time=file_path.stat().st_mtime,
    )

    print(f"\nProcessing transcript: {doc.file_name} ({len(content)} chars)...")
    llm_client = LLMClient(config.llm)
    engine = ContextEngine(llm_client)

    try:
        result = engine.process(doc)
    except Exception as e:
        print(f"[Error] Context reasoning failed: {e}", file=sys.stderr)
        state_tracker.record_failure(str(file_path), sha256, str(e))
        sys.exit(1)

    print(f"\n=======================================================")
    print(f"  Title: {result.title}")
    print(f"  Category: {result.category}")
    print(f"  Summary: {result.summary}")
    print(f"  Decisions: {len(result.key_decisions)}")
    print(f"  Action Items: {len(result.action_items)}")
    print(f"=======================================================\n")

    router = ActionRouter(config)
    report = router.route(result, doc)

    print("Routing Executed:")
    if report["obsidian"]:
        print(f"  [Obsidian] Note created -> {report['obsidian']}")
    if report["email"]:
        print(f"  [Email] Status: {report['email'].get('status')} -> {report['email'].get('saved_path') or report['email'].get('recipients')}")
    if report["slides"]:
        print(f"  [Slides] Deck generated -> {report['slides']}")
    if report["calendar"]:
        print(f"  [Calendar] Events created -> {len(report['calendar'])} event(s)")

    state_tracker.record_success(
        file_path=str(file_path),
        sha256=sha256,
        file_mtime=doc.modified_time,
        title=result.title,
        category=str(result.category),
        routing_data=report,
    )
    print("\nProcessing complete and state recorded successfully.")


def run_daemon(config: AppConfig) -> None:
    """Run the continuous monitoring loop."""
    drive_path = config.source.drive_path
    if not drive_path:
        print("[Error] No drive_path configured. Set OMIDAEMON_DRIVE_PATH in .env or config/default_config.yaml", file=sys.stderr)
        sys.exit(1)

    drive_dir = Path(drive_path).resolve()
    if not drive_dir.is_dir():
        print(f"[Error] Google Drive directory not found: {drive_dir}", file=sys.stderr)
        sys.exit(1)

    state_tracker = StateTracker(config.state_db_path)
    watcher = LocalDriveWatcher(str(drive_dir), state_tracker, config.source.file_patterns)
    llm_client = LLMClient(config.llm)
    engine = ContextEngine(llm_client)
    router = ActionRouter(config)

    print("=======================================================")
    print("  OmiDaemon Active — Watching Google Drive")
    print(f"  Drive Folder: {drive_dir}")
    print(f"  Poll Interval: {config.source.poll_interval_seconds}s")
    print(f"  LLM Provider: {config.llm.provider} ({config.llm.model})")
    print("  Press Ctrl+C to stop.")
    print("=======================================================\n")

    try:
        for doc in watcher.poll(interval_seconds=config.source.poll_interval_seconds):
            print(f"[{time.strftime('%X')}] New transcript detected: {doc.file_name}")
            try:
                result = engine.process(doc)
                report = router.route(result, doc)
                state_tracker.record_success(
                    file_path=doc.file_path,
                    sha256=doc.sha256,
                    file_mtime=doc.modified_time,
                    title=result.title,
                    category=str(result.category),
                    routing_data=report,
                )
                print(f"[{time.strftime('%X')}] Successfully processed & routed '{result.title}'")
            except Exception as e:
                print(f"[{time.strftime('%X')}] [Error] Processing failed for {doc.file_name}: {e}", file=sys.stderr)
                state_tracker.record_failure(doc.file_path, doc.sha256, str(e))
    except KeyboardInterrupt:
        print("\nOmiDaemon shutting down gracefully.")


def main() -> None:
    parser = argparse.ArgumentParser(description="OmiDaemon: Wearable AI Transcript Intelligence Engine")
    parser.add_argument("--config", "-c", help="Path to config.yaml", default=None)
    subparsers = parser.add_subparsers(dest="command")

    # Command: start (foreground)
    subparsers.add_parser("start", help="Start continuous Google Drive monitoring in foreground")

    # Command: start-bg (background)
    subparsers.add_parser("start-bg", help="Start continuous monitoring daemon in background (windowless)")

    # Command: stop-bg (background)
    subparsers.add_parser("stop-bg", help="Stop running background daemon")

    # Command: status-bg
    subparsers.add_parser("status-bg", help="Check status of background daemon process")

    # Command: tray
    subparsers.add_parser("tray", help="Launch the native Windows System Tray application")

    # Command: install-startup
    subparsers.add_parser("install-startup", help="Configure OmiDaemon to auto-start on Windows login")

    # Command: process <file>
    process_p = subparsers.add_parser("process", help="Process a single transcript file")
    process_p.add_argument("file", help="Path to transcript file (.txt, .md, .json)")
    process_p.add_argument("--force", "-f", action="store_true", help="Reprocess even if already in state DB")

    # Command: status
    subparsers.add_parser("status", help="Show recent processing history and state")

    args = parser.parse_args()
    config = AppConfig.load(args.config)
    service = DaemonService()

    if args.command == "start" or args.command is None:
        if args.command is None and len(sys.argv) > 1:
            parser.print_help()
            sys.exit(1)
        run_daemon(config)
    elif args.command == "start-bg":
        res = service.start_background(args.config)
        if res["status"] == "started":
            print(f"[OmiDaemon] Background daemon started successfully (PID: {res['pid']}).")
            print(f"[OmiDaemon] Logging to: {res['log']}")
        elif res["status"] == "already_running":
            print(f"[OmiDaemon] Daemon is already running (PID: {res['pid']}). Log: {res['log']}")
        else:
            print(f"[OmiDaemon] Failed to start daemon: {res}")
    elif args.command == "stop-bg":
        res = service.stop_background()
        if res["status"] == "stopped":
            print(f"[OmiDaemon] Stopped background daemon (PID: {res['pid']}).")
        elif res["status"] == "not_running":
            print("[OmiDaemon] No background daemon is currently running.")
        else:
            print(f"[OmiDaemon] Error stopping daemon: {res}")
    elif args.command == "status-bg":
        running, pid = service.is_running()
        if running:
            print(f"[OmiDaemon] Background daemon is RUNNING (PID: {pid}).")
            print(f"[OmiDaemon] Log file: {service.log_file}")
        else:
            print("[OmiDaemon] Background daemon is STOPPED.")
    elif args.command == "tray":
        tray_exe = Path(__file__).resolve().parent.parent.parent / "windows" / "OmiDaemonTray.exe"
        if not tray_exe.exists():
            print(f"[Error] Tray executable not found at {tray_exe}. Run windows/build_tray.ps1 to build it.", file=sys.stderr)
            sys.exit(1)
        import subprocess
        print(f"[OmiDaemon] Launching System Tray application ({tray_exe.name})...")
        subprocess.Popen([str(tray_exe)], cwd=str(tray_exe.parent.parent))
    elif args.command == "install-startup":
        res = service.install_startup_task()
        if res["status"] == "installed":
            print(f"[OmiDaemon] Windows startup task '{res['task_name']}' created successfully.")
            print("[OmiDaemon] The daemon will automatically launch in the background whenever you log into Windows.")
        else:
            print(f"[OmiDaemon] Failed to install startup task: {res.get('error')}")
    elif args.command == "process":
        process_single_file(Path(args.file), config, force=args.force)
    elif args.command == "status":
        tracker = StateTracker(config.state_db_path)
        records = tracker.list_recent(limit=15)
        print("\n=== OmiDaemon Recent Processed Transcripts ===")
        if not records:
            print("No transcripts have been processed yet.")
        for r in records:
            dt = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(r["processed_at"]))
            print(f"[{dt}] [{r['status'].upper()}] {r['title'] or Path(r['file_path']).name} ({r['category'] or 'unknown'})")
        print("")


if __name__ == "__main__":
    main()
