#!/usr/bin/env python3
"""
ClickHouse Schema Setup Script - Single Table Version
Pure schema management (No data insertion)
"""

import sys
import logging
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from db.connection import ClickHouseConnection
from db.table import SCHEMAS
from config import get_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

class SchemaManager:
    def __init__(self, client):
        self.client = client
        self.database = get_settings().clickhouse_database
    
    def create_table(self, table_name: str, schema: str) -> bool:
        try:
            logger.info(f"Creating table: {table_name}...")
            self.client.command(schema)
            logger.info(f"✓ {table_name} created successfully")
            return True
        except Exception as e:
            # Handle "already exists" gracefully
            if "already exists" in str(e).lower():
                logger.info(f"✓ {table_name} already exists")
                return True
            logger.error(f"✗ Failed to create {table_name}: {e}")
            return False
            
    def setup_schema(self) -> bool:
        """Iterate through SCHEMAS and create tables"""
        # Unpack tuple: (table_name, schema_sql, is_view_flag)
        for table_name, schema, _ in SCHEMAS:
            if not self.create_table(table_name, schema):
                return False
        return True

def main():
    try:
        # 1. Test Connection
        if not ClickHouseConnection.test_connection():
            logger.error("Could not connect to ClickHouse.")
            sys.exit(1)
            
        client = ClickHouseConnection.get_client()
        manager = SchemaManager(client)
        
        # 2. Setup Schema (Create Tables)
        if manager.setup_schema():
            logger.info("All schemas setup successfully.")
            sys.exit(0)
        else:
            logger.error("Schema setup failed.")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Critical Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()