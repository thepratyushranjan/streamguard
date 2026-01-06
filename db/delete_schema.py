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
        logger.info("Attempting to drop 'video_analytics_logs' table...")
        
        # Drop the video_analytics_logs table
        try:
            client.command("DROP TABLE IF EXISTS video_analytics_logs")
            logger.info("✓ Dropped video_analytics_logs table")
        except Exception as e:
            logger.warning(f"DROP TABLE warning: {e}")

        logger.info("Cleanup complete. Now run 'python setup_db.py'")

    except Exception as e:
        logger.error(f"Critical Error: {e}")

if __name__ == "__main__":
    clean_database()