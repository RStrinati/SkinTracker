from __future__ import annotations

from typing import Any, Dict, List

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


def upsert_face_embeddings(user_id: str, photo_key: str, faces: List[Dict[str, Any]]) -> None:
    """Insert face embeddings into the ``face_embeddings`` table."""
    client = _get_client()
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
        client.table("face_embeddings").insert(rows).execute()
