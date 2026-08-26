from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "CustomerCare AI Agent"
    app_env: str = "development"
    debug: bool = True

    openai_api_key: str

    twilio_account_sid: str
    twilio_auth_token: str
    twilio_phone_number: str

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