SOP_COMPLIANCE_AUDITS_TABLE = """
CREATE TABLE IF NOT EXISTS sop_compliance_audits (
    -- METADATA

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

    -- 5 CORE SOP TRIGGERS (Primary Dashboard Metrics)
    -- (Values: 1=Pass/Yes, 0=Fail/No, -1=N/A)
    sop_manned_air          Int8 DEFAULT -1,    -- Air station has attendant
    sop_greeting            Int8 DEFAULT -1,    -- Namaste greeting detected
    sop_uniform             Int8 DEFAULT -1,    -- Uniform score >= 0.7
    sop_unauthorized        Int8 DEFAULT 0,     -- Unauthorized activity detected
    sop_cleanliness         Int8 DEFAULT -1,    -- Cleanliness score >= 0.7

    -- SAFETY KPIs (Int8: 1=Issue, 0=Clear, -1=Not Assessed)
    du_cover_open           Int8 DEFAULT -1,
    manhole_open            Int8 DEFAULT -1,
    fuel_plastic_bottle     Int8 DEFAULT -1,
    foreign_objects         Int8 DEFAULT -1,
    smoking_detected        Int8 DEFAULT -1,
    fire_detected           Int8 DEFAULT -1,
    fight_detected          Int8 DEFAULT -1,
    mob_gathering           Int8 DEFAULT -1,
    unauthorized_area       Int8 DEFAULT -1,    -- Person in no-entry zone

    -- OPERATIONS KPIs (Int8: 1=Present/Manned, 0=Absent, -1=N/A)
    fsm_present             Int8 DEFAULT -1,
    manned_air_filling      Int8 DEFAULT -1,
    five_liter_testing      Int8 DEFAULT -1,
    five_liter_returned     Int8 DEFAULT -1,

    -- SCORE-BASED KPIs (UInt8: 0-10 scale)
    uniform_score           UInt8 DEFAULT 0,
    cleanliness_score       UInt8 DEFAULT 0,
    safety_score            UInt8 DEFAULT 0,
    hygiene_score           UInt8 DEFAULT 0,
    overall_score           UInt8 DEFAULT 0,

    -- BEHAVIORAL KPIs (Int8: 1=Yes, 0=No, -1=N/A)
    customer_present        UInt8 DEFAULT 0,
    greeting_detected       Int8 DEFAULT -1,
    show_zero_detected      Int8 DEFAULT -1,
    customer_left_unfueled  Int8 DEFAULT -1,
    mobile_phone_use        Int8 DEFAULT -1,    -- FSM distracted by phone

    -- COUNTS
    people_count            UInt8 DEFAULT 0,
    staff_count             UInt8 DEFAULT 0,
    customer_count          UInt8 DEFAULT 0,
    vehicle_count           UInt8 DEFAULT 0,
    active_pumps            UInt8 DEFAULT 0,
    media_analyzed          UInt8 DEFAULT 0,

    -- VEHICLE DATA (Arrays)
    `vehicles.type` Array(LowCardinality(String)) DEFAULT [],
    `vehicles.plate` Array(String) DEFAULT [],
    `vehicles.confidence` Array(Float32) DEFAULT [],

    -- STATUS & CLASSIFICATION
    status LowCardinality(String),
    utilization LowCardinality(String),
    event_triggers Array(LowCardinality(String)) DEFAULT [],

    -- AI OUTPUTS
    ai_summary              String,

    -- AGGREGATES
    items_needing_attention UInt8 DEFAULT 0,
    safety_issues_count     UInt8 DEFAULT 0,
    compliance_issues_count UInt8 DEFAULT 0

) ENGINE = ReplacingMergeTree()
PARTITION BY toYYYYMMDD(toDateTime(event_timestamp))
ORDER BY (site_id, event_timestamp, cam_id)
SETTINGS index_granularity = 8192;
"""

SCHEMAS = [
    ("sop_compliance_audits", SOP_COMPLIANCE_AUDITS_TABLE, False)
]

