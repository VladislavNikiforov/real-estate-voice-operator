"""gdrive/uploader.py — Upload files to Google Drive, return shareable link.

Falls back to saving locally if credentials are not configured.
"""

import os
import uuid
from pathlib import Path

from server.config import GDRIVE_CREDENTIALS_PATH, GDRIVE_FOLDER_ID, GDRIVE_CONFIGURED

_LOCAL_DIR = Path("generated_files")


async def upload_to_drive(
    file_bytes: bytes,
    filename: str,
    mime_type: str = "application/pdf",
) -> str:
    """Upload a file to Google Drive and return a shareable link.

    If GDRIVE_CREDENTIALS_PATH / GDRIVE_FOLDER_ID are not set (or upload fails),
    saves locally and returns a file:// path.

    Returns:
        "https://drive.google.com/file/d/xxx/view?usp=sharing"  (real upload)
        "file://generated_files/{filename}"                      (local fallback)
    """
    if GDRIVE_CONFIGURED:
        try:
            return await _drive_upload(file_bytes, filename, mime_type)
        except Exception as exc:
            print(f"[GDrive] Upload failed ({exc}), falling back to local save")

    return _save_locally(file_bytes, filename)


# ── Real Drive upload ─────────────────────────────────────────

async def _drive_upload(file_bytes: bytes, filename: str, mime_type: str) -> str:
    """Authenticate with service account and upload to Drive folder."""
    import io
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaIoBaseUpload
    from google.oauth2.service_account import Credentials

    creds = Credentials.from_service_account_file(
        GDRIVE_CREDENTIALS_PATH,
        scopes=["https://www.googleapis.com/auth/drive"],
    )
    service = build("drive", "v3", credentials=creds, cache_discovery=False)

    # Upload
    meta = {"name": filename, "parents": [GDRIVE_FOLDER_ID]}
    media = MediaIoBaseUpload(io.BytesIO(file_bytes), mimetype=mime_type, resumable=False)
    file_ = service.files().create(body=meta, media_body=media, fields="id").execute()
    file_id = file_["id"]

    # Make publicly readable
    service.permissions().create(
        fileId=file_id,
        body={"type": "anyone", "role": "reader"},
    ).execute()

    link = f"https://drive.google.com/file/d/{file_id}/view?usp=sharing"
    print(f"[GDrive] Uploaded '{filename}' → {link}")
    return link


# ── Local fallback ────────────────────────────────────────────

def _save_locally(file_bytes: bytes, filename: str) -> str:
    _LOCAL_DIR.mkdir(exist_ok=True)
    dest = _LOCAL_DIR / filename
    dest.write_bytes(file_bytes)
    size_kb = len(file_bytes) / 1024
    print(f"[GDrive mock] Saved '{filename}' locally ({size_kb:.1f} KB) → {dest}")
    return f"file://{dest.resolve()}"
