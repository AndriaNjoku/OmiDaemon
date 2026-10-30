"""Local filesystem watcher for Google Drive synced folder."""

import hashlib
import time
from pathlib import Path
from typing import List, Generator, Optional
from ..models import TranscriptDocument
from .state_tracker import StateTracker


class LocalDriveWatcher:
    def __init__(
        self,
        drive_path: str,
        state_tracker: StateTracker,
        file_patterns: Optional[List[str]] = None,
    ):
        self.drive_path = Path(drive_path).resolve() if drive_path else None
        self.state_tracker = state_tracker
        self.file_patterns = file_patterns or ["*.txt", "*.md", "*.json"]

    @staticmethod
    def compute_sha256(file_path: Path) -> str:
        h = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(65536):
                h.update(chunk)
        return h.hexdigest()

    def scan_for_unprocessed(self) -> List[TranscriptDocument]:
        """Scan directory and return list of unprocessed or modified documents."""
        if not self.drive_path or not self.drive_path.is_dir():
            return []

        unprocessed: List[TranscriptDocument] = []

        # Gather files matching patterns
        matched_files = set()
        for pattern in self.file_patterns:
            for p in self.drive_path.rglob(pattern):
                if p.is_file():
                    matched_files.add(p)

        # Sort chronologically by modification time
        sorted_files = sorted(matched_files, key=lambda f: f.stat().st_mtime)

        for p in sorted_files:
            try:
                stat = p.stat()
                # Skip 0-byte files that are still being written by sync
                if stat.st_size == 0:
                    continue

                sha256 = self.compute_sha256(p)
                if not self.state_tracker.is_processed(str(p), sha256):
                    # Read content
                    content = p.read_text(encoding="utf-8", errors="replace")
                    doc = TranscriptDocument(
                        file_path=str(p.resolve()),
                        file_name=p.name,
                        sha256=sha256,
                        content=content,
                        modified_time=stat.st_mtime,
                    )
                    unprocessed.append(doc)
            except Exception as e:
                print(f"[Watcher] Error reading {p}: {e}")

        return unprocessed

    def poll(self, interval_seconds: int = 15) -> Generator[TranscriptDocument, None, None]:
        """Continuous polling generator yielding new transcripts as they arrive."""
        while True:
            docs = self.scan_for_unprocessed()
            for doc in docs:
                yield doc
            time.sleep(interval_seconds)
