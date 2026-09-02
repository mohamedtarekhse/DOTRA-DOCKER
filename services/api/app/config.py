from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://acuseek:acuseek_secret@postgres:5432/acuseek"
    REDIS_URL: str = "redis://redis:6379/0"
    MQTT_BROKER: str = "mosquitto"
    MQTT_PORT: int = 1883
    MQTT_USERNAME: str = "acuseek"
    MQTT_PASSWORD: str = "acuseek_mqtt_secret"

    MINIO_ENDPOINT: str = "minio:9000"
    MINIO_ROOT_USER: str = "acuseek"
    MINIO_ROOT_PASSWORD: str = "acuseek_minio_secret"
    MINIO_PUBLIC_BASE: str = "http://192.168.10.50/minio"

    AI_ENGINE_URL: str = "http://ai-engine:8100"
    LPR_EVENT_SECRET: str = "lpr_secret"

    JWT_SECRET: str = "change_me"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440

    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "acuseek"

    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""
    TELEGRAM_WEBHOOK_SECRET: str = ""

    MEDIA_DIR: str = "/media"
    CORS_ORIGINS: str = "*"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    def model_post_init(self, __context) -> None:
        weak_secrets = {
            "change_me", "change_me_production", "change_me_to_a_long_random_string",
            "please_change_me", "secret",
        }
        if not self.JWT_SECRET or len(self.JWT_SECRET) < 32 or self.JWT_SECRET in weak_secrets:
            raise RuntimeError(
                "JWT_SECRET must be a strong random value (>= 32 chars). "
                "Set it in .env — refusing to boot with the default secret."
            )


settings = Settings()
