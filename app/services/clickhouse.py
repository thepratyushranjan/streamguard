import clickhouse_connect
from clickhouse_connect.driver import Client
from typing import Optional
from app.core.config import get_settings

class ClickHouseConnection:
    _instance: Optional[Client] = None
    
    @classmethod
    def get_client(cls) -> Client:
        """Get or create ClickHouse client (singleton pattern)"""
        if cls._instance is None:
            settings = get_settings()
            try:
                cls._instance = clickhouse_connect.get_client(
                    host=settings.clickhouse_host,
                    port=settings.clickhouse_port,
                    username=settings.clickhouse_user,
                    password=settings.clickhouse_password,
                    database=settings.clickhouse_database
                )
            except Exception as e:
                print(f"Failed to connect to ClickHouse: {e}")
                raise e
        return cls._instance
    
    @classmethod
    def close(cls):
        """Close ClickHouse connection"""
        if cls._instance:
            try:
                cls._instance.close()
            except Exception:
                pass
            cls._instance = None
    
    @classmethod
    def test_connection(cls) -> bool:
        """Test if connection is working"""
        try:
            client = cls.get_client()
            result = client.query("SELECT 1")
            return result.first_row[0] == 1
        except Exception:
            return False

def get_clickhouse() -> Client:
    """Dependency for FastAPI"""
    return ClickHouseConnection.get_client()
