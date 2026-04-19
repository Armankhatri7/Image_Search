from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class SignUpRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    username: str
    password: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str


class UploadResponse(BaseModel):
    message: str
    item_id: str


class SearchRequest(BaseModel):
    prompt: str = Field(min_length=2, max_length=500)


class SearchResult(BaseModel):
    photo_id: str
    image_path: str
    image_url: str | None = None
    similarity: float
    matched_person: str | None = None
    summary_excerpt: str


class SearchResponse(BaseModel):
    prompt: str
    parsed_person_name: str | None = None
    results: list[SearchResult]


class IndexingStatus(BaseModel):
    photo_id: str
    status: str
    error_message: str | None = None
    updated_at: datetime | None = None


class ParsedQueryIntent(BaseModel):
    person_name: str | None = None
    requires_person_filter: bool = False
    confidence: float = 0.0


class GeminiPersonSummary(BaseModel):
    person_name: str | None
    summary: str


class GeminiSummaryBundle(BaseModel):
    overall_summary: str
    person_summaries: list[GeminiPersonSummary]


class Detection(BaseModel):
    bbox: tuple[int, int, int, int]
    person_name: str | None
    confidence: float


class SupabaseRow(BaseModel):
    data: dict[str, Any]
