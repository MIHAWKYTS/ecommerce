from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg2://ecommerce:ecommerce@localhost:5432/ecommerce"
    redis_url: str = "redis://localhost:6379/0"
    cors_origins: str = "http://localhost:3000"
    admin_emails: str = ""

    model_config = {"env_prefix": ""}


settings = Settings()
