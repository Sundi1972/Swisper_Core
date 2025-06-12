import os
from typing import Optional
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = "gpt-4o"
    
    app_env: str = os.getenv("APP_ENV", "development")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    
    session_timeout_hours: int = int(os.getenv("SESSION_TIMEOUT_HOURS", "24"))
    max_messages_per_session: int = int(os.getenv("MAX_MESSAGES_PER_SESSION", "100"))
    
    max_search_results: int = 10
    ranking_threshold: float = 0.7
    
    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()
