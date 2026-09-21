import os
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

    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60

    langchain_api_key: str
    langchain_tracing_v2: bool = False
    langchain_project: str = "CustomerCare_Agent"

    langsmith_tracing: bool = False
    langsmith_api_key: str | None = None
    langsmith_project: str = "customer-care-agent"
    langsmith_endpoint: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


def configure_langsmith(settings: Settings) -> None:
    """
    Configure LangChain/LangSmith tracing from application settings.

    LangSmith is optional. If tracing is disabled or not usable
    LangSmith API key is configured, this function does nothing.

    Observability must never prevent the application from starting.
    """

    if not settings.langsmith_tracing:
        return

    if not settings.langsmith_api_key:
        return

    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = settings.langsmith_api_key
    os.environ["LANGCHAIN_PROJECT"] = settings.langsmith_project

    if settings.langsmith_endpoint:
        os.environ["LANGCHAIN_ENDPOINT"] = settings.langsmith_endpoint

