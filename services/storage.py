"""Helpers for interacting with Supabase storage."""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

from supabase import Client, create_client  # type: ignore


@dataclass
class StorageService:
    client: Client
    bucket_name: str = "skin-photos"

    @classmethod
    def from_env(cls) -> "StorageService":  # pragma: no cover - simple factory
        url = os.environ["SUPABASE_URL"]
        key = os.environ["SUPABASE_ANON_KEY"]
        client = create_client(url, key)
        return cls(client)

    @property
    def bucket(self):  # pragma: no cover - thin wrapper
        return self.client.storage.from_(self.bucket_name)

    def upload(self, path: str, data: bytes, content_type: str = "image/png") -> str:
        self.bucket.upload(path, data, {"content-type": content_type})
        return path
