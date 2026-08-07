from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    app_env: str = "development"
    app_name: str = "L.U.C.E.R.O Business Partner"
    # Include primary brand domain now so a future JS widget needs no CORS redesign
    cors_origins: str = (
        "https://lucero-iota.vercel.app,"
        "https://lucero-zeta.vercel.app,"
        "http://localhost:3000,"
        "https://www.anthonywarrenmckinzy.com,"
        "https://anthonywarrenmckinzy.com"
    )

    # Knowledge sites (seed crawler)
    primary_website: str = "https://www.anthonywarrenmckinzy.com"
    knowledge_website: str = "https://www.759inc.blue"
    log_level: str = "INFO"

    # Supabase
    supabase_url: str
    supabase_anon_key: str
    supabase_service_role_key: str
    supabase_jwt_secret: str

    # OpenRouter
    openrouter_api_key: str
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_default_model: str = "qwen/qwen3.7-plus"
    openrouter_fallback_model: str = "deepseek/deepseek-chat"
    openrouter_embedding_model: str = "openai/text-embedding-3-small"

    # RAG
    rag_chunk_size: int = 1000
    rag_chunk_overlap: int = 200
    rag_top_k: int = 8
    rag_similarity_threshold: float = 0.35

    # Agents (Phase 2 research)
    enable_web_research: bool = True
    serper_api_key: str = ""
    tavily_api_key: str = ""

    # Replicate media (Base44 OS)
    replicate_api_token: str = ""
    replicate_flux_model: str = "black-forest-labs/flux-schnell"
    replicate_sdxl_model: str = "stability-ai/sdxl"
    replicate_wan_model: str = "wan-video/wan-2.2-t2v-fast"
    replicate_cogvideox_model: str = "thomashayden/cogvideox-5b"
    replicate_kokoro_model: str = "jaaari/kokoro-82m"
    replicate_whisper_model: str = "openai/whisper"
    replicate_upscale_model: str = "nightmareai/real-esrgan"
    replicate_remove_bg_model: str = "cjwbw/rembg"
    generated_storage_bucket: str = "generated-assets"
    job_poll_seconds: int = 5

    # Channel bridge (ZeroClaw / WhatsApp OpenAI-compat)
    enable_channel_bridge: bool = False
    lucero_channel_api_key: str = ""
    channel_default_user_id: str = ""
    channel_default_agent: str = "support"
    # Comma-separated E.164 numbers. Empty = reply to all customers on the
    # linked business WhatsApp. When set, only these senders get replies.
    channel_allowed_numbers: str = ""
    channel_deny_message: str = (
        "This number is not authorized to message L.U.C.E.R.O. "
        "Ask the owner to allowlist your WhatsApp number."
    )

    @property
    def channel_allowed_number_list(self) -> List[str]:
        return [
            n.strip()
            for n in self.channel_allowed_numbers.split(",")
            if n.strip()
        ]

    # Resend email (free tier)
    resend_api_key: str = ""
    email_from: str = ""
    # Reminder poller (seconds). 0 disables background loop.
    reminder_poll_seconds: int = 60

    # Storage
    storage_bucket: str = "documents"

    @property
    def cors_origin_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_development(self) -> bool:
        return self.app_env.lower() in {"development", "dev", "local"}


@lru_cache
def get_settings() -> Settings:
    return Settings()


def clear_settings_cache() -> None:
    get_settings.cache_clear()
