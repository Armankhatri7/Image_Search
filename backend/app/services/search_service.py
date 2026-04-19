from __future__ import annotations

from app.config import settings
from app.schemas import SearchResult, SearchResponse
from app.services.face_service import face_service
from app.services.gemini_service import gemini_service
from app.services.supabase_client import supabase_service


class SearchService:
    def search(self, user_id: str, prompt: str) -> SearchResponse:
        intent = gemini_service.parse_query_intent(prompt)
        query_embedding = gemini_service.embed_text(prompt)

        filters: dict[str, str] = {"user_id": user_id}
        parsed_person_name: str | None = None
        if intent.requires_person_filter and intent.person_name and intent.confidence >= 0.65:
            parsed_person_name = intent.person_name.lower().strip()
            filters["person_name"] = parsed_person_name

        summaries = supabase_service.select("summaries", filters=filters)

        scored: list[tuple[dict, float]] = []
        for row in summaries:
            similarity = face_service.cosine_similarity(query_embedding, row["embedding"])
            if similarity >= settings.search_min_similarity:
                scored.append((row, similarity))

        scored.sort(key=lambda item: item[1], reverse=True)
        scored = scored[: settings.search_top_k]

        best_by_photo: dict[str, tuple[dict, float]] = {}
        for row, score in scored:
            photo_id = row["photo_id"]
            previous = best_by_photo.get(photo_id)
            if not previous or score > previous[1]:
                best_by_photo[photo_id] = (row, score)

        photos = supabase_service.select("photos", filters={"user_id": user_id})
        photo_map = {p["id"]: p for p in photos}

        results: list[SearchResult] = []
        for photo_id, (row, score) in best_by_photo.items():
            photo = photo_map.get(photo_id)
            if not photo:
                continue
            image_path = photo.get("original_path") or photo.get("annotated_path")
            image_url = supabase_service.signed_url(image_path) if image_path else None
            results.append(
                SearchResult(
                    photo_id=photo_id,
                    image_path=image_path,
                    image_url=image_url,
                    similarity=score,
                    matched_person=row.get("person_name"),
                    summary_excerpt=(row.get("summary_text") or "")[:160],
                )
            )

        results.sort(key=lambda r: r.similarity, reverse=True)

        return SearchResponse(prompt=prompt, parsed_person_name=parsed_person_name, results=results)


search_service = SearchService()
