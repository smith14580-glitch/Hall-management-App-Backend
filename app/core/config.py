from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@localhost:5432/marque_one"
    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_REFRESH_SECRET_KEY: str = "change-me-refresh-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    CORS_ORIGINS: str = "http://localhost:3000"
    ENVIRONMENT: str = "development"
    ENABLE_DOCS: bool = True
    FIRST_ADMIN_NAME: str = "Dev Admin"
    FIRST_ADMIN_PHONE: str = "03000000000"
    FIRST_ADMIN_PASSWORD: str = "Admin1234"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


settings = Settings()

# Neon (and other hosts) give plain postgres:// or postgresql:// URLs;
# SQLAlchemy needs the psycopg driver explicitly. Normalize here so any
# of the three spellings works when pasted into hosting env vars.
if settings.DATABASE_URL.startswith("postgresql://"):
    settings.DATABASE_URL = settings.DATABASE_URL.replace(
        "postgresql://", "postgresql+psycopg://", 1
    )
elif settings.DATABASE_URL.startswith("postgres://"):
    settings.DATABASE_URL = settings.DATABASE_URL.replace(
        "postgres://", "postgresql+psycopg://", 1
    )
