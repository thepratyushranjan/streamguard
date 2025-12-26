from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Literal, Union, Dict, Any
from datetime import datetime
from dataclasses import dataclass

class HealthResponse(BaseModel):
    status: str
    clickhouse: str
    timestamp: datetime

# --- New Request Models ---

class Detection(BaseModel):
    class_id: int
    label: str
    confidence: float
    bbox: List[int] = Field(..., min_items=4, max_items=4) # [left, top, width, height]

class EventData(BaseModel):
    people_count: int = 0
    detections: List[Detection] = []
    triggers: List[str] = []
    capture_triggered: bool = False

class EventMeta(BaseModel):
    cam_id: int
    site: str
    status: Literal['SAFE', 'WARNING', 'CRITICAL']
    ts: float # Unix timestamp
    cam_name: Optional[str] = "Unknown"

    @field_validator('status', mode='before')
    def uppercase_status(cls, v):
        return v.upper() if isinstance(v, str) else v

class CameraEventRequest(BaseModel):
    type: Literal['METRIC', 'EVENT']
    processed_at: float
    meta: EventMeta
    # Support both 'data' (METRIC) and 'event' (EVENT) keys common in Vector logs
    data: Optional[EventData] = None
    event: Optional[EventData] = None

    @property
    def payload(self) -> EventData:
        """Helper to get the actual data payload regardless of event type"""
        return self.data or self.event or EventData()


@dataclass
class EventResult:
    """Encapsulates event processing result"""
    event_index: int
    status_code: int | None
    success: bool
    enriched_data: Dict[str, Any]
    error: str | None = None