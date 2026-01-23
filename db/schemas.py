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
    # Optional detection metadata
    model_id: int = 0
    track_id: int = 0
    parent_track_id: int = 0
    # Optional LPR (License Plate Recognition) data
    lpr: Optional[dict] = Field(default_factory=dict)

    @field_validator('object_id', mode='before')
    def parse_object_id(cls, v):
        if not v:
            return 0
        try:
            return int(v)
        except (ValueError, TypeError):
            return 0

class EventData(BaseModel):
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

# Utility function for score conversion (DRY: reusable across schemas)
def score_to_uint8(value: Optional[float]) -> int:
    """Convert 0-1 float score to 0-10 integer scale."""
    return min(max(int((value or 0) * 10), 0), 10)


# Field name constants for mapping (DRY: avoids repetition in to_audit and services)
METADATA_FIELDS = ['company_id', 'device_id', 'cam_id', 'cam_name', 'site_name', 
                   'site_id', 'event_timestamp', 'latitude', 'longitude', 
                   'country', 'state', 'district']
SOP_FIELDS = ['sop_manned_air', 'sop_greeting', 'sop_uniform', 'sop_unauthorized', 'sop_cleanliness']
SAFETY_FIELDS = ['du_cover_open', 'manhole_open', 'fuel_plastic_bottle', 'foreign_objects',
                 'smoking_detected', 'fire_detected', 'fight_detected', 'mob_gathering', 'unauthorized_area']
OPERATIONS_FIELDS = ['fsm_present', 'manned_air_filling', 'five_liter_testing', 'five_liter_returned']
SCORE_FIELDS = ['uniform_score', 'cleanliness_score', 'safety_score', 'hygiene_score']
BEHAVIORAL_INT_FIELDS = ['greeting_detected', 'show_zero_detected', 'customer_left_unfueled', 'mobile_phone_use']
COUNT_FIELDS = ['people_count', 'staff_count', 'customer_count', 'vehicle_count', 'active_pumps']
AGGREGATE_FIELDS = ['items_needing_attention', 'safety_issues_count', 'compliance_issues_count']


class AIResponseMetadata(BaseModel):
    """AI Response metadata section."""
    company_id: str = ""
    device_id: str = ""
    cam_id: int = 0
    cam_name: str = ""
    site_name: str = ""
    site_id: str = ""
    event_timestamp: int = 0
    latitude: float = 0.0
    longitude: float = 0.0
    country: str = ""
    state: str = ""
    district: str = ""
    clip_duration_seconds: int = 0
    media_analyzed: int = 0


class AIResponseSafety(BaseModel):
    """AI Response safety KPIs."""
    du_cover_open: int = -1
    manhole_open: int = -1
    fuel_plastic_bottle: int = -1
    foreign_objects: int = -1
    smoking_detected: int = -1
    fire_detected: int = -1
    fight_detected: int = -1
    mob_gathering: int = -1
    unauthorized_area: int = -1


class AIResponseOperations(BaseModel):
    """AI Response operations KPIs."""
    fsm_present: int = -1
    manned_air_filling: int = -1
    five_liter_testing: int = -1
    five_liter_returned: int = -1


class AIResponseScores(BaseModel):
    """AI Response scores (0-1 float scale)."""
    uniform_score: Optional[float] = None
    cleanliness_score: Optional[float] = None
    safety_score: Optional[float] = None
    hygiene_score: Optional[float] = None

    def to_uint8(self, value: Optional[float]) -> int:
        """Convert 0-1 score to 0-10 scale."""
        return score_to_uint8(value)

    def to_uint8_dict(self) -> dict:
        """Convert all scores to uint8 dict for bulk assignment."""
        return {field: score_to_uint8(getattr(self, field)) for field in SCORE_FIELDS}


class AIResponseBehavioral(BaseModel):
    """AI Response behavioral KPIs."""
    customer_present: bool = False
    greeting_detected: int = -1
    show_zero_detected: int = -1
    customer_left_unfueled: int = -1
    mobile_phone_use: int = -1


class AIResponseCounts(BaseModel):
    """AI Response counts."""
    people_count: int = 0
    staff_count: int = 0
    customer_count: int = 0
    vehicle_count: int = 0
    active_pumps: int = 0


class AIResponseVehicle(BaseModel):
    """AI Response vehicle entry."""
    type: Optional[str] = None
    plate: Optional[str] = None
    plate_confidence: Optional[float] = None


class AIResponseClassification(BaseModel):
    """AI Response classification."""
    status: str = ""
    utilization: str = ""


class AIResponseAggregates(BaseModel):
    """AI Response aggregates."""
    items_needing_attention: int = 0
    overall_compliance_pct: int = 0
    safety_issues_count: int = 0
    compliance_issues_count: int = 0


class AIResponseSOP(BaseModel):
    """AI Response SOP core triggers."""
    sop_manned_air: int = -1
    sop_greeting: int = -1
    sop_uniform: int = -1
    sop_unauthorized: int = 0
    sop_cleanliness: int = -1


class AIResponse(BaseModel):
    """Complete AI validation response schema."""
    metadata: AIResponseMetadata = Field(default_factory=AIResponseMetadata)
    safety: AIResponseSafety = Field(default_factory=AIResponseSafety)
    operations: AIResponseOperations = Field(default_factory=AIResponseOperations)
    scores: AIResponseScores = Field(default_factory=AIResponseScores)
    behavioral: AIResponseBehavioral = Field(default_factory=AIResponseBehavioral)
    counts: AIResponseCounts = Field(default_factory=AIResponseCounts)
    vehicles: List[AIResponseVehicle] = Field(default_factory=list)
    classification: AIResponseClassification = Field(default_factory=AIResponseClassification)
    triggers: List[str] = Field(default_factory=list)
    ai_summary: str = ""
    aggregates: AIResponseAggregates = Field(default_factory=AIResponseAggregates)
    sop: AIResponseSOP = Field(default_factory=AIResponseSOP)

    def _copy_fields(self, source: BaseModel, fields: List[str]) -> dict:
        """Copy specified fields from source model to dict."""
        return {field: getattr(source, field) for field in fields}

    def _extract_vehicles(self) -> dict:
        """Extract vehicle data into separate arrays."""
        return {
            'vehicles_type': [v.type or "" for v in self.vehicles],
            'vehicles_plate': [v.plate or "" for v in self.vehicles],
            'vehicles_confidence': [v.plate_confidence or 0.0 for v in self.vehicles],
        }

    def to_audit(self) -> "SOPComplianceAudit":
        """Convert AI response to SOPComplianceAudit model."""
        # Build audit data using helper methods (DRY approach)
        audit_data = {}

        # Copy fields from nested models
        audit_data.update(self._copy_fields(self.metadata, METADATA_FIELDS))
        audit_data.update(self._copy_fields(self.sop, SOP_FIELDS))
        audit_data.update(self._copy_fields(self.safety, SAFETY_FIELDS))
        audit_data.update(self._copy_fields(self.operations, OPERATIONS_FIELDS))
        audit_data.update(self._copy_fields(self.counts, COUNT_FIELDS))
        audit_data.update(self._copy_fields(self.aggregates, AGGREGATE_FIELDS))

        # Convert scores from 0-1 to 0-10 scale
        audit_data.update(self.scores.to_uint8_dict())

        # Behavioral fields (special handling for customer_present)
        audit_data['customer_present'] = 1 if self.behavioral.customer_present else 0
        audit_data.update(self._copy_fields(self.behavioral, BEHAVIORAL_INT_FIELDS))

        # Additional mappings
        audit_data['media_analyzed'] = self.metadata.media_analyzed
        audit_data.update(self._extract_vehicles())
        audit_data['status'] = self.classification.status
        audit_data['utilization'] = self.classification.utilization
        audit_data['event_triggers'] = self.triggers
        audit_data['ai_summary'] = self.ai_summary

        return SOPComplianceAudit(**audit_data)


class VehicleData(BaseModel):
    """Vehicle detection data."""
    type: str = ""
    plate: str = ""
    confidence: float = 0.0


class SOPComplianceAudit(BaseModel):
    """SOP Compliance Audit model for database storage."""
    # METADATA
    row_id: Optional[str] = None
    company_id: str = ""
    device_id: str = ""
    cam_id: int = 0
    cam_name: str = ""
    site_name: str = ""
    site_id: str = ""
    event_timestamp: int = 0

    # Geo-Location
    latitude: float = 0.0
    longitude: float = 0.0
    country: str = ""
    state: str = ""
    district: str = ""

    # 5 CORE SOP TRIGGERS (1=Pass, 0=Fail, -1=N/A)
    sop_manned_air: int = -1
    sop_greeting: int = -1
    sop_uniform: int = -1
    sop_unauthorized: int = 0
    sop_cleanliness: int = -1

    # SAFETY KPIs (1=Issue, 0=Clear, -1=Not Assessed)
    du_cover_open: int = -1
    manhole_open: int = -1
    fuel_plastic_bottle: int = -1
    foreign_objects: int = -1
    smoking_detected: int = -1
    fire_detected: int = -1
    fight_detected: int = -1
    mob_gathering: int = -1
    unauthorized_area: int = -1

    # OPERATIONS KPIs (1=Present, 0=Absent, -1=N/A)
    fsm_present: int = -1
    manned_air_filling: int = -1
    five_liter_testing: int = -1
    five_liter_returned: int = -1

    # SCORE-BASED KPIs (0-10 scale)
    uniform_score: int = 0
    cleanliness_score: int = 0
    safety_score: int = 0
    hygiene_score: int = 0
    overall_score: int = 0

    # BEHAVIORAL KPIs (1=Yes, 0=No, -1=N/A)
    customer_present: int = 0
    greeting_detected: int = -1
    show_zero_detected: int = -1
    customer_left_unfueled: int = -1
    mobile_phone_use: int = -1

    # COUNTS
    people_count: int = 0
    staff_count: int = 0
    customer_count: int = 0
    vehicle_count: int = 0
    active_pumps: int = 0
    media_analyzed: int = 0

    # VEHICLE DATA (Arrays)
    vehicles_type: List[str] = Field(default_factory=list)
    vehicles_plate: List[str] = Field(default_factory=list)
    vehicles_confidence: List[float] = Field(default_factory=list)

    # STATUS & CLASSIFICATION
    status: str = ""
    utilization: str = ""
    event_triggers: List[str] = Field(default_factory=list)

    # AI OUTPUTS
    ai_summary: str = ""

    # AGGREGATES
    items_needing_attention: int = 0
    safety_issues_count: int = 0
    compliance_issues_count: int = 0

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