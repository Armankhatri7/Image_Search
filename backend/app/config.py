from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    api_host: str = "0.0.0.0"
    api_port: int = 8000
    jwt_secret: str = "change-me"
    jwt_expire_minutes: int = 60

    supabase_url: str
    supabase_key: str
    supabase_bucket: str = "images"

    gemini_api_key: str
    gemini_llm_model: str = "models/gemini-2.5-flash"
    gemini_vlm_model: str = "models/gemini-2.5-flash"
    gemini_embed_model: str = "models/gemini-embedding-001"

    search_top_k: int = 25
    search_min_similarity: float = 0.72
    face_match_threshold: float = 0.47


settings = Settings()
