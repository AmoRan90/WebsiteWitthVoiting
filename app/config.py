from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    SECRET_KEY: str = "change-me-in-production"
    DATABASE_URL: str = "postgresql+asyncpg://voting:voting@db:5432/voting"

    class Config:
        env_file = ".env"


settings = Settings()