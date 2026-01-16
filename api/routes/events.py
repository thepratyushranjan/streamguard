from fastapi import APIRouter
from services.events_services import get_recent_events

router = APIRouter(tags=["Events"])


@router.get("/last-events")
def get_last_events():
    """Get last processed events for debugging"""
    return get_recent_events()
