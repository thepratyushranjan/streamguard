from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional
import os

# BASE_DIR is the root of the project.
# config.py is in core/, so we need to go up one level.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

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
    validation_base_url: str

    
    @property
    def validation_url(self) -> str:
        return f"{self.validation_base_url.rstrip('/')}/api/v1/validation/validate"
    
    @property
    def ai_info_validation_url(self) -> str:
        return f"{self.validation_base_url.rstrip('/')}/api/v1/validation/ai-info-validate"
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"

@lru_cache()
def get_settings() -> Settings:
    return Settings()
