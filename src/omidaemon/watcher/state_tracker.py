"""SQLite-backed state tracking for idempotent transcript processing."""

import sqlite3
import json
import time
from pathlib import Path
from typing import Optional, Dict, Any, List
from contextlib import contextmanager


class StateTracker:
    def __init__(self, db_path: str = "data/omidaemon_state.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(str(self.db_path), timeout=15.0)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_db(self) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS processed_transcripts (
                    file_path TEXT PRIMARY KEY,
                    sha256 TEXT NOT NULL,
                    file_mtime REAL NOT NULL,
                    processed_at REAL NOT NULL,
                    status TEXT NOT NULL,
                    title TEXT,
                    category TEXT,
                    routing_data TEXT,
                    error_message TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_sha256 ON processed_transcripts(sha256)
                """
            )

    def is_processed(self, file_path: str, sha256: str) -> bool:
        """Check if file has already been successfully processed with the exact same content hash."""
        with self._conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT status, sha256 FROM processed_transcripts WHERE file_path = ?",
                (str(Path(file_path).resolve()),),
            )
            row = cursor.fetchone()
            if not row:
                return False
            return bool(row["status"] == "success" and row["sha256"] == sha256)

    def record_success(
        self,
        file_path: str,
        sha256: str,
        file_mtime: float,
        title: str,
        category: str,
        routing_data: Optional[Dict[str, Any]] = None,
    ) -> None:
        resolved_path = str(Path(file_path).resolve())
        serialized_routing = json.dumps(routing_data or {}, ensure_ascii=False)
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO processed_transcripts 
                    (file_path, sha256, file_mtime, processed_at, status, title, category, routing_data, error_message)
                VALUES (?, ?, ?, ?, 'success', ?, ?, ?, NULL)
                ON CONFLICT(file_path) DO UPDATE SET
                    sha256 = excluded.sha256,
                    file_mtime = excluded.file_mtime,
                    processed_at = excluded.processed_at,
                    status = excluded.status,
                    title = excluded.title,
                    category = excluded.category,
                    routing_data = excluded.routing_data,
                    error_message = NULL
                """,
                (resolved_path, sha256, file_mtime, time.time(), title, category, serialized_routing),
            )

    def record_failure(self, file_path: str, sha256: str, error_message: str) -> None:
        resolved_path = str(Path(file_path).resolve())
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO processed_transcripts 
                    (file_path, sha256, file_mtime, processed_at, status, title, category, routing_data, error_message)
                VALUES (?, ?, 0, ?, 'error', NULL, NULL, NULL, ?)
                ON CONFLICT(file_path) DO UPDATE SET
                    sha256 = excluded.sha256,
                    processed_at = excluded.processed_at,
                    status = excluded.status,
                    error_message = excluded.error_message
                """,
                (resolved_path, sha256, time.time(), error_message),
            )

    def list_recent(self, limit: int = 20) -> List[Dict[str, Any]]:
        with self._conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT file_path, sha256, processed_at, status, title, category, error_message
                FROM processed_transcripts
                ORDER BY processed_at DESC
                LIMIT ?
                """,
                (limit,),
            )
            return [dict(row) for row in cursor.fetchall()]
