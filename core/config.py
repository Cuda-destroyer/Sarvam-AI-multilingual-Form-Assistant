"""
Application Configuration using Pydantic Settings.
Reads configuration from environment variables, .env file, or Streamlit secrets.
"""

from pathlib import Path
from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    """Central typed configuration for the Sarvam Multilingual Form Filler."""

    # Sarvam AI credentials & URLs
    sarvam_api_key: Optional[str] = Field(default=None, alias="SARVAM_API_KEY")
    sarvam_base_url: str = Field(default="https://api.sarvam.ai", alias="SARVAM_BASE_URL")

    # Models
    stt_model: str = Field(default="saaras:v3", alias="SARVAM_STT_MODEL")
    tts_model: str = Field(default="bulbul:v3", alias="SARVAM_TTS_MODEL")
    llm_model: str = Field(default="sarvam-30b", alias="SARVAM_LLM_MODEL")
    translate_model: str = Field(default="mayura:v1", alias="SARVAM_TRANSLATE_MODEL")

    # Application parameters
    app_env: str = Field(default="development", alias="APP_ENV")
    app_log_level: str = Field(default="INFO", alias="APP_LOG_LEVEL")
    max_file_size_mb: int = Field(default=10, alias="MAX_FILE_SIZE_MB")
    max_audio_duration_sec: int = Field(default=30, alias="MAX_AUDIO_DURATION_SEC")
    allowed_extensions: List[str] = Field(default=["pdf", "docx"], alias="ALLOWED_EXTENSIONS")

    # Default languages
    default_spoken_language: str = Field(default="hi-IN", alias="DEFAULT_SPOKEN_LANGUAGE")
    default_document_language: str = Field(default="en-IN", alias="DEFAULT_DOCUMENT_LANGUAGE")

    # Session storage
    storage_dir: Path = Field(default=Path("./storage"), alias="STORAGE_DIR")
    temp_dir: Path = Field(default=Path("./temp"), alias="TEMP_DIR")
    session_retention_minutes: int = Field(default=60, alias="SESSION_RETENTION_MINUTES")

    # Rate limiting & Cost budgets
    max_llm_calls_per_session: int = Field(default=50, alias="MAX_LLM_CALLS_PER_SESSION")
    max_audio_seconds_per_session: int = Field(default=300, alias="MAX_AUDIO_SECONDS_PER_SESSION")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def is_sarvam_configured(self) -> bool:
        """Check if a non-placeholder API key is configured."""
        if not self.sarvam_api_key:
            return False
        placeholder_values = ["your_sarvam_api_key_here", "placeholder", "none", ""]
        return self.sarvam_api_key.strip().lower() not in placeholder_values


# Singleton configuration instance
_config_instance: Optional[AppSettings] = None


def get_config() -> AppSettings:
    """Retrieve the application configuration, checking Streamlit secrets if running inside Streamlit."""
    global _config_instance
    if _config_instance is None:
        # Check Streamlit secrets first if available
        api_key_from_st = None
        try:
            import streamlit as st
            if hasattr(st, "secrets") and "SARVAM_API_KEY" in st.secrets:
                api_key_from_st = st.secrets["SARVAM_API_KEY"]
        except Exception:
            pass

        settings = AppSettings()
        if api_key_from_st and not settings.sarvam_api_key:
            settings.sarvam_api_key = api_key_from_st

        # Ensure runtime directories exist
        settings.storage_dir.mkdir(parents=True, exist_ok=True)
        settings.temp_dir.mkdir(parents=True, exist_ok=True)

        _config_instance = settings

    return _config_instance
