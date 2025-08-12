from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any, Dict

from supabase import Client, create_client

from env import get_settings

_client: Client | None = None


def _get_client() -> Client:
    settings = get_settings()
    global _client
    if _client is None:
        _client = create_client(
            settings.NEXT_PUBLIC_SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY
        )
    return _client


def download_from_bucket(bucket: str, object_path: str) -> Path:
    """Download a file from Supabase storage and return the local path."""
    client = _get_client()
    data = client.storage.from_(bucket).download(object_path)
    tmp_dir = Path(tempfile.mkdtemp())
    file_path = tmp_dir / Path(object_path).name
    file_path.write_bytes(data)
    return file_path


def upload_json_to_bucket(bucket: str, object_path: str, payload: Dict[str, Any]) -> None:
    """Upload JSON data to Supabase storage."""
    client = _get_client()
    json_bytes = json.dumps(payload).encode("utf-8")
    client.storage.from_(bucket).upload(
        path=object_path,
        file=json_bytes,
        file_options={"content-type": "application/json"},
        upsert=True,
    )
