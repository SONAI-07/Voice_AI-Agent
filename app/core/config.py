from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "CustomerCare AI Agent"
    app_env: str = "development"
    debug: bool = True

    sarvam_api_key: str
    murf_api_key: str
    murf_voice_id: str

    twilio_account_sid: str
    twilio_auth_token: str
    twilio_phone_number: str

    smtp_host: str
    smtp_port: int = 587
    smtp_username: str
    smtp_password: str
    smtp_sender: str

    whatsapp_access_token: str
    whatsapp_phone_number_id: str
    whatsapp_api_version: str = "v23.0"
    whatsapp_brochure_template_name: str
    whatsapp_brochure_template_language: str = "en"

    database_url: str
    redis_url: str
    public_base_url: str

    langchain_api_key: str
    langchain_tracing_v2: bool = False
    langchain_project: str = "CustomerCare_Agent"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()