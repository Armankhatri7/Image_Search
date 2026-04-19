from __future__ import annotations

from app.config import settings
from app.services.face_service import FaceMatch, face_service
from app.services.gemini_service import gemini_service
from app.services.supabase_client import supabase_service


class IndexingService:
    @staticmethod
    def _safe_remove_storage(path: str | None) -> None:
        if not path:
            return
        try:
            supabase_service.remove_file(path)
        except Exception:
            pass

    @staticmethod
    def _safe_delete_photo(photo_id: str, user_id: str) -> None:
        try:
            supabase_service.delete("photos", {"id": photo_id, "user_id": user_id})
        except Exception:
            pass

    def upload_known_face(self, user_id: str, person_name: str, image_bytes: bytes) -> dict:
        locations, encodings = face_service.detect_and_encode(image_bytes)
        if len(encodings) != 1:
            raise ValueError("Known face image must contain exactly one face")

        image_path = supabase_service.build_storage_path(user_id, "known_faces")
        supabase_service.upload_bytes(image_path, image_bytes)

        row = supabase_service.insert(
            "known_faces",
            {
                "user_id": user_id,
                "person_name": person_name.lower().strip(),
                "image_path": image_path,
                "face_embedding": encodings[0],
            },
        )
        return row

    def _match_faces(self, user_id: str, locations: list[tuple[int, int, int, int]], encodings: list[list[float]]) -> list[FaceMatch]:
        known = supabase_service.select("known_faces", filters={"user_id": user_id})
        matches: list[FaceMatch] = []

        for bbox, embedding in zip(locations, encodings):
            best_name: str | None = None
            best_score = -1.0
            for ref in known:
                score = face_service.cosine_similarity(embedding, ref["face_embedding"])
                if score > best_score:
                    best_score = score
                    best_name = ref["person_name"]

            if best_score < settings.face_match_threshold:
                best_name = "unknown"

            matches.append(FaceMatch(bbox=bbox, embedding=embedding, person_name=best_name, confidence=best_score))

        return matches

    def upload_photo(self, user_id: str, image_bytes: bytes) -> dict:
        original_path = supabase_service.build_storage_path(user_id, "photos")
        supabase_service.upload_bytes(original_path, image_bytes)
        annotated_path: str | None = None

        photo = supabase_service.insert(
            "photos",
            {
                "user_id": user_id,
                "original_path": original_path,
                "status": "processing",
            },
        )

        try:
            locations, encodings = face_service.detect_and_encode(image_bytes)
            matches = self._match_faces(user_id, locations, encodings)

            for match in matches:
                supabase_service.insert(
                    "detected_faces",
                    {
                        "photo_id": photo["id"],
                        "user_id": user_id,
                        "person_name": match.person_name,
                        "bbox_top": match.bbox[0],
                        "bbox_right": match.bbox[1],
                        "bbox_bottom": match.bbox[2],
                        "bbox_left": match.bbox[3],
                        "face_embedding": match.embedding,
                        "confidence": match.confidence,
                    },
                )

            annotated_bytes = face_service.annotate_image(image_bytes, matches)
            annotated_path = supabase_service.build_storage_path(user_id, "annotated")
            supabase_service.upload_bytes(annotated_path, annotated_bytes)

            person_names = [m.person_name or "unknown" for m in matches]
            bundle = gemini_service.summarize_annotated_image(annotated_bytes, person_names)

            overall_embedding = gemini_service.embed_text(bundle.overall_summary)
            supabase_service.insert(
                "summaries",
                {
                    "photo_id": photo["id"],
                    "user_id": user_id,
                    "person_name": None,
                    "summary_type": "overall",
                    "summary_text": bundle.overall_summary,
                    "embedding": overall_embedding,
                },
            )

            for person_summary in bundle.person_summaries:
                if not person_summary.summary.strip():
                    continue
                person_embedding = gemini_service.embed_text(person_summary.summary)
                supabase_service.insert(
                    "summaries",
                    {
                        "photo_id": photo["id"],
                        "user_id": user_id,
                        "person_name": (person_summary.person_name or "unknown").lower().strip(),
                        "summary_type": "person",
                        "summary_text": person_summary.summary,
                        "embedding": person_embedding,
                    },
                )

            supabase_service.upsert(
                "photos",
                {
                    "id": photo["id"],
                    "user_id": user_id,
                    "original_path": original_path,
                    "annotated_path": annotated_path,
                    "status": "indexed",
                },
                on_conflict="id",
            )
        except Exception as exc:
            # Failed indexing entries are removed to prevent repeated failed rows in the UI.
            self._safe_remove_storage(annotated_path)
            self._safe_remove_storage(original_path)
            self._safe_delete_photo(photo["id"], user_id)
            if "429" in str(exc).lower() or "resource exhausted" in str(exc).lower():
                raise ValueError("Gemini quota reached (429). Please retry after a short wait.") from exc
            raise

        return photo


indexing_service = IndexingService()
