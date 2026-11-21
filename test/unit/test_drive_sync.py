"""
test/unit/test_drive_sync.py — Unit tests for Google Drive sync connectivity and router.
"""

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, call, patch

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

    def test_upload_or_update_file_handles_new_and_replace(self):
        """Verify upload_or_update_file creates new files and deletes all existing duplicates after re-uploading."""
        mock_service = MagicMock()
        client = GoogleDriveClient(root_folder_id="ROOT123")
        client._service = mock_service

        mock_files = mock_service.files.return_value

        with patch("pathlib.Path.exists", return_value=True), \
             patch("googleapiclient.http.MediaFileUpload"):

            # Case A: File does not exist -> creates it without delete()
            mock_files.list.return_value.execute.return_value = {"files": []}
            mock_req_create = MagicMock()
            mock_req_create.next_chunk.return_value = (None, {"id": "FILE_111", "webViewLink": "https://drive/111"})
            mock_files.create.return_value = mock_req_create

            res_create = client.upload_or_update_file("dummy.mp4", "EE01.mp4", "PARENT_FOLDER")
            self.assertEqual(res_create["id"], "FILE_111")
            self.assertEqual(res_create["name"], "EE01.mp4")
            mock_files.create.assert_called_once()
            mock_files.delete.assert_not_called()

            # Case B: Duplicate existing files -> uploads a fresh file, then deletes previous file IDs
            mock_files.create.reset_mock()
            mock_files.delete.reset_mock()
            mock_files.update.reset_mock()
            mock_files.list.return_value.execute.return_value = {
                "files": [
                    {"id": "EXISTING_222", "name": "EE01.mp4"},
                    {"id": "DUP_333", "name": "EE01.mp4"},
                ]
            }
            mock_req_reupload = MagicMock()
            mock_req_reupload.next_chunk.return_value = (None, {"id": "FRESH_444", "webViewLink": "https://drive/444"})
            mock_files.create.return_value = mock_req_reupload

            res_replace = client.upload_or_update_file("dummy.mp4", "EE01.mp4", "PARENT_FOLDER")
            self.assertEqual(res_replace["id"], "FRESH_444")
            mock_files.delete.assert_has_calls([
                call(fileId="EXISTING_222", supportsAllDrives=True),
                call().execute(),
                call(fileId="DUP_333", supportsAllDrives=True),
                call().execute(),
            ])
            mock_files.create.assert_called_once()
            mock_files.update.assert_not_called()

    def test_delete_file_permanent_trash_fallback_and_404(self):
        """Verify permanent delete, 403 trash fallback, 404 False return, and folder cache eviction."""
        mock_service = MagicMock()
        client = GoogleDriveClient(root_folder_id="ROOT123")
        client._service = mock_service
        mock_files = mock_service.files.return_value

        # 1. Permanent delete + cache eviction
        client._folder_cache[("ROOT123", "english")] = "F1"
        self.assertTrue(client.delete_file("F1", "english"))
        mock_files.delete.assert_called_once_with(fileId="F1", supportsAllDrives=True)
        self.assertNotIn(("ROOT123", "english"), client._folder_cache)

        # 2. HTTP 403 -> falls back to moving item to Trash
        err_403 = Exception("Forbidden")
        err_403.resp = SimpleNamespace(status=403)
        mock_files.delete.return_value.execute.side_effect = err_403
        client._folder_cache[("P1", "dup")] = "F2"
        self.assertTrue(client.delete_file("F2", "EE01.mp4"))
        mock_files.update.assert_called_once_with(fileId="F2", body={"trashed": True}, supportsAllDrives=True)
        self.assertNotIn(("P1", "dup"), client._folder_cache)

        # 3. HTTP 404 -> returns False cleanly
        err_404 = Exception("Not Found")
        err_404.resp = SimpleNamespace(status=404)
        mock_files.delete.return_value.execute.side_effect = err_404
        self.assertFalse(client.delete_file("F3", "missing.mp4"))

        # 4. Unexpected HTTP 500 -> re-raises
        err_500 = Exception("Server Error")
        err_500.resp = SimpleNamespace(status=500)
        mock_files.delete.return_value.execute.side_effect = err_500
        with self.assertRaises(Exception):
            client.delete_file("F4", "boom.mp4")

    def test_clear_folder_deletes_all_paginated_items(self):
        """Verify clear_folder paginates through all items and deletes every child."""
        mock_service = MagicMock()
        client = GoogleDriveClient(root_folder_id="ROOT123")
        client._service = mock_service
        mock_files = mock_service.files.return_value

        mock_files.list.return_value.execute.side_effect = [
            {
                "files": [
                    {"id": "ITEM_1", "name": "EE01.mp4", "mimeType": "video/mp4"},
                    {"id": "ITEM_2", "name": "EE01_thumbnail.png", "mimeType": "image/png"},
                ],
                "nextPageToken": "TOK_2",
            },
            {
                "files": [
                    {"id": "ITEM_3", "name": "old_notes.txt", "mimeType": "text/plain"},
                ],
            },
        ]

        deleted_count = client.clear_folder("FOLDER_EE01")
        self.assertEqual(deleted_count, 3)
        self.assertEqual(mock_files.list.call_count, 2)
        second_call_kwargs = mock_files.list.call_args_list[1][1]
        self.assertEqual(second_call_kwargs.get("pageToken"), "TOK_2")
        mock_files.delete.assert_has_calls([
            call(fileId="ITEM_1", supportsAllDrives=True),
            call().execute(),
            call(fileId="ITEM_2", supportsAllDrives=True),
            call().execute(),
            call(fileId="ITEM_3", supportsAllDrives=True),
            call().execute(),
        ])

    def test_delete_duplicate_folders_removes_extras_only(self):
        """Verify delete_duplicate_folders preserves keep_folder_id and deletes duplicates."""
        mock_service = MagicMock()
        client = GoogleDriveClient(root_folder_id="ROOT123")
        client._service = mock_service
        mock_files = mock_service.files.return_value

        mock_files.list.return_value.execute.return_value = {
            "files": [
                {"id": "SCRIPT_KEEP", "name": "EE01"},
                {"id": "SCRIPT_DUP1", "name": "EE01"},
                {"id": "SCRIPT_DUP2", "name": "EE01"},
            ]
        }

        deleted_count = client.delete_duplicate_folders("EE01", parent_id="TYPE_EXPR", keep_folder_id="SCRIPT_KEEP")
        self.assertEqual(deleted_count, 2)
        deleted_ids = [c.kwargs["fileId"] for c in mock_files.delete.call_args_list if "fileId" in c.kwargs]
        self.assertEqual(deleted_ids, ["SCRIPT_DUP1", "SCRIPT_DUP2"])

    def test_upload_script_to_drive_end_to_end(self):
        """Verify upload_script_to_drive traverses hierarchy, clears existing Drive items, uploads assets cleanly, and updates state."""
        mock_client = MagicMock()
        mock_client.root_folder_id = DEFAULT_ROOT_FOLDER_ID
        mock_client.get_or_create_folder.side_effect = [
            "LANG_EN_ID",     # Step 1: language folder
            "TYPE_EXPR_ID",   # Step 2: video type folder
            "SCRIPT_EE01_ID", # Step 3: script ID folder
        ]
        mock_client.list_named_files.side_effect = [
            [{"id": "OLD_VIDEO", "name": "EE01.mp4"}],
            [{"id": "OLD_THUMB", "name": "EE01_thumbnail.png"}],
        ]
        mock_client.delete_file.return_value = True
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
        self.assertEqual(result["deleted_existing_count"], 2)
        self.assertEqual(result["video"]["name"], "EE01.mp4")
        self.assertEqual(result["thumbnail"]["name"], "EE01_thumbnail.png")

        mock_client.delete_duplicate_folders.assert_not_called()
        mock_client.clear_folder.assert_not_called()
        mock_client.delete_file.assert_has_calls([
            call("OLD_VIDEO", "EE01.mp4"),
            call("OLD_THUMB", "EE01_thumbnail.png"),
        ])

        call_names = [c[0] for c in mock_client.mock_calls]
        last_upload = max(i for i, name in enumerate(call_names) if name == "upload_or_update_file")
        self.assertLess(last_upload, call_names.index("delete_file"))

        # Verify state was saved with drive status
        self.assertTrue(mock_sm.save_script_state.called)
        saved_id, saved_data = mock_sm.save_script_state.call_args[0]
        self.assertEqual(saved_id, "EE01")
        self.assertEqual(saved_data["status"]["drive_upload"], "done")
        self.assertEqual(saved_data["assets"]["drive_folder_id"], "SCRIPT_EE01_ID")
        self.assertIn("drive.google.com/drive/folders/SCRIPT_EE01_ID", saved_data["assets"]["drive_folder_url"])

    def test_failed_thumbnail_upload_keeps_previous_drive_files(self):
        client = MagicMock()
        client.list_named_files.side_effect = [
            [{"id": "OLD_VIDEO", "name": "EE01.mp4"}],
            [{"id": "OLD_THUMB", "name": "EE01_thumbnail.png"}],
        ]
        client.upload_or_update_file.side_effect = [
            {"id": "NEW_VIDEO"}, OSError("thumbnail upload failed"),
        ]
        state = MagicMock()
        state.load_script_state.return_value = {
            "id": "EE01",
            "content_metadata": {"language": "english", "video_type": "expression"},
            "assets": {"final_video": "old.mp4", "thumbnail_path": "thumb.png"},
        }

        with patch("pathlib.Path.exists", return_value=True):
            with self.assertRaisesRegex(OSError, "thumbnail upload failed"):
                upload_script_to_drive("EE01", client=client, state_mgr=state)

        client.delete_file.assert_called_once_with("NEW_VIDEO", "EE01.mp4")
        client.delete_duplicate_folders.assert_not_called()
        state.save_script_state.assert_not_called()

    def test_upload_script_to_drive_missing_local_file_does_not_delete_remote(self):
        """Verify missing local assets fail before any Drive lookup or deletion."""
        mock_client = MagicMock()
        mock_sm = MagicMock()
        mock_sm.load_script_state.return_value = {
            "id": "EE01",
            "content_metadata": {"language": "english", "video_type": "expression"},
            "assets": {},
        }

        with patch("pathlib.Path.exists", return_value=False):
            with self.assertRaises(FileNotFoundError):
                upload_script_to_drive("EE01", client=mock_client, state_mgr=mock_sm)

        mock_client.get_or_create_folder.assert_not_called()
        mock_client.delete_duplicate_folders.assert_not_called()
        mock_client.clear_folder.assert_not_called()


if __name__ == "__main__":
    unittest.main()

