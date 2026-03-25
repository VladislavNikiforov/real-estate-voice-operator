"""mock/mock_gdrive.py — Fake Google Drive upload.

Saves locally and returns a realistic-looking fake Drive link.
This is automatically used by gdrive/uploader.py when credentials are absent.
Can also be imported directly in tests.
"""

import uuid
from pathlib import Path

_LOCAL = Path("generated_files")
_FAKE_BASE = "https://drive.google.com/file/d"


def fake_upload(file_bytes: bytes, filename: str) -> str:
    """Save file locally and return a fake Drive link."""
    _LOCAL.mkdir(exist_ok=True)
    dest = _LOCAL / filename
    dest.write_bytes(file_bytes)
    fake_id = uuid.uuid4().hex[:28]
    link = f"{_FAKE_BASE}/{fake_id}/view?usp=sharing"
    size_kb = len(file_bytes) / 1024
    print(f"[mock_gdrive] Saved '{filename}' ({size_kb:.1f} KB) → {dest}")
    print(f"[mock_gdrive] Fake Drive link: {link}")
    return link
