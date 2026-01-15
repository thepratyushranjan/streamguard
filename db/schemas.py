from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Literal, Union
from datetime import datetime, timezone

class HealthResponse(BaseModel):
    status: str
    clickhouse: str
    timestamp: datetime

# --- New Request Models ---

class Detection(BaseModel):
    class_id: int = 0
    label: str = ""
    confidence: float = 0.0
    bbox: List[int] = Field(default_factory=lambda: [0, 0, 0, 0], min_items=4, max_items=4)
    object_id: Optional[Union[int, str]] = 0
    recognition: Optional[dict] = Field(default_factory=dict)
    display_label: Optional[str] = ""

    @field_validator('object_id', mode='before')
    def parse_object_id(cls, v):
        if not v:
            return 0
        try:
            return int(v)
        except (ValueError, TypeError):
            return 0

class EventData(BaseModel):
    people_count: int = 0
    video_count: int = 0
    image_count: int = 0
    detections: List[Detection] = Field(default_factory=list)
    triggers: List[str] = Field(default_factory=list)
    capture_triggered: bool = False
    
    status: Optional[str] = "safe" 
    triaged_by: Optional[str] = ""
    triage_notes: Optional[str] = ""
    triage_timestamp: Optional[float] = 0.0
    ai_insights: Optional[str] = ""
    evidence_path: Optional[str] = ""

    @field_validator('status', mode='before')
    def lowercase_status(cls, v):
        return v.lower() if isinstance(v, str) and v else "safe"

class EventMeta(BaseModel):
    company_id: int  # Mandatory field (UInt32)
    device_id: int   # Mandatory field (UInt32)
    cam_id: Union[int, str] = 0
    site_name: str = ""
    ts: float = 0.0
    cam_name: Optional[str] = "Unknown"
    
    latitude: Optional[float] = 0.0
    longitude: Optional[float] = 0.0
    country: Optional[str] = ""
    state: Optional[str] = ""
    district: Optional[str] = ""
    site_id: Optional[str] = ""

    @field_validator('cam_id', mode='before')
    def parse_cam_id(cls, v):
        try:
            return int(v)
        except (ValueError, TypeError):
            return 0

class CameraEventRequest(BaseModel):
    type: Literal['metric', 'event', 'ai-info', 'METRIC', 'EVENT', 'AI-INFO'] = "metric"
    processed_at: Optional[float] = 0.0
    meta: EventMeta = Field(default_factory=EventMeta)
    data: EventData = Field(default_factory=EventData)

    @field_validator('type', mode='before')
    def lowercase_type(cls, v):
        return v.lower() if isinstance(v, str) and v else "metric"

    @field_validator('processed_at', mode='before')
    def parse_processed_at(cls, v):
        if not v:
            return 0.0
        if isinstance(v, (int, float)):
            return float(v)
        # Handle ISO string like "2026-01-05T10:43:53.891786473Z"
        try:
            dt = datetime.fromisoformat(str(v).replace('Z', '+00:00'))
            return dt.timestamp()
        except (ValueError, TypeError):
            return 0.0

    @property
    def payload(self) -> EventData:
        return self.data