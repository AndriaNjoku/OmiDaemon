import unittest
from unittest.mock import patch, MagicMock
from omidaemon.watcher.drive_api_watcher import GoogleDriveAPIWatcher
from omidaemon.watcher.state_tracker import StateTracker
import tempfile
import os


class TestDriveAPIWatcher(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "state.db")
        self.tracker = StateTracker(self.db_path)
        self.watcher = GoogleDriveAPIWatcher(
            folder_id="mock_folder_123",
            state_tracker=self.tracker,
            access_token="mock_token_abc",
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_auth_header(self):
        headers = self.watcher._get_auth_headers()
        self.assertEqual(headers["Authorization"], "Bearer mock_token_abc")

    @patch("httpx.Client.get")
    def test_list_and_download_flow(self, mock_get):
        # Mock file list response
        mock_list_resp = MagicMock()
        mock_list_resp.status_code = 200
        mock_list_resp.json.return_value = {
            "files": [
                {
                    "id": "file_01",
                    "name": "wearable_transcript.txt",
                    "mimeType": "text/plain",
                }
            ]
        }

        # Mock download response
        mock_dl_resp = MagicMock()
        mock_dl_resp.status_code = 200
        mock_dl_resp.text = "Speaker 1: Testing Google Drive API download."

        mock_get.side_effect = [mock_list_resp, mock_dl_resp]

        docs = self.watcher.scan_for_unprocessed()
        self.assertEqual(len(docs), 1)
        self.assertEqual(docs[0].file_name, "wearable_transcript.txt")
        self.assertIn("Testing Google Drive API", docs[0].content)


if __name__ == "__main__":
    unittest.main()
