"""
System Health Service Module

Handles processing and database operations for system health data.
Follows production-level patterns with proper error handling and logging.
"""
from typing import List, Dict, Any, Union
from datetime import datetime
from fastapi import HTTPException
from clickhouse_connect.driver import Client
from db.schemas import SystemHealthPayloadRequest, SystemHealth
from utils.logger import get_logger

logger = get_logger(__name__)

# ClickHouse column names for system_health table
SYSTEM_HEALTH_COLUMNS = [
    'company_id', 'device_id', 'site_id', 'site_name',
    'event_timestamp',
    'latitude', 'longitude', 'reg_latitude', 'reg_longitude',
    'device_ip_local', 'device_ip_public',
    'country', 'state', 'district', 'city',
    'primary_internet_speed', 'secondary_internet_speed',
    'cpu_usage_percent', 'ram_usage_percent', 'device_status',
    'cameras.cam_id', 'cameras.cam_name', 'cameras.zone_names', 'cameras.status', 'cameras.fps'
]

# Status mapping for ClickHouse Enum
DEVICE_STATUS_MAP = {
    'online': 'online',
    'offline': 'offline', 
    'error': 'error'
}


def _parse_event_timestamp_to_unix(timestamp_value: Union[str, int]) -> int:
    """
    Parse event timestamp from various formats to Unix timestamp.
    
    Args:
        timestamp_value: Timestamp as int (Unix) or string (ISO)
        
    Returns:
        int: Unix timestamp
    """
    if isinstance(timestamp_value, int):
        return timestamp_value
        
    timestamp_str = str(timestamp_value)
    dt = None
    try:
        # Handle ISO format: "2026-01-08 13:51:29" or "2026-01-08T13:51:29"
        for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f"]:
            try:
                dt = datetime.strptime(timestamp_str, fmt)
                break
            except ValueError:
                continue
        
        # Fallback: try ISO format with timezone
        if not dt:
            dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            
        return int(dt.timestamp())
    except (ValueError, TypeError) as e:
        logger.warning(f"Failed to parse timestamp '{timestamp_str}': {e}, using current time")
        return int(datetime.now().timestamp())


def _normalize_status(status: str) -> str:
    """
    Normalize device/camera status string for ClickHouse Enum.
    
    Args:
        status: Status string from payload
        
    Returns:
        Normalized status string
    """
    normalized = status.lower().strip()
    return DEVICE_STATUS_MAP.get(normalized, 'error')


def _transform_payload_to_row(payload: SystemHealthPayloadRequest) -> List[Any]:
    """
    Transform a single payload request into a ClickHouse row.
    
    Args:
        payload: SystemHealthPayloadRequest instance
        
    Returns:
        List of values matching SYSTEM_HEALTH_COLUMNS order
    """
    meta = payload.meta
    details = payload.system_details
    cameras = details.cameras
    
    # Parse timestamp
    event_ts = _parse_event_timestamp_to_unix(meta.event_timestamp)
    
    # Transform camera arrays with status normalization
    camera_statuses = [_normalize_status(s) for s in cameras.status]
    
    return [
        str(meta.company_id),
        str(meta.device_id),
        meta.site_id or "",
        meta.site_name or "",
        event_ts,
        meta.latitude or 0.0,
        meta.longitude or 0.0,
        details.reg_latitude or 0.0,
        details.reg_longitude or 0.0,
        details.device_ip_local or "",
        details.device_ip_public or "",
        meta.country or "",
        meta.state or "",
        meta.district or "",
        meta.city or "",
        details.primary_internet_speed or 0.0,
        details.secondary_internet_speed or 0.0,
        details.cpu_usage_percent or 0.0,
        details.ram_usage_percent or 0.0,
        _normalize_status(details.device_status),
        cameras.cam_id or [],
        cameras.cam_name or [],
        cameras.zone_names or [],
        camera_statuses or [],
        cameras.fps or []
    ]


def process_system_health(
    payloads: List[SystemHealthPayloadRequest], 
    client: Client
) -> Dict[str, Any]:
    """
    Process system health payloads and insert into ClickHouse.
    
    Args:
        payloads: List of SystemHealthPayloadRequest instances
        client: ClickHouse client connection
        
    Returns:
        Dict with processing results
        
    Raises:
        HTTPException: On database insert failure
    """
    
    try:
        # Transform all payloads to rows
        rows = [_transform_payload_to_row(payload) for payload in payloads]
        
        # Batch insert into ClickHouse
        client.insert(
            'system_health',
            rows,
            column_names=SYSTEM_HEALTH_COLUMNS
        )
        
        return {
            "success": True,
            "inserted": len(rows)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Database insert failed: {str(e)}"
        )


def process_single_system_health(
    payload: SystemHealthPayloadRequest, 
    client: Client
) -> Dict[str, Any]:
    """
    Process a single system health payload and insert into ClickHouse.
    Convenience wrapper for single payload processing.
    
    Args:
        payload: SystemHealthPayloadRequest instance
        client: ClickHouse client connection
        
    Returns:
        Dict with processing results
    """
    return process_system_health([payload], client)
