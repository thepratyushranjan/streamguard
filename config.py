from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class Settings(BaseSettings):
    clickhouse_host: str
    clickhouse_port: int
    clickhouse_user: str
    clickhouse_password: str
    clickhouse_database: str
    vector_url: str = "http://vector:8080"
    camera_logs_path: str = "camera_logs.json"
    google_application_credentials: Optional[str] = os.path.join(BASE_DIR, "vertex-ai-user.json")
    captures_dir: str = os.path.join(BASE_DIR, "captures")
    bucket_name: str
    event_prefix: str
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"

@lru_cache()
def get_settings() -> Settings:
    return Settings()