from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    DATABASE_URL: str
    REDIS_URL: str = "redis://redis:6379/1"
    JWT_SECRET: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    RABBITMQ_URL: str = "amqp://admin:localdev@rabbitmq:5672/"
    SERVICE_NAME: str = "auth-service"
    SERVICE_PORT: int = 8001

    class Config:
        env_file = ".env"

@lru_cache()
def get_settings(): return Settings()
