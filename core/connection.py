import clickhouse_connect
from clickhouse_connect.driver import Client
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from core.config import get_settings
from typing import Optional, Dict
from utils.logger import get_logger

logger = get_logger(__name__)


class ClickHouseConnection:
    _instances: Dict[Optional[str], Client] = {}
    
    @classmethod
    def get_client(cls, db_name=None) -> Client:
        """Get or create ClickHouse client (multiton pattern based on db_name)"""
        # If db_name is not provided, use the default from settings inside the creation logic
        # But we need a key for the dictionary. Let's use db_name (which might be None) as part of the key.
        # However, if db_name is None, it means "default database".
        
        if db_name not in cls._instances:
            settings = get_settings()
            # If db_name is explicitly passed, use it. Otherwise use settings.clickhouse_database (if it exists) or None?
            # Looking at original code: database=db_name.
            # If db_name is None, clickhouse_connect uses default.
            
            client = clickhouse_connect.get_client(
                host=settings.clickhouse_host,
                port=settings.clickhouse_port,
                username=settings.clickhouse_user,
                password=settings.clickhouse_password,
                database=db_name or settings.clickhouse_database
            )
            cls._instances[db_name] = client
            logger.debug(f"ClickHouse client created for {settings.clickhouse_host}:{settings.clickhouse_port} (db={db_name})")
        return cls._instances[db_name]
    
    @classmethod
    def close(cls):
        """Close all ClickHouse connections"""
        for db_name, client in cls._instances.items():
            try:
                client.close()
                logger.debug(f"ClickHouse connection closed (db={db_name})")
            except Exception as e:
                logger.error(f"Error closing connection for db={db_name}: {e}")
        cls._instances.clear()
    
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


def get_clickhouse(db_name =None) -> Client:
    """Dependency for FastAPI"""
    return ClickHouseConnection.get_client(db_name)