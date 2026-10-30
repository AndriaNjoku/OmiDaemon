"""Google Drive cloud API watcher for downloading transcripts directly from Drive."""

import json
import hashlib
from typing import List, Optional, Dict, Any
from pathlib import Path
import httpx
from ..models import TranscriptDocument
from .state_tracker import StateTracker


class GoogleDriveAPIWatcher:
    """
    Watches a Google Drive folder directly via Google Drive REST API v3.
    Requires an OAuth access token, Service Account, or API key.
    """

    def __init__(
        self,
        folder_id: str,
        state_tracker: StateTracker,
        access_token: Optional[str] = None,
        service_account_path: Optional[str] = None,
    ):
        self.folder_id = folder_id
        self.state_tracker = state_tracker
        self.access_token = access_token
        self.service_account_path = service_account_path
        self._cached_token = access_token

    def _get_auth_headers(self) -> Dict[str, str]:
        token = self._resolve_token()
        if not token:
            raise ValueError("No valid Google Drive access token configured.")
        return {"Authorization": f"Bearer {token}"}

    def _resolve_token(self) -> Optional[str]:
        if self._cached_token:
            return self._cached_token

        # If a service account file is provided, generate token
        if self.service_account_path and Path(self.service_account_path).is_file():
            try:
                from google.oauth2 import service_account
                import google.auth.transport.requests

                creds = service_account.Credentials.from_service_account_file(
                    self.service_account_path,
                    scopes=["https://www.googleapis.com/auth/drive.readonly"],
                )
                request = google.auth.transport.requests.Request()
                creds.refresh(request)
                self._cached_token = creds.token
                return self._cached_token
            except Exception as e:
                print(f"[DriveAPI] Error loading service account: {e}")

        return None

    def list_files(self) -> List[Dict[str, Any]]:
        """List files in the target Google Drive folder."""
        if not self.folder_id:
            return []

        headers = self._get_auth_headers()
        url = "https://www.googleapis.com/drive/v3/files"
        query = f"'{self.folder_id}' in parents and trashed = false"
        params = {
            "q": query,
            "fields": "files(id, name, mimeType, modifiedTime, size, md5Checksum)",
            "pageSize": 50,
        }

        with httpx.Client(timeout=20.0) as client:
            resp = client.get(url, headers=headers, params=params)
            if resp.status_code != 200:
                raise RuntimeError(f"Google Drive API error ({resp.status_code}): {resp.text}")
            return resp.json().get("files", [])

    def download_file_content(self, file_id: str, mime_type: str) -> str:
        """Download file content, exporting Google Docs to text if necessary."""
        headers = self._get_auth_headers()
        with httpx.Client(timeout=30.0) as client:
            # Handle Google Docs export vs binary download
            if mime_type == "application/vnd.google-apps.document":
                url = f"https://www.googleapis.com/drive/v3/files/{file_id}/export"
                resp = client.get(url, headers=headers, params={"mimeType": "text/plain"})
            else:
                url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media"
                resp = client.get(url, headers=headers)

            if resp.status_code != 200:
                raise RuntimeError(f"Failed to download Drive file {file_id}: {resp.text}")
            return resp.text

    def scan_for_unprocessed(self) -> List[TranscriptDocument]:
        """Fetch files from Drive API and return new/updated transcripts."""
        files = self.list_files()
        unprocessed = []

        for f in files:
            file_id = f["id"]
            file_name = f.get("name", file_id)
            # Filter for transcript-like extensions or docs
            valid_ext = any(file_name.lower().endswith(ext) for ext in (".txt", ".md", ".json"))
            is_gdoc = f.get("mimeType") == "application/vnd.google-apps.document"

            if not (valid_ext or is_gdoc):
                continue

            try:
                content = self.download_file_content(file_id, f.get("mimeType", ""))
                if not content.strip():
                    continue

                sha256 = hashlib.sha256(content.encode("utf-8")).hexdigest()
                virtual_path = f"gdrive://{self.folder_id}/{file_id}/{file_name}"

                if not self.state_tracker.is_processed(virtual_path, sha256):
                    doc = TranscriptDocument(
                        file_path=virtual_path,
                        file_name=file_name,
                        sha256=sha256,
                        content=content,
                        modified_time=0.0,
                    )
                    unprocessed.append(doc)
            except Exception as e:
                print(f"[DriveAPI] Error processing file {file_name} ({file_id}): {e}")

        return unprocessed
