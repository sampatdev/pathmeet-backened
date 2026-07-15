from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://apple@localhost:5432/pathmeet"
    secret_key: str = "13234fsdfsfasfasrq234sdgzsdnhwieuyuwehbduweyuzncsike"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24  # 1 day
    redis_url: str = "redis://localhost:6379/0"
    kafka_bootstrap_servers: str = "localhost:9092"
    anthropic_api_key: str = ''

    class Config:
        env_file = ".env"

settings = Settings()