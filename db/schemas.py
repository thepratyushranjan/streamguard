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
    company_id: str  # Mandatory field (String)
    device_id: str   # Mandatory field (String)
    cam_id: Union[int, str] = 0
    site_name: str = ""
    zone_name: str  # Mandatory field (String)
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

# --- SOP Compliance Audit Schemas ---

class SOPComplianceAudit(BaseModel):
    # Metadata & Identifiers
    row_id: Optional[str] = None  # UUID as string
    company_id: str
    device_id: str
    site_id: str
    site_name: str
    cam_id: int
    cam_name: str
    event_timestamp: datetime

    # Geo-Location
    latitude: float = 0.0
    longitude: float = 0.0
    country: str = ""
    state: str = ""
    district: str = ""

    # Safety Violation Flags (0 = Safe, 1 = Violation, -1 = Uncertain)
    du_cover_open: int = 0
    manhole_open: int = 0
    fuel_plastic_bottle: int = 0
    foreign_objects: int = 0

    # Quality & Behavioral KPIs
    uniform_score: Optional[float] = None
    hygiene_score: Optional[float] = None
    cleanliness_score: Optional[float] = None

    # Behavioral (1 = Success, 0 = Fail, NULL/None = No Opportunity)
    greeting_detected: Optional[int] = None
    show_zero_detected: Optional[int] = None

    # Contextual Data
    ai_summary: str = ""
    evidence_path: str = ""

    # Dashboard Aggregates
    items_needing_attention: int = 0

class SOPComplianceAuditResponse(SOPComplianceAudit):
    row_id: str  # Mandatory in response


# --- System Health Schemas ---

class CameraStatus(BaseModel):
    cam_id: int = 0
    status: Literal['online', 'offline', 'error'] = 'online'
    fps: int = 0


class SystemHealth(BaseModel):
    # Primary Identifiers
    row_id: Optional[str] = None  # UUID as string
    company_id: str
    device_id: str
    site_id: str
    site_name: str
    cam_id: int = 0
    cam_name: str = ""
    event_timestamp: datetime

    # Geo-Location (Current vs Registered)
    latitude: float = 0.0
    longitude: float = 0.0
    reg_latitude: float = 0.0
    reg_longitude: float = 0.0
    device_ip_local: str = ""
    device_ip_public: str = ""
    country: str = ""
    state: str = ""
    district: str = ""

    # Network & Performance
    primary_internet_speed: float = 0.0
    secondary_internet_speed: float = 0.0
    cpu_usage_percent: int = 0
    ram_usage_percent: int = 0
    device_status: Literal['online', 'offline', 'error'] = 'online'

    # Nested Camera Status
    cameras: List[CameraStatus] = Field(default_factory=list)


class SystemHealthResponse(SystemHealth):
    row_id: str  # Mandatory in response


# --- System Health Payload Request Schemas (for API input) ---

class SystemHealthPayloadMeta(BaseModel):
    """Metadata from the incoming system health payload."""
    event_timestamp: str  # ISO format string, will be parsed
    cam_id: Union[int, str] = 0
    cam_name: str = ""
    company_id: str
    device_id: str
    site_name: str = ""
    site_id: str = ""
    latitude: float = 0.0
    longitude: float = 0.0
    country: str = ""
    state: str = ""
    district: str = ""

    @field_validator('cam_id', mode='before')
    def parse_cam_id(cls, v):
        if isinstance(v, str) and v.startswith('d'):
            try:
                return int(v[1:])
            except (ValueError, TypeError):
                return 0
        try:
            return int(v)
        except (ValueError, TypeError):
            return 0


class SystemHealthPayloadCameras(BaseModel):
    """Camera array data from the system health payload."""
    cam_id: List[int] = Field(default_factory=list)
    status: List[str] = Field(default_factory=list)
    fps: List[int] = Field(default_factory=list)


class SystemHealthPayloadDetails(BaseModel):
    """System details from the incoming system health payload."""
    reg_latitude: float = 0.0
    reg_longitude: float = 0.0
    device_ip_local: str = ""
    device_ip_public: str = ""
    primary_internet_speed: float = 0.0
    secondary_internet_speed: float = 0.0
    cpu_usage_percent: int = 0
    ram_usage_percent: int = 0
    device_status: Literal['online', 'offline', 'error'] = 'online'
    cameras: SystemHealthPayloadCameras = Field(default_factory=SystemHealthPayloadCameras)


class SystemHealthPayloadRequest(BaseModel):
    """
    Request schema for system health POST endpoint.
    Matches the incoming payload structure from devices.
    """
    type: str = "system-health"
    meta: SystemHealthPayloadMeta
    system_details: SystemHealthPayloadDetails = Field(default_factory=SystemHealthPayloadDetails)