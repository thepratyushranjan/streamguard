import sys
import logging
from connection import ClickHouseConnection

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def clean_database():
    try:
        if not ClickHouseConnection.test_connection():
            logger.error("Could not connect to ClickHouse.")
            return

        client = ClickHouseConnection.get_client()
        logger.info("Attempting to drop corrupted 'camera_events'...")
        
        # 1. Drop as VIEW first (fixes the Code: 60 error)
        try:
            client.command("DROP VIEW IF EXISTS camera_events")
            logger.info("✓ Executed DROP VIEW")
        except Exception as e:
            logger.warning(f"DROP VIEW warning: {e}")

        # 2. Drop as TABLE (to be safe)
        try:
            client.command("DROP TABLE IF EXISTS camera_events")
            logger.info("✓ Executed DROP TABLE")
        except Exception as e:
            logger.warning(f"DROP TABLE warning: {e}")

        logger.info("Cleanup complete. Now run 'python setup_db.py'")

    except Exception as e:
        logger.error(f"Critical Error: {e}")

if __name__ == "__main__":
    clean_database()