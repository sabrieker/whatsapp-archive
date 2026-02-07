from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5439/whatsapp_archive"

    # MinIO
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "whatsapp-archive"
    minio_secure: bool = False

    # App
    secret_key: str = "change-me-in-production"
    debug: bool = True
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    # Upload
    chunk_size: int = 5 * 1024 * 1024  # 5MB chunks
    max_upload_size: int = 10 * 1024 * 1024 * 1024  # 10GB max

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()
