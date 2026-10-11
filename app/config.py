from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # Telegram Credentials
    bot_token: str = Field(default="", description="Telegram Bot API Token")
    bot_name: str = Field(default="Group Predictor Bot", description="Bot display name")
    bot_username: str = Field(
        default="Group_predictor_bot", description="Bot handle username"
    )
    master_owner_id: int = Field(
        default=8741198488, description="Primary Master Operator Telegram ID"
    )
    owner_id: int = Field(
        default=8741198488, description="Telegram numeric ID of the bot master"
    )
    log_chat_id: int = Field(
        default=8741198488, description="Telegram chat ID for global security logs"
    )
    support_username: str | None = Field(
        default="HxIndonesia", description="Official support handle"
    )
    maintenance_mode: bool = Field(
        default=False, description="Global maintenance mode flag"
    )
    master_recovery_token: str = Field(
        default="GP_MASTER_7788_RECOVERY_KEY",
        description="Secret recovery token for dead man's switch",
    )
    traitor_admin_threshold: int = Field(
        default=3, description="Max kicks/bans by a non-master admin in 60s"
    )

    # Database
    database_url: str = Field(
        default="sqlite+aiosqlite:///tg_guard_pro.db",
        description="Async database connection string",
    )

    # Redis Cache (Optional)
    redis_url: str | None = Field(default=None, description="Redis connection URL")

    # Environment & Monitoring
    environment: str = Field(
        default="production", description="development / staging / production"
    )
    log_level: str = Field(default="INFO", description="Logging severity level")
    timezone: str = Field(
        default="Asia/Kolkata", description="Application default timezone"
    )
    default_language: str = Field(
        default="hi", description="Default language code ('hi' or 'en')"
    )
    sentry_dsn: str | None = Field(
        default=None, description="Sentry DSN for error telemetry"
    )

    @field_validator("database_url", mode="before")
    @classmethod
    def assemble_db_connection(cls, v: str | None) -> str:
        if not v:
            return "sqlite+aiosqlite:///tg_guard_pro.db"
        # Render / Heroku / Cloud providers often supply postgres:// or postgresql://
        if v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql+asyncpg://", 1)
        if v.startswith("postgresql://") and not v.startswith("postgresql+"):
            return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()
