from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Taller SaaS API"
    app_env: str = "development"
    api_v1_prefix: str = "/api/v1"

    database_url: str = Field(min_length=1)
    database_ssl: bool = True
    database_ssl_verify: bool = False

    jwt_secret: str = Field(min_length=32)
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    cors_origins: str = "http://localhost:3000"

    supabase_url: str | None = None
    supabase_service_role_key: str | None = None
    supabase_storage_bucket: str = "taller-archivos"

    frontend_url: str = "http://localhost:3000"
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from_email: str | None = None
    smtp_from_name: str = "Gestión de taller"
    smtp_use_tls: bool = True
    smtp_use_ssl: bool = False
    brevo_api_key: str | None = None
    brevo_from_email: str | None = None
    brevo_from_name: str = "Gestión de taller"

    @field_validator("database_url")
    @classmethod
    def validate_async_driver(cls, value: str) -> str:
        if value.startswith("postgresql://"):
            return value.replace("postgresql://", "postgresql+asyncpg://", 1)
        if not value.startswith("postgresql+asyncpg://"):
            raise ValueError(
                "DATABASE_URL debe comenzar con postgresql:// o postgresql+asyncpg://"
            )
        return value

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def smtp_configured(self) -> bool:
        return bool(self.smtp_host and self.smtp_from_email)

    @property
    def brevo_configured(self) -> bool:
        return bool(self.brevo_api_key and self.brevo_from_email)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
