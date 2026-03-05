from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Literal, Union
from datetime import datetime, timezone


# --- Reusable Mixins ---

class GeoLocationMixin(BaseModel):
    """Reusable geo-location fields shared across multiple schemas."""
    latitude: float = 0.0
    longitude: float = 0.0
    country: str = ""
    state: str = ""
    district: str = ""
    city: str = ""


class DeviceIdentityMixin(BaseModel):
    """Reusable device/camera identity fields shared across multiple schemas."""
    company_id: str = ""
    device_id: str = ""
    cam_id: str = ""
    cam_name: str = ""
    site_name: str = ""
    site_id: str = ""


# --- Reusable Utility Functions ---

def _lowercase_or_default(v, default: str = "") -> str:
    """Shared logic for lowercase field validators."""
    return v.lower() if isinstance(v, str) and v else default


def copy_fields(source: BaseModel, fields: List[str], default=None) -> dict:
    """Copy specified fields from a Pydantic model to a dict."""
    return {f: getattr(source, f, default) for f in fields if hasattr(source, f)}


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
    dwell_time: float = 0.0
    filled: int = 0
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
    triage_timestamp: Optional[int] = 0
    ai_insights: Optional[str] = ""
    evidence_path: Optional[str] = ""
    event_accuracy_score: Optional[float] = None

    @field_validator('status', mode='before')
    def lowercase_status(cls, v):
        return _lowercase_or_default(v, "safe")

class EventMeta(BaseModel):
    company_id: str  # Mandatory field (String)
    device_id: str   # Mandatory field (String)
    cam_id: str = ""
    site_name: str = ""
    zone_names: List[str] = Field(default_factory=list)  # Mandatory field (Array of Strings)
    ts: float = 0.0
    cam_name: Optional[str] = "Unknown"
    
    latitude: Optional[float] = 0.0
    longitude: Optional[float] = 0.0
    country: Optional[str] = ""
    state: Optional[str] = ""
    district: Optional[str] = ""
    city: Optional[str] = ""
    site_id: Optional[str] = ""

class CameraEventRequest(BaseModel):
    type: Literal['metric', 'event', 'ai-info', 'METRIC', 'EVENT', 'AI-INFO'] = "metric"
    processed_at: Optional[float] = 0.0
    meta: EventMeta = Field(default_factory=EventMeta)
    data: EventData = Field(default_factory=EventData)

    @field_validator('type', mode='before')
    def lowercase_type(cls, v):
        return _lowercase_or_default(v, "metric")

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

# Field name constants
METADATA_FIELDS = ['company_id', 'device_id', 'cam_id', 'cam_name', 'site_name', 
                   'site_id', 'event_timestamp', 'latitude', 'longitude', 
                   'country', 'state', 'district', 'city', 'evidence_path']

SOP_FIELDS = ['sop_manned_air', 'sop_greeting', 'sop_uniform', 'sop_unauthorized', 'sop_cleanliness']
SAFETY_FIELDS = ['du_cover_open', 'manhole_open', 'fuel_plastic_bottle', 'foreign_objects',
                 'smoking_detected', 'fire_detected', 'fight_detected', 'mob_gathering', 'unauthorized_area']
OPERATIONS_FIELDS = ['fsm_present', 'manned_air_filling', 'five_liter_testing', 'five_liter_returned']
SCORE_FIELDS = ['uniform_score', 'cleanliness_score', 'safety_score', 'hygiene_score']
BEHAVIORAL_INT_FIELDS = ['greeting_detected', 'show_zero_detected', 'customer_left_unfueled', 'mobile_phone_use']
COUNT_FIELDS = ['people_count', 'staff_count', 'customer_count', 'vehicle_count', 'active_pumps']
AGGREGATE_FIELDS = ['items_needing_attention', 'safety_issues_count', 'compliance_issues_count']

# OFFICE COMPLIANCE AUDIT SCHEMAS
OFFICE_METADATA_FIELDS = [
    'company_id', 'device_id', 'cam_id', 'cam_name', 'site_name', 'site_id',
    'event_timestamp', 'latitude', 'longitude', 'country', 'state', 'district', 'city',
    'clip_duration_seconds', 'analysis_mode', 'evidence_path'
]
OFFICE_SOP_FIELDS = [
    'sop_access_control', 'sop_safety_equipment', 'sop_uniform_compliance',
    'sop_visitor_management', 'sop_emergency_readiness'
]
OFFICE_CRITICAL_ALERT_FIELDS = [
    'unauthorized_zone_entry', 'fire_smoke_detected', 'emergency_exit_blocked',
    'crowd_density_critical', 'physical_altercation', 'credential_sharing',
    'attendance_mismatch', 'server_room_entry', 'lone_worker_hazard', 'workplace_violence'
]
OFFICE_HIGH_ALERT_FIELDS = [
    'tailgating_entry', 'fire_equipment_obstructed', 'safety_glasses_missing',
    'fall_incident', 'suspicious_concealment', 'abandoned_object', 'camera_offline',
    'early_departure', 'lone_worker_extended', 'visitor_without_escort',
    'property_removal', 'contractor_ppe_missing'
]
OFFICE_MEDIUM_ALERT_FIELDS = [
    'trip_hazard_object', 'smoking_non_designated', 'id_badge_not_visible',
    'safety_signage_obstructed', 'first_aid_inaccessible', 'extended_break',
    'workstation_absence', 'visitor_badge_missing'
]
OFFICE_LOW_ALERT_FIELDS = ['improper_waste_disposal', 'uniform_non_compliance']
OFFICE_SCORE_FIELDS = [
    'uniform_score', 'safety_score', 'cleanliness_score',
    'access_compliance_score', 'overall_score'
]
OFFICE_COUNT_FIELDS = [
    'people_count', 'employee_count', 'visitor_count',
    'contractor_count', 'unidentified_count', 'media_analyzed'
]
OFFICE_ZONE_FIELDS = ['zone_id', 'zone_name', 'zone_type', 'authorized_access_only']
OFFICE_ZONE_KPI_FIELDS = [
    'unauthorized_presence', 'outside_schedule', 'occupancy_mismatch',
    'after_hours_presence', 'after_shift', 'cross_role_violation', 'cross_department',
    'no_badge', 'unescorted', 'overstay', 'unauthorized_entry_attempt',
    'tailgating_incident', 'door_anomaly', 'ppe_violation', 'missing_ppe',
    'safety_breach', 'group_violation', 'loitering', 'crowd_violation',
    'proximity_violation', 'repeated_access', 'infrastructure_violation',
    'event_violation', 'active_event_type'
]
OFFICE_AGGREGATE_FIELDS = [
    'critical_issues_count', 'high_issues_count', 'medium_issues_count',
    'low_issues_count', 'total_issues_count', 'overall_compliance_pct'
]

# Utility function for score conversion (DRY: reusable across schemas)
def score_to_uint8(value: Optional[float]) -> int:
    """Convert 0-1 float score to 0-10 integer scale."""
    return min(max(int((value or 0) * 10), 0), 10)


class CoerceIntMixin(BaseModel):
    """Mixin that coerces float values to int (via round) for all int fields.
    
    Use this as a parent class for any schema where the AI might return
    float values (e.g. 1.0, 0.0) for fields defined as int.
    """
    @field_validator("*", mode="before")
    @classmethod
    def coerce_float_to_int(cls, v, info):
        # Only round floats for fields that are annotated as int
        if isinstance(v, float) and info.field_name in cls.model_fields:
            field = cls.model_fields[info.field_name]
            if field.annotation is int:
                return round(v)
        return v

class AIResponseMetadata(DeviceIdentityMixin, GeoLocationMixin):
    """AI Response metadata section."""
    event_timestamp: int = 0
    clip_duration_seconds: int = 0
    media_analyzed: int = 0
    evidence_path: Optional[str] = ""


class AIResponseSafety(CoerceIntMixin):
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


class AIResponseOperations(CoerceIntMixin):
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


class AIResponseBehavioral(CoerceIntMixin):
    """AI Response behavioral KPIs."""
    customer_present: bool = False
    greeting_detected: int = -1
    show_zero_detected: int = -1
    customer_left_unfueled: int = -1
    mobile_phone_use: int = -1


class AIResponseCounts(CoerceIntMixin):
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


class AIResponseAggregates(CoerceIntMixin):
    """AI Response aggregates."""
    items_needing_attention: int = 0
    overall_compliance_pct: int = 0
    safety_issues_count: int = 0
    compliance_issues_count: int = 0


class AIResponseSOP(CoerceIntMixin):
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
        return copy_fields(source, fields)

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


class SOPComplianceAudit(DeviceIdentityMixin, GeoLocationMixin):
    """SOP Compliance Audit model for database storage."""
    # METADATA
    row_id: Optional[str] = None
    event_timestamp: int = 0
    evidence_path: str = ""

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
    cam_id: str = ""
    cam_name: str = ""
    zone_names: List[str] = Field(default_factory=list)
    status: Literal['online', 'offline', 'error'] = 'online'
    fps: float = 0.0


class SystemHealth(BaseModel):
    # Primary Identifiers
    row_id: Optional[str] = None  # UUID as string
    company_id: str
    device_id: str
    site_id: str
    site_name: str
    event_timestamp: int

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
    city: str = ""

    # Network & Performance
    primary_internet_speed: float = 0.0
    secondary_internet_speed: float = 0.0
    cpu_usage_percent: float = 0.0
    ram_usage_percent: float = 0.0
    device_status: Literal['online', 'offline', 'error'] = 'online'

    # Nested Camera Status
    cameras: List[CameraStatus] = Field(default_factory=list)


class SystemHealthResponse(SystemHealth):
    row_id: str  # Mandatory in response


# --- System Health Payload Request Schemas (for API input) ---

class SystemHealthPayloadMeta(BaseModel):
    """Metadata from the incoming system health payload."""
    event_timestamp: Union[int, str]  # Unix timestamp (int) or ISO string
    company_id: str
    device_id: str
    site_name: str = ""
    site_id: str = ""
    latitude: float = 0.0
    longitude: float = 0.0
    country: str = ""
    state: str = ""
    district: str = ""
    city: str = ""


class SystemHealthPayloadCameras(BaseModel):
    """Camera array data from the system health payload."""
    cam_id: List[str] = Field(default_factory=list)
    cam_name: List[str] = Field(default_factory=list)
    zone_names: List[List[str]] = Field(default_factory=list)
    status: List[str] = Field(default_factory=list)
    fps: List[float] = Field(default_factory=list)


class SystemHealthPayloadDetails(BaseModel):
    """System details from the incoming system health payload."""
    reg_latitude: float = 0.0
    reg_longitude: float = 0.0
    device_ip_local: str = ""
    device_ip_public: str = ""
    primary_internet_speed: float = 0.0
    secondary_internet_speed: float = 0.0
    cpu_usage_percent: float = 0.0
    ram_usage_percent: float = 0.0
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


# --- Triage Update Schema ---

class TriageUpdateRequest(BaseModel):
    """Request body for updating triage fields."""
    triaged_by: Optional[str] = None
    triage_timestamp: Optional[int] = None
    ai_insights: Optional[str] = None
    triage_notes: Optional[str] = None



class OfficeAIResponseMetadata(DeviceIdentityMixin, GeoLocationMixin):
    """Office AI Response metadata section."""
    event_timestamp: int = 0
    clip_duration_seconds: int = 0
    media_analyzed: int = 0
    analysis_mode: str = "standard"
    evidence_path: Optional[str] = ""


class OfficeAIResponseCriticalAlerts(CoerceIntMixin):
    """Office AI Response critical alerts (1=Issue, 0=Clear, -1=N/A)."""
    unauthorized_zone_entry: int = -1
    fire_smoke_detected: int = -1
    emergency_exit_blocked: int = -1
    crowd_density_critical: int = -1
    physical_altercation: int = -1
    credential_sharing: int = -1
    attendance_mismatch: int = -1
    server_room_entry: int = -1
    lone_worker_hazard: int = -1
    workplace_violence: int = -1


class OfficeAIResponseHighAlerts(CoerceIntMixin):
    """Office AI Response high alerts (1=Issue, 0=Clear, -1=N/A)."""
    tailgating_entry: int = -1
    fire_equipment_obstructed: int = -1
    safety_glasses_missing: int = -1
    fall_incident: int = -1
    suspicious_concealment: int = -1
    abandoned_object: int = -1
    camera_offline: int = -1
    early_departure: int = -1
    lone_worker_extended: int = -1
    visitor_without_escort: int = -1
    property_removal: int = -1
    contractor_ppe_missing: int = -1


class OfficeAIResponseMediumAlerts(CoerceIntMixin):
    """Office AI Response medium alerts (1=Issue, 0=Clear, -1=N/A)."""
    trip_hazard_object: int = -1
    smoking_non_designated: int = -1
    id_badge_not_visible: int = -1
    safety_signage_obstructed: int = -1
    first_aid_inaccessible: int = -1
    extended_break: int = -1
    workstation_absence: int = -1
    visitor_badge_missing: int = -1


class OfficeAIResponseLowAlerts(CoerceIntMixin):
    """Office AI Response low alerts (1=Issue, 0=Clear, -1=N/A)."""
    improper_waste_disposal: int = -1
    uniform_non_compliance: int = -1


class OfficeAIResponseScores(BaseModel):
    """Office AI Response scores (0.0-1.0 float scale)."""
    uniform_compliance_score: Optional[float] = 0.0
    safety_score: Optional[float] = 0.0
    cleanliness_score: Optional[float] = 0.0
    access_compliance_score: Optional[float] = 0.0
    overall_compliance_score: Optional[float] = 0.0


class OfficeAIResponseCounts(CoerceIntMixin):
    """Office AI Response counts."""
    people_count: int = 0
    employee_count: int = 0
    visitor_count: int = 0
    contractor_count: int = 0
    unidentified_count: int = 0


class OfficeAIResponseZoneAnalysis(BaseModel):
    """Office AI Response zone analysis."""
    zone_id: str = ""
    zone_name: str = ""
    zone_type: str = ""
    occupancy_level: str = "low"
    authorized_access_only: bool = False


class OfficeAIResponseFaceMatch(BaseModel):
    """Office AI Response face match entry."""
    identity_id: str = ""
    confidence: float = 0.0
    location: str = ""
    timestamp_offset: int = 0


class OfficeAIResponseClassification(BaseModel):
    """Office AI Response classification."""
    status: str = "safe"
    utilization: str = "low"


class OfficeAIResponseAggregates(CoerceIntMixin):
    """Office AI Response aggregates."""
    critical_issues_count: int = 0
    high_issues_count: int = 0
    medium_issues_count: int = 0
    low_issues_count: int = 0
    total_issues_count: int = 0
    overall_compliance_pct: int = 0


class OfficeAIResponseSOP(CoerceIntMixin):
    """Office AI Response SOP core triggers (1=Pass, 0=Fail, -1=N/A)."""
    sop_access_control: int = -1
    sop_safety_equipment: int = -1
    sop_uniform_compliance: int = -1
    sop_visitor_management: int = -1
    sop_emergency_readiness: int = -1


class OfficeAIResponse(BaseModel):
    """Complete Office AI validation response schema."""
    metadata: OfficeAIResponseMetadata = Field(default_factory=OfficeAIResponseMetadata)
    critical_alerts: OfficeAIResponseCriticalAlerts = Field(default_factory=OfficeAIResponseCriticalAlerts)
    high_alerts: OfficeAIResponseHighAlerts = Field(default_factory=OfficeAIResponseHighAlerts)
    medium_alerts: OfficeAIResponseMediumAlerts = Field(default_factory=OfficeAIResponseMediumAlerts)
    low_alerts: OfficeAIResponseLowAlerts = Field(default_factory=OfficeAIResponseLowAlerts)
    scores: OfficeAIResponseScores = Field(default_factory=OfficeAIResponseScores)
    counts: OfficeAIResponseCounts = Field(default_factory=OfficeAIResponseCounts)
    zone_analysis: OfficeAIResponseZoneAnalysis = Field(default_factory=OfficeAIResponseZoneAnalysis)
    face_matches: List[OfficeAIResponseFaceMatch] = Field(default_factory=list)
    classification: OfficeAIResponseClassification = Field(default_factory=OfficeAIResponseClassification)
    triggers: List[str] = Field(default_factory=list)
    ai_summary: str = ""
    aggregates: OfficeAIResponseAggregates = Field(default_factory=OfficeAIResponseAggregates)
    sop: OfficeAIResponseSOP = Field(default_factory=OfficeAIResponseSOP)

    def _copy_fields(self, source: BaseModel, fields: List[str]) -> dict:
        """Copy specified fields from source model to dict."""
        return copy_fields(source, fields)

    def _extract_faces(self) -> dict:
        """Extract face data into separate arrays."""
        return {
            'faces_identity_id': [f.identity_id for f in self.face_matches],
            'faces_confidence': [f.confidence for f in self.face_matches],
            'faces_location': [f.location for f in self.face_matches],
            'faces_timestamp_offset': [f.timestamp_offset for f in self.face_matches],
        }

    def to_audit(self) -> "OfficeComplianceAudit":
        """Convert AI response to OfficeComplianceAudit model."""
        audit_data = {}

        # Copy metadata fields
        audit_data.update(self._copy_fields(self.metadata, OFFICE_METADATA_FIELDS))
        audit_data['media_analyzed'] = self.metadata.media_analyzed

        # Copy SOP fields
        audit_data.update(self._copy_fields(self.sop, OFFICE_SOP_FIELDS))

        # Copy alert fields
        audit_data.update(self._copy_fields(self.critical_alerts, OFFICE_CRITICAL_ALERT_FIELDS))
        audit_data.update(self._copy_fields(self.high_alerts, OFFICE_HIGH_ALERT_FIELDS))
        audit_data.update(self._copy_fields(self.medium_alerts, OFFICE_MEDIUM_ALERT_FIELDS))
        audit_data.update(self._copy_fields(self.low_alerts, OFFICE_LOW_ALERT_FIELDS))

        # Copy scores (map input field names to DB field names)
        audit_data['uniform_score'] = self.scores.uniform_compliance_score or 0.0
        audit_data['safety_score'] = self.scores.safety_score or 0.0
        audit_data['cleanliness_score'] = self.scores.cleanliness_score or 0.0
        audit_data['access_compliance_score'] = self.scores.access_compliance_score or 0.0
        audit_data['overall_score'] = self.scores.overall_compliance_score or 0.0

        # Copy counts
        audit_data.update(self._copy_fields(self.counts, OFFICE_COUNT_FIELDS))

        # Copy zone analysis
        audit_data['zone_id'] = self.zone_analysis.zone_id
        audit_data['zone_name'] = self.zone_analysis.zone_name
        audit_data['zone_type'] = self.zone_analysis.zone_type
        audit_data['authorized_access_only'] = 1 if self.zone_analysis.authorized_access_only else 0

        # Extract face recognition data
        audit_data.update(self._extract_faces())

        # Classification and triggers
        audit_data['status'] = self.classification.status
        audit_data['utilization'] = self.classification.utilization
        audit_data['event_triggers'] = self.triggers
        audit_data['ai_summary'] = self.ai_summary

        # Aggregates
        audit_data.update(self._copy_fields(self.aggregates, OFFICE_AGGREGATE_FIELDS))

        return OfficeComplianceAudit(**audit_data)


class OfficeComplianceAudit(DeviceIdentityMixin, GeoLocationMixin):
    """Office Compliance Audit model for database storage."""
    # METADATA
    row_id: Optional[str] = None
    event_timestamp: int = 0
    evidence_path: str = ""

    # Analysis Metadata
    clip_duration_seconds: int = 0
    analysis_mode: str = "standard"

    # 5 CORE SOP TRIGGERS (1=Pass, 0=Fail, -1=N/A)
    sop_access_control: int = -1
    sop_safety_equipment: int = -1
    sop_uniform_compliance: int = -1
    sop_visitor_management: int = -1
    sop_emergency_readiness: int = -1

    # CRITICAL ALERTS (1=Issue, 0=Clear, -1=N/A)
    unauthorized_zone_entry: int = -1
    fire_smoke_detected: int = -1
    emergency_exit_blocked: int = -1
    crowd_density_critical: int = -1
    physical_altercation: int = -1
    credential_sharing: int = -1
    attendance_mismatch: int = -1
    server_room_entry: int = -1
    lone_worker_hazard: int = -1
    workplace_violence: int = -1

    # HIGH ALERTS (1=Issue, 0=Clear, -1=N/A)
    tailgating_entry: int = -1
    fire_equipment_obstructed: int = -1
    safety_glasses_missing: int = -1
    fall_incident: int = -1
    suspicious_concealment: int = -1
    abandoned_object: int = -1
    camera_offline: int = -1
    early_departure: int = -1
    lone_worker_extended: int = -1
    visitor_without_escort: int = -1
    property_removal: int = -1
    contractor_ppe_missing: int = -1

    # MEDIUM ALERTS (1=Issue, 0=Clear, -1=N/A)
    trip_hazard_object: int = -1
    smoking_non_designated: int = -1
    id_badge_not_visible: int = -1
    safety_signage_obstructed: int = -1
    first_aid_inaccessible: int = -1
    extended_break: int = -1
    workstation_absence: int = -1
    visitor_badge_missing: int = -1

    # LOW ALERTS (1=Issue, 0=Clear, -1=N/A)
    improper_waste_disposal: int = -1
    uniform_non_compliance: int = -1

    # SCORE-BASED KPIs (0.0-1.0 scale)
    uniform_score: float = 0.0
    safety_score: float = 0.0
    cleanliness_score: float = 0.0
    access_compliance_score: float = 0.0
    overall_score: float = 0.0

    # COUNTS
    people_count: int = 0
    employee_count: int = 0
    visitor_count: int = 0
    contractor_count: int = 0
    unidentified_count: int = 0
    media_analyzed: int = 0

    # ZONE ANALYSIS
    zone_id: str = ""
    zone_name: str = ""
    zone_type: str = ""
    authorized_access_only: int = 0

    # ZONE-SPECIFIC KPIs (1=Issue, 0=Clear, -1=N/A)
    unauthorized_presence: int = -1
    outside_schedule: int = -1
    occupancy_mismatch: int = -1
    after_hours_presence: int = -1
    after_shift: int = -1
    cross_role_violation: int = -1
    cross_department: int = -1
    no_badge: int = -1
    unescorted: int = -1
    overstay: int = -1
    unauthorized_entry_attempt: int = -1
    tailgating_incident: int = -1
    door_anomaly: int = -1
    ppe_violation: int = -1
    missing_ppe: int = -1
    safety_breach: int = -1
    group_violation: int = -1
    loitering: int = -1
    crowd_violation: int = -1
    proximity_violation: int = -1
    repeated_access: int = -1
    infrastructure_violation: int = -1
    event_violation: int = -1
    active_event_type: str = ""

    # FACE RECOGNITION (Arrays)
    faces_identity_id: List[str] = Field(default_factory=list)
    faces_confidence: List[float] = Field(default_factory=list)
    faces_location: List[str] = Field(default_factory=list)
    faces_timestamp_offset: List[int] = Field(default_factory=list)

    # STATUS & CLASSIFICATION
    status: str = "safe"
    utilization: str = "low"
    event_triggers: List[str] = Field(default_factory=list)

    # AI OUTPUTS
    ai_summary: str = ""

    # AGGREGATES
    critical_issues_count: int = 0
    high_issues_count: int = 0
    medium_issues_count: int = 0
    low_issues_count: int = 0
    total_issues_count: int = 0
    overall_compliance_pct: int = 0


class OfficeComplianceAuditResponse(OfficeComplianceAudit):
    """Response model with mandatory row_id."""
    row_id: str  # Mandatory in response


# --- Attendance Records Schemas ---

ATTENDANCE_DATA_FIELDS = ['event_type', 'person_name', 'person_id', 'zone',
                          'direction', 'confidence', 'track_id', 'description', 'recorded_at',
                          'total_work_hours', 'workstation_absence']


class AttendanceData(BaseModel):
    """Attendance event data section."""
    event_type: str
    person_name: str
    person_id: int
    zone: str = ""
    direction: str = "auto"
    confidence: float = 0.0
    track_id: int = 0
    description: str = ""
    recorded_at: int
    total_work_hours: int = 0
    workstation_absence: int = 0

    @field_validator('event_type', mode='before')
    def lowercase_event_type(cls, v):
        return v.lower() if isinstance(v, str) and v else v


class AttendanceRequest(BaseModel):
    """Request schema for attendance POST endpoint."""
    type: Literal['attendance', 'ATTENDANCE'] = "attendance"
    meta: EventMeta
    data: AttendanceData

    @field_validator('type', mode='before')
    def lowercase_type(cls, v):
        return _lowercase_or_default(v, "attendance")


class AttendanceRecord(DeviceIdentityMixin, GeoLocationMixin):
    """Flat attendance record model for database storage."""
    row_id: Optional[str] = None
    zone_names: List[str] = Field(default_factory=list)
    event_type: str = ""
    person_name: str = ""
    person_id: int = 0
    zone: str = ""
    direction: str = "auto"
    confidence: float = 0.0
    track_id: int = 0
    description: str = ""
    recorded_at: int = 0
    total_work_hours: int = 0
    workstation_absence: int = 0

    @classmethod
    def from_request(cls, req: AttendanceRequest) -> "AttendanceRecord":
        """Flatten nested request payload into a DB-ready record."""
        meta_fields = [f for f in METADATA_FIELDS if f not in ('event_timestamp', 'evidence_path')] + ['zone_names']
        data = {f: getattr(req.meta, f) for f in meta_fields}
        data.update({f: getattr(req.data, f) for f in ATTENDANCE_DATA_FIELDS})
        return cls(**data)

class AttendanceRecordResponse(AttendanceRecord):
    """Response model with mandatory row_id."""
    row_id: str

