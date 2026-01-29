from fastapi import APIRouter, Depends
from clickhouse_connect.driver import Client
from typing import Union, List

from utils.common import handle_route_exceptions, success_response
from services.system_health_services import process_single_system_health
from core.connection import get_clickhouse
from db.schemas import SystemHealthPayloadRequest

router = APIRouter(tags=["System Health"])


@router.post("/system-health")
@handle_route_exceptions("Failed to save system health data")
async def save_system_health(
    payload: Union[SystemHealthPayloadRequest, List[SystemHealthPayloadRequest]],
):
    """
    Receives device health metrics including:
    - Device metadata (company, site, camera info)
    - System performance (CPU, RAM, network speeds)
    - Camera statuses (online/offline/error, FPS)
    
    Accepts both single object and array of objects.
    When array is received, processes all items.
    """

    # Normalize payload to list
    items = payload if isinstance(payload, list) else [payload]
    
    total_inserted = 0
    for item in items:
        client: Client = get_clickhouse(item.meta.company_id)
        result = process_single_system_health(item, client)
        total_inserted += result.get("inserted", 0)
    
    return success_response(
        message="System health data saved successfully",
        inserted=total_inserted
    )
