from __future__ import annotations

from app.services.supabase_client import supabase_service


class DeletionService:
    @staticmethod
    def _safe_remove_storage(path: str | None) -> None:
        if not path:
            return
        try:
            supabase_service.remove_file(path)
        except Exception:
            # Storage cleanup should not block DB cleanup.
            pass

    def delete_known_face(self, user_id: str, known_face_id: str) -> bool:
        rows = supabase_service.select("known_faces", filters={"id": known_face_id, "user_id": user_id}, limit=1)
        if not rows:
            return False

        row = rows[0]
        self._safe_remove_storage(row.get("image_path"))
        supabase_service.delete("known_faces", {"id": known_face_id, "user_id": user_id})
        return True

    def delete_photo(self, user_id: str, photo_id: str) -> bool:
        rows = supabase_service.select("photos", filters={"id": photo_id, "user_id": user_id}, limit=1)
        if not rows:
            return False

        row = rows[0]
        self._safe_remove_storage(row.get("original_path"))
        self._safe_remove_storage(row.get("annotated_path"))

        # Cascades remove detected_faces and summaries through FK(photo_id) on delete cascade.
        supabase_service.delete("photos", {"id": photo_id, "user_id": user_id})
        return True


deletion_service = DeletionService()
