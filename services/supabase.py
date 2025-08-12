import os
import json
import tempfile
from pathlib import Path
from typing import Any, Dict, List

from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

class SupabaseService:
    """Unified Supabase service exposing table and storage utilities."""

    def __init__(self) -> None:
        url = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
        key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")
        self.client: Client = create_client(url, key)

    def table(self, name: str):
        """Return a handle to a Supabase table."""
        return self.client.table(name)

    def storage(self, bucket: str):
        """Return a handle to a Supabase storage bucket."""
        return self.client.storage.from_(bucket)

    # Convenience helpers -------------------------------------------------
    def download_from_bucket(self, bucket: str, object_path: str) -> Path:
        """Download a file from Supabase storage and return the local path."""
        data = self.storage(bucket).download(object_path)
        tmp_dir = Path(tempfile.mkdtemp())
        file_path = tmp_dir / Path(object_path).name
        file_path.write_bytes(data)
        return file_path

    def upload_json_to_bucket(self, bucket: str, object_path: str, payload: Dict[str, Any]) -> None:
        """Upload JSON data to Supabase storage."""
        json_bytes = json.dumps(payload).encode("utf-8")
        self.storage(bucket).upload(
            path=object_path,
            file=json_bytes,
            file_options={"content-type": "application/json"},
            upsert=True,
        )

    def upsert_face_embeddings(self, user_id: str, photo_key: str, faces: List[Dict[str, Any]]) -> None:
        """Insert face embeddings into the ``face_embeddings`` table."""
        rows = []
        for idx, face in enumerate(faces):
            rows.append(
                {
                    "user_id": user_id,
                    "photo_key": photo_key,
                    "face_index": idx,
                    "embedding": face.get("embedding_512"),
                    "det_score": face.get("det_score"),
                    "bbox": {"xyxy": face.get("bbox_xyxy")},
                }
            )
        if rows:
            self.table("face_embeddings").insert(rows).execute()


# Module-level singleton --------------------------------------------------
supabase = SupabaseService()
