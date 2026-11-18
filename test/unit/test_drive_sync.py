"""
test/unit/test_drive_sync.py — Unit tests for Google Drive sync connectivity and router.
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

MAIN_DIR = Path(__file__).resolve().parent.parent.parent / "main"
if str(MAIN_DIR) not in sys.path:
    sys.path.insert(0, str(MAIN_DIR))

# pyrefly: ignore[missing-import]
from connectivity.drive_sync.drive_client import GoogleDriveClient, DEFAULT_ROOT_FOLDER_ID
# pyrefly: ignore[missing-import]
from connectivity.drive_sync.sync_service import (
    map_language_to_folder,

    map_video_type_to_folder,
    resolve_script_assets,
    upload_script_to_drive,
)


class TestDriveSync(unittest.TestCase):
    def test_map_language_to_folder(self):
        """Verify language normalization to lowercase folder names."""
        self.assertEqual(map_language_to_folder("English"), "english")
        self.assertEqual(map_language_to_folder("FRENCH"), "french")
        self.assertEqual(map_language_to_folder("Italiano"), "italian")
        self.assertEqual(map_language_to_folder("spanish"), "spanish")
        self.assertEqual(map_language_to_folder("es"), "spanish")
        self.assertEqual(map_language_to_folder("unknown"), "english")

    def test_map_video_type_to_folder(self):
        """Verify video type mapping to exact target folder names."""
        self.assertEqual(map_video_type_to_folder("expression"), "expressions")
        self.assertEqual(map_video_type_to_folder("EXPRESSIONS"), "expressions")
        self.assertEqual(map_video_type_to_folder("fun_facts"), "fun_facts")
        self.assertEqual(map_video_type_to_folder("facts"), "fun_facts")
        self.assertEqual(map_video_type_to_folder("game"), "game")
        self.assertEqual(map_video_type_to_folder("quiz"), "game")
        self.assertEqual(map_video_type_to_folder("roleplay"), "role_play")
        self.assertEqual(map_video_type_to_folder("ROLE_PLAY"), "role_play")

    def test_resolve_script_assets_from_state(self):
        """Verify asset path resolution when paths exist in state."""
        with patch("pathlib.Path.exists", return_value=True):
            script_data = {
                "id": "EE01",
                "assets": {
                    "final_video": "D:/dummy/video.mp4",
                    "thumbnail_path": "D:/dummy/thumb.png",
                },
            }
            v_path, t_path = resolve_script_assets(script_data)
            self.assertIsNotNone(v_path)
            self.assertIsNotNone(t_path)
            self.assertEqual(v_path.name, "video.mp4")
            self.assertEqual(t_path.name, "thumb.png")

    def test_get_or_create_folder_caches_and_creates(self):
        """Verify get_or_create_folder queries Drive or creates folder if missing."""
        mock_service = MagicMock()
        client = GoogleDriveClient(root_folder_id="ROOT123")
        client._service = mock_service

        # 1. Folder exists
        mock_files = mock_service.files.return_value
        mock_files.list.return_value.execute.return_value = {
            "files": [{"id": "FOLDER_ABC", "name": "english"}]
        }

        fid = client.get_or_create_folder("english", parent_id="ROOT123")
        self.assertEqual(fid, "FOLDER_ABC")
        self.assertIn(("ROOT123", "english"), client._folder_cache)

        # 2. Cache hit (does not call API again)
        mock_files.list.reset_mock()
        fid_cached = client.get_or_create_folder("english", parent_id="ROOT123")
        self.assertEqual(fid_cached, "FOLDER_ABC")
        mock_files.list.assert_not_called()

        # 3. Folder does not exist -> creates it
        mock_files.list.return_value.execute.return_value = {"files": []}
        mock_files.create.return_value.execute.return_value = {"id": "FOLDER_NEW_XYZ"}

        fid_new = client.get_or_create_folder("role_play", parent_id="FOLDER_ABC")
        self.assertEqual(fid_new, "FOLDER_NEW_XYZ")
        mock_files.create.assert_called_once()

    def test_upload_or_update_file_handles_new_and_update(self):
        """Verify upload_or_update_file checks for existing file before uploading."""
        mock_service = MagicMock()
        client = GoogleDriveClient(root_folder_id="ROOT123")
        client._service = mock_service

        mock_files = mock_service.files.return_value

        with patch("pathlib.Path.exists", return_value=True), \
             patch("googleapiclient.http.MediaFileUpload"):

            # Case A: File does not exist -> creates it
            mock_files.list.return_value.execute.return_value = {"files": []}
            mock_req_create = MagicMock()
            mock_req_create.next_chunk.return_value = (None, {"id": "FILE_111", "webViewLink": "https://drive/111"})
            mock_files.create.return_value = mock_req_create

            res_create = client.upload_or_update_file("dummy.mp4", "EE01.mp4", "PARENT_FOLDER")
            self.assertEqual(res_create["id"], "FILE_111")
            self.assertEqual(res_create["name"], "EE01.mp4")
            mock_files.create.assert_called_once()

            # Case B: File exists -> updates it
            mock_files.list.return_value.execute.return_value = {
                "files": [{"id": "EXISTING_222", "name": "EE01.mp4"}]
            }
            mock_req_update = MagicMock()
            mock_req_update.next_chunk.return_value = (None, {"id": "EXISTING_222", "webViewLink": "https://drive/222"})
            mock_files.update.return_value = mock_req_update

            res_update = client.upload_or_update_file("dummy.mp4", "EE01.mp4", "PARENT_FOLDER")
            self.assertEqual(res_update["id"], "EXISTING_222")
            mock_files.update.assert_called_once()

    def test_upload_script_to_drive_end_to_end(self):
        """Verify upload_script_to_drive traverses hierarchy, renames assets cleanly, and updates state."""
        mock_client = MagicMock()
        mock_client.root_folder_id = DEFAULT_ROOT_FOLDER_ID
        mock_client.get_or_create_folder.side_effect = [
            "LANG_EN_ID",     # Step 1: language folder
            "TYPE_EXPR_ID",   # Step 2: video type folder
            "SCRIPT_EE01_ID", # Step 3: script ID folder
        ]
        mock_client.upload_or_update_file.side_effect = [
            {"id": "VID_999", "name": "EE01.mp4", "web_view_link": "https://drive.google.com/file/d/VID_999/view"},
            {"id": "THUMB_888", "name": "EE01_thumbnail.png", "web_view_link": "https://drive.google.com/file/d/THUMB_888/view"},
        ]

        mock_sm = MagicMock()
        state_doc = {
            "id": "EE01",
            "content_metadata": {
                "language": "english",
                "video_type": "expression",
            },
            "status": {
                "video_assembly": "done",
                "thumbnail_generation": "done",
            },
            "assets": {
                "final_video": "D:/AI/output/video_assets/english/expression/script_EE01/script_EE01_final.mp4",
                "thumbnail_path": "D:/AI/output/video_assets/english/expression/script_EE01/thumbnail.png",
            },
        }
        mock_sm.load_script_state.return_value = state_doc

        with patch("pathlib.Path.exists", return_value=True):
            result = upload_script_to_drive(
                script_id="EE01",
                client=mock_client,
                state_mgr=mock_sm,
            )

        self.assertEqual(result["script_id"], "EE01")
        self.assertEqual(result["language"], "english")
        self.assertEqual(result["video_type"], "expressions")
        self.assertEqual(result["folder_id"], "SCRIPT_EE01_ID")
        self.assertEqual(result["video"]["name"], "EE01.mp4")
        self.assertEqual(result["thumbnail"]["name"], "EE01_thumbnail.png")

        # Verify state was saved with drive status
        self.assertTrue(mock_sm.save_script_state.called)
        saved_id, saved_data = mock_sm.save_script_state.call_args[0]
        self.assertEqual(saved_id, "EE01")
        self.assertEqual(saved_data["status"]["drive_upload"], "done")
        self.assertEqual(saved_data["assets"]["drive_folder_id"], "SCRIPT_EE01_ID")
        self.assertIn("drive.google.com/drive/folders/SCRIPT_EE01_ID", saved_data["assets"]["drive_folder_url"])


if __name__ == "__main__":
    unittest.main()

