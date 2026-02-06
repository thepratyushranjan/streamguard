from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List, Union

from utils.common import handle_route_exceptions, success_response
from services.vector_services import transformer, extract_enriched_data
from services.events_services import process_camera_events
from services.validation_service import validation_service
from services.ai_validation_services import ai_validation_service
from services.triage_service import update_triage
from core.connection import get_clickhouse
from db.schemas import CameraEventRequest, TriageUpdateRequest
from utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["Vector"])


@router.post("/vector")
@handle_route_exceptions("Failed to process vector pipeline")
async def trigger_vector_pipeline(
    events: Union[List[Dict[str, Any]], Dict[str, Any]]
):
    logger.info(f"events: {events}")
    """Trigger Vector pipeline by receiving events directly in body."""
    if isinstance(events, dict):
        events = [events]
        
    if not events:
        return success_response(message="No events to process", results=[])
    
    results_dict = [
        {"event_index": i + 1, **extract_enriched_data(event)}
        for i, event in enumerate(events)
    ]
    logger.debug(f"payload_input: {results_dict}")
    
    transformed_data = transformer.transform({"results": results_dict})
    logger.debug(f"payload_transformed: {transformed_data}")

    event_type = transformed_data[0].get("type", "").lower() if transformed_data else ""
    
    if event_type == "event":
        validation_service.queue_validation_tasks(transformed_data)
    elif event_type == "ai-info":
        ai_validation_service.queue_ai_validation_tasks(transformed_data)
        return success_response(message="AI info validation queued", total_events=len(events))
        
    camera_events = [CameraEventRequest(**item) for item in transformed_data]
    db_response = process_camera_events(camera_events)
    
    return success_response(
        message="Vector pipeline processed",
        total_events=len(events),
        db_response=db_response
    )


@router.patch("/vector/triage")
@handle_route_exceptions("Failed to update triage data")
async def patch_triage(event_timestamp: int, company_id: str, request: TriageUpdateRequest):
    """Update triage fields (triaged_by, triage_timestamp, ai_insights) for a record."""
    result = update_triage(
        event_timestamp=event_timestamp,
        company_id=company_id,
        triaged_by=request.triaged_by,
        triage_timestamp=request.triage_timestamp,
        ai_insights=request.ai_insights,
        triage_notes=request.triage_notes
    )
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("reason"))
    return success_response(message="Triage updated successfully")
