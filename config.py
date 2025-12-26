from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    clickhouse_host: str
    clickhouse_port: int
    clickhouse_user: str
    clickhouse_password: str
    clickhouse_database: str
    vector_url: str = "http://vector:8080"
    camera_logs_path: str = "camera_logs.json"
    
    class Config:
        env_file = ".env"
        case_sensitive = False

@lru_cache()
def get_settings() -> Settings:
    return Settings()