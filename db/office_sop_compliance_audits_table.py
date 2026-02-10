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

    -- Evidence path referencing source media
    evidence_path String DEFAULT '',

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
