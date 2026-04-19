from __future__ import annotations

import uuid
from typing import Any

from supabase import Client, create_client

from app.config import settings


class SupabaseService:
    def __init__(self) -> None:
        self.client: Client = create_client(settings.supabase_url, settings.supabase_key)

    def insert(self, table: str, payload: dict[str, Any]) -> dict[str, Any]:
        response = self.client.table(table).insert(payload).execute()
        return response.data[0]

    def upsert(self, table: str, payload: dict[str, Any], on_conflict: str | None = None) -> list[dict[str, Any]]:
        response = self.client.table(table).upsert(payload, on_conflict=on_conflict).execute()
        return response.data

    def select(
        self,
        table: str,
        columns: str = "*",
        filters: dict[str, Any] | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        query = self.client.table(table).select(columns)
        if filters:
            for key, value in filters.items():
                query = query.eq(key, value)
        if limit:
            query = query.limit(limit)
        response = query.execute()
        return response.data

    def delete(self, table: str, filters: dict[str, Any]) -> list[dict[str, Any]]:
        query = self.client.table(table).delete()
        for key, value in filters.items():
            query = query.eq(key, value)
        response = query.execute()
        return response.data

    def upload_bytes(self, path: str, content: bytes, content_type: str = "image/jpeg") -> str:
        self.client.storage.from_(settings.supabase_bucket).upload(
            path,
            content,
            file_options={"content-type": content_type, "upsert": "true"},
        )
        return path

    def signed_url(self, path: str, expires_in: int = 3600) -> str:
        response = self.client.storage.from_(settings.supabase_bucket).create_signed_url(path, expires_in)
        return response.get("signedURL", "")

    def remove_file(self, path: str) -> None:
        self.client.storage.from_(settings.supabase_bucket).remove([path])

    @staticmethod
    def build_storage_path(user_id: str, folder: str, ext: str = ".jpg") -> str:
        return f"{user_id}/{folder}/{uuid.uuid4().hex}{ext}"


supabase_service = SupabaseService()
