"""
ClickHouse Table Management CLI
Usage:
    python db/manage_tables.py create <table_name>   # Create specific table
    python db/manage_tables.py delete <table_name>   # Delete specific table
    python db/manage_tables.py list                  # List all available tables
    python db/manage_tables.py create --all          # Create all tables
    python db/manage_tables.py delete --all          # Delete all tables
"""

import sys
import argparse
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from db.connection import ClickHouseConnection
from db.video_analytics_logs_table import SCHEMAS as VIDEO_ANALYTICS_SCHEMAS
from db.sop_compliance_audits_table import SCHEMAS as SOP_COMPLIANCE_SCHEMAS
from db.system_health_table import SCHEMAS as SYSTEM_HEALTH_SCHEMAS
from config import get_settings
from utils.logger import get_logger

logger = get_logger(__name__)

# Combine all schemas
ALL_SCHEMAS = VIDEO_ANALYTICS_SCHEMAS + SOP_COMPLIANCE_SCHEMAS + SYSTEM_HEALTH_SCHEMAS

# Build schema registry (table_name -> schema_sql)
SCHEMA_REGISTRY = {name: schema for name, schema, _ in ALL_SCHEMAS}


def get_client():
    """Get ClickHouse client with connection test."""
    if not ClickHouseConnection.test_connection():
        logger.error("Could not connect to ClickHouse.")
        sys.exit(1)
    return ClickHouseConnection.get_client()


def list_tables():
    """List all available table schemas."""
    print("\n📋 Available Tables:")
    print("-" * 40)
    for name in SCHEMA_REGISTRY.keys():
        print(f"  • {name}")
    print("-" * 40)
    print(f"Total: {len(SCHEMA_REGISTRY)} tables\n")


def create_table(table_name: str) -> bool:
    """Create a single table."""
    if table_name not in SCHEMA_REGISTRY:
        logger.error(f"Unknown table: '{table_name}'")
        list_tables()
        return False
    
    client = get_client()
    schema = SCHEMA_REGISTRY[table_name]
    
    try:
        logger.info(f"Creating table: {table_name}...")
        client.command(schema)
        logger.info(f"✓ {table_name} created successfully")
        return True
    except Exception as e:
        if "already exists" in str(e).lower():
            logger.info(f"✓ {table_name} already exists")
            return True
        logger.error(f"✗ Failed to create {table_name}: {e}")
        return False


def delete_table(table_name: str) -> bool:
    """Delete a single table."""
    if table_name not in SCHEMA_REGISTRY:
        logger.error(f"Unknown table: '{table_name}'")
        list_tables()
        return False
    
    client = get_client()
    
    try:
        logger.info(f"Dropping table: {table_name}...")
        client.command(f"DROP TABLE IF EXISTS {table_name}")
        logger.info(f"✓ {table_name} dropped successfully")
        return True
    except Exception as e:
        logger.error(f"✗ Failed to drop {table_name}: {e}")
        return False


def create_all() -> bool:
    """Create all tables."""
    logger.info("Creating all tables...")
    success = True
    for table_name in SCHEMA_REGISTRY.keys():
        if not create_table(table_name):
            success = False
    return success


def delete_all() -> bool:
    """Delete all tables."""
    logger.info("Dropping all tables...")
    success = True
    for table_name in SCHEMA_REGISTRY.keys():
        if not delete_table(table_name):
            success = False
    return success


def main():
    parser = argparse.ArgumentParser(
        description="ClickHouse Table Management CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python db/manage_tables.py list
  python db/manage_tables.py create video_analytics_logs
  python db/manage_tables.py delete sop_compliance_audits
  python db/manage_tables.py create --all
  python db/manage_tables.py delete --all
        """
    )
    
    parser.add_argument(
        "action",
        choices=["create", "delete", "list"],
        help="Action to perform"
    )
    
    parser.add_argument(
        "table_name",
        nargs="?",
        help="Table name (use --all for all tables)"
    )
    
    parser.add_argument(
        "--all",
        action="store_true",
        help="Apply action to all tables"
    )
    
    args = parser.parse_args()
    
    # Handle list action
    if args.action == "list":
        list_tables()
        sys.exit(0)
    
    # Validate arguments
    if not args.table_name and not args.all:
        parser.error(f"'{args.action}' requires a table name or --all flag")
    
    if args.table_name and args.all:
        parser.error("Cannot specify both table_name and --all")
    
    # Execute action
    if args.action == "create":
        success = create_all() if args.all else create_table(args.table_name)
    elif args.action == "delete":
        success = delete_all() if args.all else delete_table(args.table_name)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
