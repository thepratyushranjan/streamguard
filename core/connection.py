import clickhouse_connect
from clickhouse_connect.driver import Client
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from core.config import get_settings
from typing import Optional
from utils.logger import get_logger

logger = get_logger(__name__)


class ClickHouseConnection:
    _instance: Optional[Client] = None
    
    @classmethod
    def get_client(cls) -> Client:
        """Get or create ClickHouse client (singleton pattern)"""
        if cls._instance is None:
            settings = get_settings()
            cls._instance = clickhouse_connect.get_client(
                host=settings.clickhouse_host,
                port=settings.clickhouse_port,
                username=settings.clickhouse_user,
                password=settings.clickhouse_password,
                database=settings.clickhouse_database
            )
            logger.debug(f"ClickHouse client created for {settings.clickhouse_host}:{settings.clickhouse_port}")
        return cls._instance
    
    @classmethod
    def close(cls):
        """Close ClickHouse connection"""
        if cls._instance:
            cls._instance.close()
            cls._instance = None
            logger.debug("ClickHouse connection closed")
    
    @classmethod
    def test_connection(cls) -> bool:
        """Test if connection is working"""
        try:
            client = cls.get_client()
            result = client.query("SELECT 1")
            return result.first_row[0] == 1
        except Exception as e:
            logger.error(f"ClickHouse connection test failed: {e}")
            return False


def get_clickhouse() -> Client:
    """Dependency for FastAPI"""
    return ClickHouseConnection.get_client()