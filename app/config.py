from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://racing:racing@localhost:5432/racing_line"

    model_config = {"env_file": ".env"}


settings = Settings()
