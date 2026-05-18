"""Load Firebase credentials from env or a local key file (never commit the real key)."""

from __future__ import annotations

import base64
import json
import os
from pathlib import Path

from firebase_admin import credentials

_REPO_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_KEY_PATH = _REPO_ROOT / "system1" / "firebase-key.json"


def get_firebase_certificate():
    """Return a firebase_admin credentials.Certificate for Firestore."""
    b64 = os.getenv("FIREBASE_KEY_BASE64", "").strip()
    if b64:
        try:
            payload = json.loads(base64.b64decode(b64))
        except (json.JSONDecodeError, ValueError) as exc:
            raise RuntimeError("FIREBASE_KEY_BASE64 is set but invalid") from exc
        return credentials.Certificate(payload)

    path_str = os.getenv("FIREBASE_CREDENTIALS_PATH", "").strip()
    key_path = Path(path_str) if path_str else _DEFAULT_KEY_PATH
    if not key_path.is_absolute():
        key_path = _REPO_ROOT / key_path

    if key_path.is_file():
        return credentials.Certificate(str(key_path))

    raise RuntimeError(
        "Firebase credentials not found. Set FIREBASE_KEY_BASE64 in .env, or place "
        "your service account JSON at system1/firebase-key.json (see "
        "system1/firebase-key.json.example). See SETUP_GUIDE.md."
    )
