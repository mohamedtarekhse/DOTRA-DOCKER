from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://acuseek:acuseek_secret@postgres:5432/acuseek"
    REDIS_URL: str = "redis://redis:6379/0"

    MINIO_ENDPOINT: str = "minio:9000"
    MINIO_ROOT_USER: str = "acuseek"
    MINIO_ROOT_PASSWORD: str = "acuseek_minio_secret"
    MINIO_PUBLIC_BASE: str = "http://192.168.10.50/media"

    AI_ENGINE_URL: str = "http://ai-engine:8100"
    LPR_EVENT_SECRET: str = "lpr_secret"

    JWT_SECRET: str = "change_me"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440

    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""

    MEDIA_DIR: str = "/media"
    CORS_ORIGINS: str = "*"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


settings = Settings()
