"""
Attendance Records Service Module

Handles processing and database operations for attendance event data.
Follows production-level patterns with proper error handling and logging.
"""
from typing import List, Dict, Any
from fastapi import HTTPException
from clickhouse_connect.driver import Client

from db.schemas import AttendanceRecord, AttendanceRequest, METADATA_FIELDS, ATTENDANCE_DATA_FIELDS
from utils.logger import get_logger
from utils.constant import ATTENDANCE_COLUMNS

logger = get_logger(__name__)


def _build_attendance_row(record: AttendanceRecord) -> List[Any]:
    """
    Build a ClickHouse row from an AttendanceRecord, matching ATTENDANCE_COLUMNS order.

    Args:
        record: Validated AttendanceRecord instance.

    Returns:
        List of values aligned with ATTENDANCE_COLUMNS.
    """
    return [
        # Metadata
        record.company_id,
        record.device_id,
        record.cam_id,
        record.cam_name,
        record.site_name,
        record.site_id,
        record.zone_names,
        # Geo-Location
        record.latitude,
        record.longitude,
        record.country,
        record.state,
        record.district,
        record.city,
        # Attendance Data
        record.event_type,
        record.person_name,
        record.person_id,
        record.zone,
        record.direction,
        record.confidence,
        record.track_id,
        record.description,
        record.recorded_at,
        record.total_work_hours,
        record.workstation_absence,
    ]


def process_attendance_record(
    record: AttendanceRecord,
    client: Client,
) -> Dict[str, Any]:
    """
    Insert a single attendance record into ClickHouse.

    Args:
        record: AttendanceRecord instance ready for storage.
        client: ClickHouse client connection.

    Returns:
        Dict with success status and insert count.

    Raises:
        HTTPException: On database insert failure.
    """
    return process_attendance_records([record], client)


def process_attendance_records(
    records: List[AttendanceRecord],
    client: Client,
) -> Dict[str, Any]:
    """
    Batch-insert attendance records into ClickHouse.

    Args:
        records: List of AttendanceRecord instances.
        client: ClickHouse client connection.

    Returns:
        Dict with success status and number of rows inserted.

    Raises:
        HTTPException: On database insert failure.
    """
    try:
        rows = [_build_attendance_row(r) for r in records]

        client.insert(
            'attendance_logs',
            rows,
            column_names=ATTENDANCE_COLUMNS,
        )

        logger.info(f"Inserted {len(rows)} attendance record(s)")
        return {"success": True, "inserted": len(rows)}

    except Exception as e:
        logger.error(f"Attendance record insert error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Database insert failed: {str(e)}",
        )
