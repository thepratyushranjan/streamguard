OFFICE_COMPLIANCE_AUDITS_TABLE = """
CREATE TABLE IF NOT EXISTS office_compliance_audits (
    -- ═══════════════════════════════════════════════════════════════
    -- METADATA
    -- ═══════════════════════════════════════════════════════════════
    row_id UUID DEFAULT generateUUIDv4(),
    company_id String,
    device_id String,
    cam_id String,
    cam_name LowCardinality(String),
    site_name LowCardinality(String),
    site_id String,
    event_timestamp UInt32,

    -- Geo-Location
    latitude Float64 DEFAULT 0,
    longitude Float64 DEFAULT 0,
    country LowCardinality(String),
    state LowCardinality(String),
    district LowCardinality(String),
    city LowCardinality(String),

    -- Analysis Metadata
    clip_duration_seconds UInt16 DEFAULT 0,
    analysis_mode LowCardinality(String) DEFAULT 'standard',

    -- ═══════════════════════════════════════════════════════════════
    -- 5 CORE SOP TRIGGERS (Primary Dashboard Metrics)
    -- Values: 1=Pass/Yes, 0=Fail/No, -1=N/A
    -- ═══════════════════════════════════════════════════════════════
    sop_access_control      Int8 DEFAULT -1,
    sop_safety_equipment    Int8 DEFAULT -1,
    sop_uniform_compliance  Int8 DEFAULT -1,
    sop_visitor_management  Int8 DEFAULT -1,
    sop_emergency_readiness Int8 DEFAULT -1,

    -- ═══════════════════════════════════════════════════════════════
    -- CRITICAL ALERTS (Int8: 1=Issue, 0=Clear, -1=Not Assessed)
    -- ═══════════════════════════════════════════════════════════════
    unauthorized_zone_entry     Int8 DEFAULT -1,
    fire_smoke_detected         Int8 DEFAULT -1,
    emergency_exit_blocked      Int8 DEFAULT -1,
    crowd_density_critical      Int8 DEFAULT -1,
    physical_altercation        Int8 DEFAULT -1,
    credential_sharing          Int8 DEFAULT -1,
    attendance_mismatch         Int8 DEFAULT -1,
    server_room_entry           Int8 DEFAULT -1,
    lone_worker_hazard          Int8 DEFAULT -1,
    workplace_violence          Int8 DEFAULT -1,

    -- ═══════════════════════════════════════════════════════════════
    -- HIGH ALERTS (Int8: 1=Issue, 0=Clear, -1=Not Assessed)
    -- ═══════════════════════════════════════════════════════════════
    tailgating_entry            Int8 DEFAULT -1,
    fire_equipment_obstructed   Int8 DEFAULT -1,
    safety_glasses_missing      Int8 DEFAULT -1,
    fall_incident               Int8 DEFAULT -1,
    suspicious_concealment      Int8 DEFAULT -1,
    abandoned_object            Int8 DEFAULT -1,
    camera_offline              Int8 DEFAULT -1,
    early_departure             Int8 DEFAULT -1,
    lone_worker_extended        Int8 DEFAULT -1,
    visitor_without_escort      Int8 DEFAULT -1,
    property_removal            Int8 DEFAULT -1,
    contractor_ppe_missing      Int8 DEFAULT -1,

    -- ═══════════════════════════════════════════════════════════════
    -- MEDIUM ALERTS (Int8: 1=Issue, 0=Clear, -1=Not Assessed)
    -- ═══════════════════════════════════════════════════════════════
    trip_hazard_object          Int8 DEFAULT -1,
    smoking_non_designated      Int8 DEFAULT -1,
    id_badge_not_visible        Int8 DEFAULT -1,
    safety_signage_obstructed   Int8 DEFAULT -1,
    first_aid_inaccessible      Int8 DEFAULT -1,
    extended_break              Int8 DEFAULT -1,
    workstation_absence         Int8 DEFAULT -1,
    visitor_badge_missing       Int8 DEFAULT -1,

    -- ═══════════════════════════════════════════════════════════════
    -- LOW ALERTS (Int8: 1=Issue, 0=Clear, -1=Not Assessed)
    -- ═══════════════════════════════════════════════════════════════
    improper_waste_disposal     Int8 DEFAULT -1,
    uniform_non_compliance      Int8 DEFAULT -1,

    -- ═══════════════════════════════════════════════════════════════
    -- SCORE-BASED KPIs (Float32: 0.0-1.0 scale)
    -- ═══════════════════════════════════════════════════════════════
    uniform_score               Float32 DEFAULT 0.0,
    safety_score                Float32 DEFAULT 0.0,
    cleanliness_score           Float32 DEFAULT 0.0,
    access_compliance_score     Float32 DEFAULT 0.0,
    overall_score               Float32 DEFAULT 0.0,

    -- ═══════════════════════════════════════════════════════════════
    -- COUNTS
    -- ═══════════════════════════════════════════════════════════════
    people_count                UInt16 DEFAULT 0,
    employee_count              UInt16 DEFAULT 0,
    visitor_count               UInt16 DEFAULT 0,
    contractor_count            UInt16 DEFAULT 0,
    unidentified_count          UInt16 DEFAULT 0,
    media_analyzed              UInt8 DEFAULT 0,

    -- ═══════════════════════════════════════════════════════════════
    -- ZONE ANALYSIS
    -- ═══════════════════════════════════════════════════════════════
    zone_id LowCardinality(String) DEFAULT '',
    zone_name LowCardinality(String) DEFAULT '',
    zone_type LowCardinality(String) DEFAULT '',
    authorized_access_only UInt8 DEFAULT 0,

    -- ═══════════════════════════════════════════════════════════════
    -- ZONE-SPECIFIC KPIs (Int8: 1=Issue, 0=Clear, -1=Not Assessed)
    -- ═══════════════════════════════════════════════════════════════
    unauthorized_presence       Int8 DEFAULT -1,
    outside_schedule            Int8 DEFAULT -1,
    occupancy_mismatch          Int8 DEFAULT -1,
    after_hours_presence        Int8 DEFAULT -1,
    after_shift                 Int8 DEFAULT -1,
    cross_role_violation        Int8 DEFAULT -1,
    cross_department            Int8 DEFAULT -1,
    no_badge                    Int8 DEFAULT -1,
    unescorted                  Int8 DEFAULT -1,
    overstay                    Int8 DEFAULT -1,
    unauthorized_entry_attempt  Int8 DEFAULT -1,
    tailgating_incident         Int8 DEFAULT -1,
    door_anomaly                Int8 DEFAULT -1,
    ppe_violation               Int8 DEFAULT -1,
    missing_ppe                 Int8 DEFAULT -1,
    safety_breach               Int8 DEFAULT -1,
    group_violation             Int8 DEFAULT -1,
    loitering                   Int8 DEFAULT -1,
    crowd_violation             Int8 DEFAULT -1,
    proximity_violation         Int8 DEFAULT -1,
    repeated_access             Int8 DEFAULT -1,
    infrastructure_violation    Int8 DEFAULT -1,
    event_violation             Int8 DEFAULT -1,
    active_event_type LowCardinality(String) DEFAULT '',

    -- ═══════════════════════════════════════════════════════════════
    -- FACE RECOGNITION (Arrays)
    -- ═══════════════════════════════════════════════════════════════
    `faces.identity_id` Array(String) DEFAULT [],
    `faces.confidence` Array(Float32) DEFAULT [],
    `faces.location` Array(LowCardinality(String)) DEFAULT [],
    `faces.timestamp_offset` Array(UInt16) DEFAULT [],

    -- ═══════════════════════════════════════════════════════════════
    -- STATUS & CLASSIFICATION
    -- ═══════════════════════════════════════════════════════════════
    status LowCardinality(String),
    utilization LowCardinality(String),
    event_triggers Array(LowCardinality(String)) DEFAULT [],

    -- ═══════════════════════════════════════════════════════════════
    -- AI OUTPUTS
    -- ═══════════════════════════════════════════════════════════════
    ai_summary String,

    -- ═══════════════════════════════════════════════════════════════
    -- AGGREGATES
    -- ═══════════════════════════════════════════════════════════════
    critical_issues_count   UInt8 DEFAULT 0,
    high_issues_count       UInt8 DEFAULT 0,
    medium_issues_count     UInt8 DEFAULT 0,
    low_issues_count        UInt8 DEFAULT 0,
    total_issues_count      UInt8 DEFAULT 0,
    overall_compliance_pct  UInt8 DEFAULT 0

) ENGINE = ReplacingMergeTree()
PARTITION BY toYYYYMMDD(toDateTime(event_timestamp))
ORDER BY (site_id, event_timestamp, cam_id)
SETTINGS index_granularity = 8192;
"""

SCHEMAS = [
    ("office_compliance_audits", OFFICE_COMPLIANCE_AUDITS_TABLE, False)
]

# Column metadata for documentation/validation
COLUMN_METADATA = {
    # Metadata
    "row_id": {"type": "UUID", "description": "Unique row identifier", "pk": True},
    "company_id": {"type": "String", "description": "Company identifier"},
    "device_id": {"type": "String", "description": "Device identifier"},
    "cam_id": {"type": "String", "description": "Camera identifier", "pk": True},
    "cam_name": {"type": "LowCardinality(String)", "description": "Camera name"},
    "site_name": {"type": "LowCardinality(String)", "description": "Site/location name"},
    "site_id": {"type": "String", "description": "Unique site ID"},
    "event_timestamp": {"type": "UInt32", "description": "Unix timestamp of event", "partition": True},

    # Geo-Location
    "latitude": {"type": "Float64", "description": "Latitude coordinate"},
    "longitude": {"type": "Float64", "description": "Longitude coordinate"},
    "country": {"type": "LowCardinality(String)", "description": "Country"},
    "state": {"type": "LowCardinality(String)", "description": "State"},
    "district": {"type": "LowCardinality(String)", "description": "District"},
    "city": {"type": "LowCardinality(String)", "description": "City"},

    # Analysis Metadata
    "clip_duration_seconds": {"type": "UInt16", "description": "Duration of analyzed clip in seconds"},
    "analysis_mode": {"type": "LowCardinality(String)", "description": "Analysis mode (standard/quick/detailed)"},

    # 5 Core SOP Triggers
    "sop_access_control": {"type": "Int8", "description": "Access control compliance (1=Pass, 0=Fail, -1=N/A)"},
    "sop_safety_equipment": {"type": "Int8", "description": "Safety equipment accessible (1=Pass, 0=Fail, -1=N/A)"},
    "sop_uniform_compliance": {"type": "Int8", "description": "Uniform/badge compliance (1=Pass, 0=Fail, -1=N/A)"},
    "sop_visitor_management": {"type": "Int8", "description": "Visitor management compliance (1=Pass, 0=Fail, -1=N/A)"},
    "sop_emergency_readiness": {"type": "Int8", "description": "Emergency readiness (1=Pass, 0=Fail, -1=N/A)"},

    # Critical Alerts
    "unauthorized_zone_entry": {"type": "Int8", "description": "Unauthorized zone entry (1=Issue, 0=Clear, -1=N/A)"},
    "fire_smoke_detected": {"type": "Int8", "description": "Fire/smoke detected (1=Issue, 0=Clear, -1=N/A)"},
    "emergency_exit_blocked": {"type": "Int8", "description": "Emergency exit blocked (1=Issue, 0=Clear, -1=N/A)"},
    "crowd_density_critical": {"type": "Int8", "description": "Critical crowd density (1=Issue, 0=Clear, -1=N/A)"},
    "physical_altercation": {"type": "Int8", "description": "Physical altercation detected (1=Issue, 0=Clear, -1=N/A)"},
    "credential_sharing": {"type": "Int8", "description": "Credential sharing detected (1=Issue, 0=Clear, -1=N/A)"},
    "attendance_mismatch": {"type": "Int8", "description": "Attendance mismatch (1=Issue, 0=Clear, -1=N/A)"},
    "server_room_entry": {"type": "Int8", "description": "Unauthorized server room entry (1=Issue, 0=Clear, -1=N/A)"},
    "lone_worker_hazard": {"type": "Int8", "description": "Lone worker hazard (1=Issue, 0=Clear, -1=N/A)"},
    "workplace_violence": {"type": "Int8", "description": "Workplace violence detected (1=Issue, 0=Clear, -1=N/A)"},

    # High Alerts
    "tailgating_entry": {"type": "Int8", "description": "Tailgating entry detected (1=Issue, 0=Clear, -1=N/A)"},
    "fire_equipment_obstructed": {"type": "Int8", "description": "Fire equipment obstructed (1=Issue, 0=Clear, -1=N/A)"},
    "safety_glasses_missing": {"type": "Int8", "description": "Safety glasses missing (1=Issue, 0=Clear, -1=N/A)"},
    "fall_incident": {"type": "Int8", "description": "Fall incident detected (1=Issue, 0=Clear, -1=N/A)"},
    "suspicious_concealment": {"type": "Int8", "description": "Suspicious concealment (1=Issue, 0=Clear, -1=N/A)"},
    "abandoned_object": {"type": "Int8", "description": "Abandoned object detected (1=Issue, 0=Clear, -1=N/A)"},
    "camera_offline": {"type": "Int8", "description": "Camera offline (1=Issue, 0=Clear, -1=N/A)"},
    "early_departure": {"type": "Int8", "description": "Early departure detected (1=Issue, 0=Clear, -1=N/A)"},
    "lone_worker_extended": {"type": "Int8", "description": "Extended lone worker (1=Issue, 0=Clear, -1=N/A)"},
    "visitor_without_escort": {"type": "Int8", "description": "Visitor without escort (1=Issue, 0=Clear, -1=N/A)"},
    "property_removal": {"type": "Int8", "description": "Property removal detected (1=Issue, 0=Clear, -1=N/A)"},
    "contractor_ppe_missing": {"type": "Int8", "description": "Contractor PPE missing (1=Issue, 0=Clear, -1=N/A)"},

    # Medium Alerts
    "trip_hazard_object": {"type": "Int8", "description": "Trip hazard object (1=Issue, 0=Clear, -1=N/A)"},
    "smoking_non_designated": {"type": "Int8", "description": "Smoking in non-designated area (1=Issue, 0=Clear, -1=N/A)"},
    "id_badge_not_visible": {"type": "Int8", "description": "ID badge not visible (1=Issue, 0=Clear, -1=N/A)"},
    "safety_signage_obstructed": {"type": "Int8", "description": "Safety signage obstructed (1=Issue, 0=Clear, -1=N/A)"},
    "first_aid_inaccessible": {"type": "Int8", "description": "First aid inaccessible (1=Issue, 0=Clear, -1=N/A)"},
    "extended_break": {"type": "Int8", "description": "Extended break detected (1=Issue, 0=Clear, -1=N/A)"},
    "workstation_absence": {"type": "Int8", "description": "Workstation absence (1=Issue, 0=Clear, -1=N/A)"},
    "visitor_badge_missing": {"type": "Int8", "description": "Visitor badge missing (1=Issue, 0=Clear, -1=N/A)"},

    # Low Alerts
    "improper_waste_disposal": {"type": "Int8", "description": "Improper waste disposal (1=Issue, 0=Clear, -1=N/A)"},
    "uniform_non_compliance": {"type": "Int8", "description": "Uniform non-compliance (1=Issue, 0=Clear, -1=N/A)"},

    # Score-based KPIs
    "uniform_score": {"type": "Float32", "description": "Uniform compliance score (0.0-1.0)"},
    "safety_score": {"type": "Float32", "description": "Safety compliance score (0.0-1.0)"},
    "cleanliness_score": {"type": "Float32", "description": "Cleanliness score (0.0-1.0)"},
    "access_compliance_score": {"type": "Float32", "description": "Access compliance score (0.0-1.0)"},
    "overall_score": {"type": "Float32", "description": "Overall compliance score (0.0-1.0)"},

    # Counts
    "people_count": {"type": "UInt16", "description": "Total people count"},
    "employee_count": {"type": "UInt16", "description": "Employee count"},
    "visitor_count": {"type": "UInt16", "description": "Visitor count"},
    "contractor_count": {"type": "UInt16", "description": "Contractor count"},
    "unidentified_count": {"type": "UInt16", "description": "Unidentified persons count"},
    "media_analyzed": {"type": "UInt8", "description": "Media files analyzed count"},

    # Zone Analysis
    "zone_id": {"type": "LowCardinality(String)", "description": "Zone identifier"},
    "zone_name": {"type": "LowCardinality(String)", "description": "Zone name"},
    "zone_type": {"type": "LowCardinality(String)", "description": "Zone type category"},
    "authorized_access_only": {"type": "UInt8", "description": "Zone requires authorized access (1=Yes, 0=No)"},

    # Zone-Specific KPIs
    "unauthorized_presence": {"type": "Int8", "description": "Unauthorized presence (1=Issue, 0=Clear, -1=N/A)"},
    "outside_schedule": {"type": "Int8", "description": "Access outside schedules (1=Issue, 0=Clear, -1=N/A)"},
    "occupancy_mismatch": {"type": "Int8", "description": "Occupancy exceeds expected (1=Issue, 0=Clear, -1=N/A)"},
    "after_hours_presence": {"type": "Int8", "description": "Presence outside allowed hours (1=Issue, 0=Clear, -1=N/A)"},
    "after_shift": {"type": "Int8", "description": "Presence after shift end (1=Issue, 0=Clear, -1=N/A)"},
    "cross_role_violation": {"type": "Int8", "description": "Person with unauthorized role (1=Issue, 0=Clear, -1=N/A)"},
    "cross_department": {"type": "Int8", "description": "Person from unauthorized department (1=Issue, 0=Clear, -1=N/A)"},
    "no_badge": {"type": "Int8", "description": "Visitor without badge (1=Issue, 0=Clear, -1=N/A)"},
    "unescorted": {"type": "Int8", "description": "Visitor without escort (1=Issue, 0=Clear, -1=N/A)"},
    "overstay": {"type": "Int8", "description": "Visitor exceeding dwell time (1=Issue, 0=Clear, -1=N/A)"},
    "unauthorized_entry_attempt": {"type": "Int8", "description": "Unauthorized entry attempt (1=Issue, 0=Clear, -1=N/A)"},
    "tailgating_incident": {"type": "Int8", "description": "Tailgating incident (1=Issue, 0=Clear, -1=N/A)"},
    "door_anomaly": {"type": "Int8", "description": "Door open anomaly (1=Issue, 0=Clear, -1=N/A)"},
    "ppe_violation": {"type": "Int8", "description": "PPE violation detected (1=Issue, 0=Clear, -1=N/A)"},
    "missing_ppe": {"type": "Int8", "description": "Specific PPE item missing (1=Issue, 0=Clear, -1=N/A)"},
    "safety_breach": {"type": "Int8", "description": "Safety protocol violation (1=Issue, 0=Clear, -1=N/A)"},
    "group_violation": {"type": "Int8", "description": "Exceeding max group size (1=Issue, 0=Clear, -1=N/A)"},
    "loitering": {"type": "Int8", "description": "Loitering detected (1=Issue, 0=Clear, -1=N/A)"},
    "crowd_violation": {"type": "Int8", "description": "Crowd density violation (1=Issue, 0=Clear, -1=N/A)"},
    "proximity_violation": {"type": "Int8", "description": "Too close to assets (1=Issue, 0=Clear, -1=N/A)"},
    "repeated_access": {"type": "Int8", "description": "Suspicious repeated access (1=Issue, 0=Clear, -1=N/A)"},
    "infrastructure_violation": {"type": "Int8", "description": "Unauthorized in infrastructure zone (1=Issue, 0=Clear, -1=N/A)"},
    "event_violation": {"type": "Int8", "description": "Violation during active event (1=Issue, 0=Clear, -1=N/A)"},
    "active_event_type": {"type": "LowCardinality(String)", "description": "Current event type for dynamic zone"},

    # Face Recognition
    "faces.identity_id": {"type": "Array(String)", "description": "Recognized face identity IDs"},
    "faces.confidence": {"type": "Array(Float32)", "description": "Face recognition confidence scores"},
    "faces.location": {"type": "Array(LowCardinality(String))", "description": "Face locations in frame"},
    "faces.timestamp_offset": {"type": "Array(UInt16)", "description": "Timestamp offsets for face detections"},

    # Status & Classification
    "status": {"type": "LowCardinality(String)", "description": "Event status (safe/warning/critical)"},
    "utilization": {"type": "LowCardinality(String)", "description": "Zone utilization level (low/medium/high)"},
    "event_triggers": {"type": "Array(LowCardinality(String))", "description": "Event trigger types"},

    # AI Outputs
    "ai_summary": {"type": "String", "description": "AI-generated summary"},

    # Aggregates
    "critical_issues_count": {"type": "UInt8", "description": "Count of critical issues"},
    "high_issues_count": {"type": "UInt8", "description": "Count of high-priority issues"},
    "medium_issues_count": {"type": "UInt8", "description": "Count of medium-priority issues"},
    "low_issues_count": {"type": "UInt8", "description": "Count of low-priority issues"},
    "total_issues_count": {"type": "UInt8", "description": "Total count of all issues"},
    "overall_compliance_pct": {"type": "UInt8", "description": "Overall compliance percentage (0-100)"},
}
