from __future__ import annotations

import json
import re
import time
from typing import Any

import google.generativeai as genai

from app.config import settings
from app.schemas import GeminiPersonSummary, GeminiSummaryBundle, ParsedQueryIntent


genai.configure(api_key=settings.gemini_api_key)


class GeminiService:
    def __init__(self) -> None:
        self.llm_model_candidates = [
            settings.gemini_llm_model,
            "models/gemini-2.5-flash",
            "models/gemini-2.0-flash",
            "models/gemini-flash-latest",
        ]
        self.vlm_model_candidates = [
            settings.gemini_vlm_model,
            "models/gemini-2.5-flash",
            "models/gemini-2.0-flash",
            "models/gemini-2.5-flash-image",
        ]

    def _extract_json(self, text: str) -> dict[str, Any]:
        match = re.search(r"\{[\s\S]*\}", text)
        if not match:
            return {}
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return {}

    @staticmethod
    def _is_rate_limit_error(exc: Exception) -> bool:
        text = str(exc).lower()
        return "429" in text or "resource exhausted" in text

    def _run_with_retry(self, fn, max_attempts: int = 3):
        last_error: Exception | None = None
        for attempt in range(max_attempts):
            try:
                return fn()
            except Exception as exc:
                last_error = exc
                if not self._is_rate_limit_error(exc) or attempt == max_attempts - 1:
                    raise
                time.sleep(2**attempt)
        raise last_error if last_error else ValueError("Gemini call failed")

    def _generate_content_with_fallback(self, contents: list[Any], model_candidates: list[str]):
        seen: set[str] = set()
        last_error: Exception | None = None
        for model_name in model_candidates:
            if model_name in seen:
                continue
            seen.add(model_name)
            try:
                model = genai.GenerativeModel(model_name)
                return self._run_with_retry(lambda: model.generate_content(contents))
            except Exception as exc:
                last_error = exc
                continue

        if last_error:
            raise ValueError(f"generateContent failed for models {list(seen)}: {last_error}") from last_error
        raise ValueError("generateContent failed: no model candidates available")

    def parse_query_intent(self, prompt: str) -> ParsedQueryIntent:
        system_prompt = (
            "Return strict JSON with keys: person_name (string|null), "
            "requires_person_filter (boolean), confidence (0..1). "
            "Only set requires_person_filter=true if a specific person is requested."
        )
        try:
            response = self._generate_content_with_fallback([system_prompt, prompt], self.llm_model_candidates)
        except Exception:
            # Fail open: no person filter is safer than breaking all searches.
            return ParsedQueryIntent()
        parsed = self._extract_json(response.text or "")
        try:
            return ParsedQueryIntent(**parsed)
        except Exception:
            return ParsedQueryIntent()

    def summarize_annotated_image(self, annotated_image_bytes: bytes, person_names: list[str]) -> GeminiSummaryBundle:
        prompt = (
            "You are indexing a personal photo for semantic search. "
            "Return strict JSON with keys overall_summary and person_summaries. "
            "person_summaries must be a list of objects with person_name and summary. "
            "Describe visible clothing/actions/scene facts without guessing identity. "
            f"Known labels in the image: {person_names}."
        )
        image_part = {"mime_type": "image/jpeg", "data": annotated_image_bytes}
        response = self._generate_content_with_fallback([prompt, image_part], self.vlm_model_candidates)
        parsed = self._extract_json(response.text or "")

        overall_summary = str(parsed.get("overall_summary", ""))
        person_items = parsed.get("person_summaries", [])
        person_summaries: list[GeminiPersonSummary] = []
        if isinstance(person_items, list):
            for item in person_items:
                if isinstance(item, dict):
                    person_summaries.append(
                        GeminiPersonSummary(
                            person_name=item.get("person_name"),
                            summary=str(item.get("summary", "")),
                        )
                    )

        if not overall_summary:
            overall_summary = "Photo with people and scene context."

        return GeminiSummaryBundle(overall_summary=overall_summary, person_summaries=person_summaries)

    def embed_text(self, text: str) -> list[float]:
        model_candidates = [
            settings.gemini_embed_model,
            "models/gemini-embedding-001",
            "models/gemini-embedding-2-preview",
            "models/embedding-001",
            "models/text-embedding-004",
        ]

        seen: set[str] = set()
        last_error: Exception | None = None
        for model_name in model_candidates:
            if model_name in seen:
                continue
            seen.add(model_name)
            try:
                result = self._run_with_retry(lambda: genai.embed_content(model=model_name, content=text))
                values = result.get("embedding", [])
                if values:
                    return [float(x) for x in values]
            except Exception as exc:
                last_error = exc

        if last_error:
            raise ValueError(f"Embedding failed for models {list(seen)}: {last_error}") from last_error
        raise ValueError("Embedding failed: provider returned empty embedding")


gemini_service = GeminiService()
