"""
drive_client.py — Google Drive API v3 client for Shorts Automation.

Handles:
- Headless Service Account authentication with fallback to OAuth 2.0 user credentials.
- In-memory folder lookup caching and auto-creation.
- Creating resumable uploads and retiring prior files by ID.
- Resumable chunked file uploads for large MP4 video files and PNG thumbnails.
"""

from __future__ import annotations

import logging
import mimetypes
import os
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Scopes required for full read/write management in shared folders
SCOPES = ["https://www.googleapis.com/auth/drive"]

DEFAULT_ROOT_FOLDER_ID = "15HhCvcrsaAn3fLQM7Hdv3J0HVgcp39_Z"


class GoogleDriveClient:
    """Client for Google Drive API v3 operations."""

    def __init__(
        self,
        credentials_path: Optional[str | Path] = None,
        root_folder_id: str = DEFAULT_ROOT_FOLDER_ID,
    ) -> None:
        self.root_folder_id = root_folder_id
        self._folder_cache: Dict[Tuple[str, str], str] = {}
        self._service = None
        self.credentials_path = self._resolve_credentials_path(credentials_path)

    @staticmethod
    def _resolve_credentials_path(custom_path: Optional[str | Path] = None) -> Optional[Path]:
        """Resolves the path to the credentials JSON file (service_account.json, token.json, or client_secret.json)."""
        if custom_path:
            p = Path(custom_path).resolve()
            if p.exists():
                return p

        # Check environment variable
        env_cred = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        if env_cred and Path(env_cred).exists():
            return Path(env_cred).resolve()

        # Check standard project locations for service_account, token, or client_secret
        base_dir = Path(__file__).resolve().parents[2]
        cred_dirs = [
            base_dir / "credentials",
            base_dir.parent / "credentials",
        ]
        
        file_priorities = [
            "token.json",
            "service_account.json",
            "client_secret.json",
        ]

        for cdir in cred_dirs:
            for fname in file_priorities:
                candidate = cdir / fname
                if candidate.exists():
                    return candidate.resolve()

        return None

    def authenticate(self) -> Any:
        """
        Authenticates with Google Drive API v3 using either:
        1. OAuth 2.0 authorized user token (token.json) / Desktop App flow (client_secret.json)
        2. Service Account credentials (service_account.json)
        Returns the Drive API service resource.
        """
        if self._service is not None:
            return self._service

        try:
            # pyrefly: ignore[missing-import]
            from google.oauth2 import service_account
            # pyrefly: ignore[missing-import]
            from google.oauth2.credentials import Credentials
            # pyrefly: ignore[missing-import]
            from google.auth.transport.requests import Request
            # pyrefly: ignore[missing-import]
            from googleapiclient.discovery import build
        except ImportError as e:
            raise ImportError(
                "Google Drive client requires 'google-api-python-client', 'google-auth', and 'google-auth-oauthlib'. "
                "Install them with: py -m pip install google-api-python-client google-auth google-auth-httplib2 google-auth-oauthlib"
            ) from e

        cred_path = self.credentials_path
        if not cred_path or not cred_path.exists():
            raise FileNotFoundError(
                "Google Drive credentials not found! Please place either:\n"
                "  1) 'client_secret.json' (OAuth 2.0 Desktop App, recommended)\n"
                "  2) 'service_account.json' (Service Account)\n"
                "in 'main/credentials/'."
            )

        try:
            import json
            with open(cred_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as exc:
            raise RuntimeError(f"Failed to read credentials file at {cred_path}: {exc}") from exc

        creds = None
        base_cred_dir = cred_path.parent
        token_path = base_cred_dir / "token.json"

        # Case 1: Service Account JSON
        if data.get("type") == "service_account":
            try:
                creds = service_account.Credentials.from_service_account_file(
                    str(cred_path),
                    scopes=SCOPES,
                )
                logger.info("Authenticated with Google Drive via Service Account (%s)", cred_path.name)
            except Exception as exc:
                logger.error("Failed to authenticate with Service Account at %s: %s", cred_path, exc)
                raise RuntimeError(f"Google Drive Service Account authentication failed: {exc}") from exc

        # Case 2: OAuth 2.0 Token JSON directly
        elif "token" in data or "refresh_token" in data:
            try:
                creds = Credentials.from_authorized_user_file(str(cred_path), SCOPES)
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                    with open(cred_path, "w", encoding="utf-8") as token_file:
                        token_file.write(creds.to_json())
                logger.info("Authenticated with Google Drive via user token (%s)", cred_path.name)
            except Exception as exc:
                logger.error("Failed to authenticate with token at %s: %s", cred_path, exc)
                raise RuntimeError(f"Google Drive token authentication failed: {exc}") from exc

        # Case 3: OAuth 2.0 Client Secret (Desktop App)
        elif "installed" in data or "web" in data:
            # Check if an existing valid token.json exists in the same directory
            if token_path.exists():
                try:
                    creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
                    if creds and creds.expired and creds.refresh_token:
                        creds.refresh(Request())
                        with open(token_path, "w", encoding="utf-8") as token_file:
                            token_file.write(creds.to_json())
                    logger.info("Authenticated with Google Drive using cached token (%s)", token_path.name)
                except Exception as exc:
                    logger.warning("Cached token.json was invalid or expired (%s). Re-authenticating...", exc)
                    creds = None

            if not creds or not creds.valid:
                try:
                    # pyrefly: ignore[missing-import]
                    from google_auth_oauthlib.flow import InstalledAppFlow
                    flow = InstalledAppFlow.from_client_secrets_file(str(cred_path), SCOPES)
                    creds = flow.run_local_server(port=0)
                    with open(token_path, "w", encoding="utf-8") as token_file:
                        token_file.write(creds.to_json())
                    logger.info("Successfully completed OAuth consent flow; saved token to %s", token_path)
                except Exception as exc:
                    logger.error("Failed OAuth client authorization with %s: %s", cred_path, exc)
                    raise RuntimeError(f"OAuth authorization failed: {exc}") from exc
        else:
            raise ValueError(
                f"Unrecognized credentials format in {cred_path.name}. "
                "Expected a Service Account key, an OAuth token, or an OAuth client secret JSON."
            )

        self._service = build("drive", "v3", credentials=creds, cache_discovery=False)
        return self._service

    @property
    def service(self) -> Any:
        """Lazily returns the authenticated Google Drive service."""
        if self._service is None:
            self.authenticate()
        return self._service

    def _evict_folder_cache(self, folder_id: str) -> None:
        """Removes any cached (parent, name) mappings pointing to folder_id."""
        stale_keys = [k for k, v in self._folder_cache.items() if v == folder_id]
        for key in stale_keys:
            del self._folder_cache[key]

    def _list_files(
        self,
        query: str,
        fields: str = "nextPageToken, files(id, name)",
        page_size: int = 100,
    ) -> List[Dict[str, Any]]:
        """Lists all Drive items matching a query across paginated responses."""
        fields_expr = fields if "nextPageToken" in fields else f"nextPageToken, {fields}"
        results: List[Dict[str, Any]] = []
        page_token: Optional[str] = None

        while True:
            list_kwargs: Dict[str, Any] = {
                "q": query,
                "spaces": "drive",
                "fields": fields_expr,
                "pageSize": page_size,
                "supportsAllDrives": True,
                "includeItemsFromAllDrives": True,
            }
            if page_token:
                list_kwargs["pageToken"] = page_token

            response = self.service.files().list(**list_kwargs).execute()
            results.extend(response.get("files", []))
            page_token = response.get("nextPageToken")
            if not page_token:
                break

        return results

    def get_or_create_folder(self, folder_name: str, parent_id: Optional[str] = None) -> str:
        """
        Finds a subfolder by name within parent_id (or root_folder_id).
        If the folder does not exist, creates it.
        Uses in-memory cache to avoid redundant API queries.
        """
        parent = parent_id or self.root_folder_id
        cache_key = (parent, folder_name)
        if cache_key in self._folder_cache:
            return self._folder_cache[cache_key]

        # Query existing folder
        safe_name = folder_name.replace("'", "\\'")
        query = (
            f"'{parent}' in parents and "
            f"name = '{safe_name}' and "
            "mimeType = 'application/vnd.google-apps.folder' and "
            "trashed = false"
        )

        response = self.service.files().list(
            q=query,
            spaces="drive",
            fields="files(id, name)",
            pageSize=10,
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
        ).execute()

        files = response.get("files", [])
        if files:
            folder_id = files[0]["id"]
            logger.debug("Found existing folder '%s' (ID: %s) under parent %s", folder_name, folder_id, parent)
            self._folder_cache[cache_key] = folder_id
            return folder_id

        # Folder does not exist, create it
        metadata = {
            "name": folder_name,
            "mimeType": "application/vnd.google-apps.folder",
            "parents": [parent],
        }
        created = self.service.files().create(
            body=metadata,
            fields="id",
            supportsAllDrives=True,
        ).execute()
        folder_id = created.get("id")
        logger.info("Created new folder '%s' (ID: %s) under parent %s", folder_name, folder_id, parent)
        self._folder_cache[cache_key] = folder_id
        return folder_id

    def delete_file(self, file_id: str, name: str = "") -> bool:
        """
        Deletes a file or folder by Drive ID, falling back to Trash if permanent delete
        is declined (HTTP 400/403, e.g. Shared Drive permissions). Returns False on 404.
        """
        label = name or file_id
        try:
            self.service.files().delete(
                fileId=file_id,
                supportsAllDrives=True,
            ).execute()
            self._evict_folder_cache(file_id)
            logger.info("Deleted existing item '%s' (ID: %s) from Drive.", label, file_id)
            return True
        except Exception as exc:
            status = getattr(getattr(exc, "resp", None), "status", None)
            if status == 404:
                self._evict_folder_cache(file_id)
                logger.debug("Drive item '%s' (ID: %s) already missing (404).", label, file_id)
                return False
            if status in (403, 400):
                self.service.files().update(
                    fileId=file_id,
                    body={"trashed": True},
                    supportsAllDrives=True,
                ).execute()
                self._evict_folder_cache(file_id)
                logger.warning(
                    "Permanent delete declined (HTTP %s) for '%s' (ID: %s); moved to Trash instead.",
                    status, label, file_id,
                )
                return True
            raise

    def clear_folder(self, folder_id: str) -> int:
        """Deletes all non-trashed items inside folder_id and returns the number of items deleted."""
        query = f"'{folder_id}' in parents and trashed = false"
        items = self._list_files(
            query=query,
            fields="nextPageToken, files(id, name, mimeType)",
            page_size=100,
        )
        deleted = 0
        for item in items:
            item_id = item.get("id")
            if not item_id:
                continue
            if self.delete_file(item_id, item.get("name", "")):
                deleted += 1
        if deleted > 0:
            logger.info("Cleared %d existing item(s) from Drive folder %s.", deleted, folder_id)
        return deleted

    def delete_duplicate_folders(self, folder_name: str, parent_id: str, keep_folder_id: str) -> int:
        """Deletes any extra non-trashed folders named folder_name under parent_id except keep_folder_id."""
        safe_name = folder_name.replace("'", "\\'")
        query = (
            f"'{parent_id}' in parents and "
            f"name = '{safe_name}' and "
            "mimeType = 'application/vnd.google-apps.folder' and "
            "trashed = false"
        )
        folders = self._list_files(
            query=query,
            fields="nextPageToken, files(id, name)",
            page_size=100,
        )
        deleted = 0
        for folder in folders:
            fid = folder.get("id")
            if not fid or fid == keep_folder_id:
                continue
            if self.delete_file(fid, folder.get("name", folder_name)):
                deleted += 1
        if deleted > 0:
            logger.info(
                "Deleted %d duplicate folder(s) named '%s' under parent %s.",
                deleted, folder_name, parent_id,
            )
        return deleted

    def list_named_files(self, parent_folder_id: str, remote_filename: str) -> list[dict]:
        safe_name = remote_filename.replace("'", "\\'")
        query = (
            f"'{parent_folder_id}' in parents and "
            f"name = '{safe_name}' and "
            "trashed = false"
        )
        return self._list_files(
            query=query,
            fields="nextPageToken, files(id, name)",
            page_size=100,
        )

    def upload_or_update_file(
        self,
        local_path: str | Path,
        remote_filename: str,
        parent_folder_id: str,
        mime_type: Optional[str] = None,
        progress_callback: Optional[Callable[[float], None]] = None,
        *,
        replace_existing: bool = True,
    ) -> Dict[str, str]:
        """
        Uploads the new file and optionally deletes previous files with the same name.
        Uses resumable chunked upload so Drive generates a fresh file ID and preview.

        Returns dict with:
            id: Google Drive file ID
            name: remote file name
            web_view_link: view URL
        """
        # pyrefly: ignore[missing-import]
        from googleapiclient.http import MediaFileUpload

        path = Path(local_path).resolve()
        if not path.exists():
            raise FileNotFoundError(f"Local file does not exist: {path}")

        if not mime_type:
            mime_type, _ = mimetypes.guess_type(str(path))
            if not mime_type:
                mime_type = "video/mp4" if path.suffix.lower() == ".mp4" else "image/png"

        existing_files = (
            self.list_named_files(parent_folder_id, remote_filename) if replace_existing else []
        )

        media = MediaFileUpload(
            str(path),
            mimetype=mime_type,
            resumable=True,
            chunksize=5 * 1024 * 1024,  # 5MB chunks
        )

        logger.info("Uploading new file '%s' to folder %s on Drive...", remote_filename, parent_folder_id)
        metadata = {
            "name": remote_filename,
            "parents": [parent_folder_id],
        }
        request = self.service.files().create(
            body=metadata,
            media_body=media,
            fields="id, name, webViewLink",
            supportsAllDrives=True,
        )

        res = None
        while res is None:
            status, res = request.next_chunk()
            if status:
                progress = float(status.progress())
                if progress_callback:
                    progress_callback(progress)
                logger.debug("[%s] Upload progress: %0.1f%%", remote_filename, progress * 100.0)

        file_id = res.get("id")
        if not file_id:
            raise RuntimeError(f"Drive did not confirm upload of {remote_filename}")
        for existing in existing_files:
            if existing.get("id") and existing["id"] != file_id:
                self.delete_file(existing["id"], existing.get("name", remote_filename))
        web_link = res.get("webViewLink", f"https://drive.google.com/file/d/{file_id}/view")
        logger.info("Successfully uploaded '%s' (ID: %s)", remote_filename, file_id)

        return {
            "id": file_id,
            "name": remote_filename,
            "web_view_link": web_link,
        }
