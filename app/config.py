"""Application settings, read from environment variables."""
import os


class Settings:
    def __init__(self) -> None:
        self.database_url = os.getenv("DATABASE_URL", "sqlite:///./hub.db")
        self.source_base_url = os.getenv("SOURCE_BASE_URL", "https://dummyjson.com")
        self.api_key = os.getenv("API_KEY", "change-me")
        self.page_size = int(os.getenv("PAGE_SIZE", "100"))


settings = Settings()
