from fastapi import APIRouter, Depends
from clickhouse_connect.driver import Client
from typing import Dict, Any, List, Union

from utils.common import handle_route_exceptions, success_response
from services.vector_services import transformer, extract_enriched_data
from services.events_services import process_camera_events
from services.validation_service import validation_service
from services.ai_validation_services import ai_validation_service
from core.connection import get_clickhouse
from db.schemas import CameraEventRequest
from utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["Vector"])


@router.post("/vector")
@handle_route_exceptions("Failed to process vector pipeline")
async def trigger_vector_pipeline(
    events: Union[List[Dict[str, Any]], Dict[str, Any]]
):
    """Trigger Vector pipeline by receiving events directly in body."""
    # Normalize single event to list
    if isinstance(events, dict):
        events = [events]
        
    if not events:
        return success_response(message="No events to process", results=[])
    
    # Process all events
    results_dict = [
        {"event_index": i + 1, **extract_enriched_data(event)}
        for i, event in enumerate(events)
    ]
    logger.debug(f"payload_input: {results_dict}")
    
    transformed_data = transformer.transform({"results": results_dict})
    logger.debug(f"payload_transformed: {transformed_data}")

    # Schedule async validation tasks (fire-and-forget, non-blocking)
    event_type = transformed_data[0].get("type", "").lower() if transformed_data else ""
    
    if event_type == "event":
        validation_service.schedule_validation_tasks(transformed_data)
    elif event_type == "ai-info":
        # Only schedule AI validation tasks, skip database save
        ai_validation_service.schedule_ai_validation_tasks(transformed_data)
        return success_response(
            message="AI info validation scheduled",
            total_events=len(events)
        )
        
    # Convert to Pydantic models and insert into ClickHouse
    camera_events = [CameraEventRequest(**item) for item in transformed_data]
    db_response = process_camera_events(camera_events)
    
    return success_response(
        message="Vector pipeline processed",
        total_events=len(events),
        db_response=db_response
    )
