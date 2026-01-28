SOP_COMPLIANCE_AUDITS_TABLE = """
CREATE TABLE IF NOT EXISTS sop_compliance_audits (
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

    -- ═══════════════════════════════════════════════════════════════
    -- 5 CORE SOP TRIGGERS (Primary Dashboard Metrics)
    -- Values: 1=Pass/Yes, 0=Fail/No, -1=N/A
    -- ═══════════════════════════════════════════════════════════════
    sop_manned_air          Int8 DEFAULT -1,    -- Air station has attendant
    sop_greeting            Int8 DEFAULT -1,    -- Namaste greeting detected
    sop_uniform             Int8 DEFAULT -1,    -- Uniform score >= 0.7
    sop_unauthorized        Int8 DEFAULT 0,     -- Unauthorized activity detected
    sop_cleanliness         Int8 DEFAULT -1,    -- Cleanliness score >= 0.7

    -- ═══════════════════════════════════════════════════════════════
    -- SAFETY KPIs (Int8: 1=Issue, 0=Clear, -1=Not Assessed)
    -- ═══════════════════════════════════════════════════════════════
    du_cover_open           Int8 DEFAULT -1,
    manhole_open            Int8 DEFAULT -1,
    fuel_plastic_bottle     Int8 DEFAULT -1,
    foreign_objects         Int8 DEFAULT -1,
    smoking_detected        Int8 DEFAULT -1,
    fire_detected           Int8 DEFAULT -1,
    fight_detected          Int8 DEFAULT -1,
    mob_gathering           Int8 DEFAULT -1,
    unauthorized_area       Int8 DEFAULT -1,    -- Person in no-entry zone

    -- ═══════════════════════════════════════════════════════════════
    -- OPERATIONS KPIs (Int8: 1=Present/Manned, 0=Absent, -1=N/A)
    -- ═══════════════════════════════════════════════════════════════
    fsm_present             Int8 DEFAULT -1,
    manned_air_filling      Int8 DEFAULT -1,
    five_liter_testing      Int8 DEFAULT -1,
    five_liter_returned     Int8 DEFAULT -1,

    -- ═══════════════════════════════════════════════════════════════
    -- SCORE-BASED KPIs (UInt8: 0-10 scale)
    -- ═══════════════════════════════════════════════════════════════
    uniform_score           UInt8 DEFAULT 0,
    cleanliness_score       UInt8 DEFAULT 0,
    safety_score            UInt8 DEFAULT 0,
    hygiene_score           UInt8 DEFAULT 0,
    overall_score           UInt8 DEFAULT 0,

    -- ═══════════════════════════════════════════════════════════════
    -- BEHAVIORAL KPIs (Int8: 1=Yes, 0=No, -1=N/A)
    -- ═══════════════════════════════════════════════════════════════
    customer_present        UInt8 DEFAULT 0,
    greeting_detected       Int8 DEFAULT -1,
    show_zero_detected      Int8 DEFAULT -1,
    customer_left_unfueled  Int8 DEFAULT -1,
    mobile_phone_use        Int8 DEFAULT -1,    -- FSM distracted by phone

    -- ═══════════════════════════════════════════════════════════════
    -- COUNTS
    -- ═══════════════════════════════════════════════════════════════
    people_count            UInt8 DEFAULT 0,
    staff_count             UInt8 DEFAULT 0,
    customer_count          UInt8 DEFAULT 0,
    vehicle_count           UInt8 DEFAULT 0,
    active_pumps            UInt8 DEFAULT 0,
    media_analyzed          UInt8 DEFAULT 0,

    -- ═══════════════════════════════════════════════════════════════
    -- VEHICLE DATA (Arrays)
    -- ═══════════════════════════════════════════════════════════════
    `vehicles.type` Array(LowCardinality(String)) DEFAULT [],
    `vehicles.plate` Array(String) DEFAULT [],
    `vehicles.confidence` Array(Float32) DEFAULT [],

    -- ═══════════════════════════════════════════════════════════════
    -- STATUS & CLASSIFICATION
    -- ═══════════════════════════════════════════════════════════════
    status LowCardinality(String),
    utilization LowCardinality(String),
    event_triggers Array(LowCardinality(String)) DEFAULT [],

    -- ═══════════════════════════════════════════════════════════════
    -- AI OUTPUTS
    -- ═══════════════════════════════════════════════════════════════
    ai_summary              String,

    -- ═══════════════════════════════════════════════════════════════
    -- AGGREGATES
    -- ═══════════════════════════════════════════════════════════════
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
    
    # 5 Core SOP Triggers
    "sop_manned_air": {"type": "Int8", "description": "Air station has attendant (1=Pass, 0=Fail, -1=N/A)"},
    "sop_greeting": {"type": "Int8", "description": "Namaste greeting detected (1=Pass, 0=Fail, -1=N/A)"},
    "sop_uniform": {"type": "Int8", "description": "Uniform score >= 0.7 (1=Pass, 0=Fail, -1=N/A)"},
    "sop_unauthorized": {"type": "Int8", "description": "Unauthorized activity detected (1=Yes, 0=No)"},
    "sop_cleanliness": {"type": "Int8", "description": "Cleanliness score >= 0.7 (1=Pass, 0=Fail, -1=N/A)"},
    
    # Safety KPIs
    "du_cover_open": {"type": "Int8", "description": "DU cover open (1=Issue, 0=Clear, -1=Not Assessed)"},
    "manhole_open": {"type": "Int8", "description": "Manhole open (1=Issue, 0=Clear, -1=Not Assessed)"},
    "fuel_plastic_bottle": {"type": "Int8", "description": "Fuel in plastic bottle (1=Issue, 0=Clear, -1=Not Assessed)"},
    "foreign_objects": {"type": "Int8", "description": "Foreign objects detected (1=Issue, 0=Clear, -1=Not Assessed)"},
    "smoking_detected": {"type": "Int8", "description": "Smoking detected (1=Issue, 0=Clear, -1=Not Assessed)"},
    "fire_detected": {"type": "Int8", "description": "Fire detected (1=Issue, 0=Clear, -1=Not Assessed)"},
    "fight_detected": {"type": "Int8", "description": "Fight detected (1=Issue, 0=Clear, -1=Not Assessed)"},
    "mob_gathering": {"type": "Int8", "description": "Mob gathering detected (1=Issue, 0=Clear, -1=Not Assessed)"},
    "unauthorized_area": {"type": "Int8", "description": "Person in no-entry zone (1=Issue, 0=Clear, -1=Not Assessed)"},
    
    # Operations KPIs
    "fsm_present": {"type": "Int8", "description": "FSM present (1=Present, 0=Absent, -1=N/A)"},
    "manned_air_filling": {"type": "Int8", "description": "Air filling manned (1=Present, 0=Absent, -1=N/A)"},
    "five_liter_testing": {"type": "Int8", "description": "5-liter testing (1=Present, 0=Absent, -1=N/A)"},
    "five_liter_returned": {"type": "Int8", "description": "5-liter returned (1=Present, 0=Absent, -1=N/A)"},
    
    # Score-based KPIs
    "uniform_score": {"type": "UInt8", "description": "Uniform compliance score (0-10)"},
    "cleanliness_score": {"type": "UInt8", "description": "Cleanliness compliance score (0-10)"},
    "safety_score": {"type": "UInt8", "description": "Safety compliance score (0-10)"},
    "hygiene_score": {"type": "UInt8", "description": "Hygiene compliance score (0-10)"},
    "overall_score": {"type": "UInt8", "description": "Overall compliance score (0-10)"},
    
    # Behavioral KPIs
    "customer_present": {"type": "UInt8", "description": "Customer present count"},
    "greeting_detected": {"type": "Int8", "description": "Greeting detected (1=Yes, 0=No, -1=N/A)"},
    "show_zero_detected": {"type": "Int8", "description": "Show zero detected (1=Yes, 0=No, -1=N/A)"},
    "customer_left_unfueled": {"type": "Int8", "description": "Customer left unfueled (1=Yes, 0=No, -1=N/A)"},
    "mobile_phone_use": {"type": "Int8", "description": "FSM using mobile phone (1=Yes, 0=No, -1=N/A)"},
    
    # Counts
    "people_count": {"type": "UInt8", "description": "Total people count"},
    "staff_count": {"type": "UInt8", "description": "Staff count"},
    "customer_count": {"type": "UInt8", "description": "Customer count"},
    "vehicle_count": {"type": "UInt8", "description": "Vehicle count"},
    "active_pumps": {"type": "UInt8", "description": "Active pumps count"},
    "media_analyzed": {"type": "UInt8", "description": "Media files analyzed count"},
    
    # Vehicle Data
    "vehicles.type": {"type": "Array(LowCardinality(String))", "description": "Vehicle types array"},
    "vehicles.plate": {"type": "Array(String)", "description": "Vehicle plates array"},
    "vehicles.confidence": {"type": "Array(Float32)", "description": "Vehicle detection confidence array"},
    
    # Status & Classification
    "status": {"type": "LowCardinality(String)", "description": "Event status"},
    "utilization": {"type": "LowCardinality(String)", "description": "Station utilization level"},
    "event_triggers": {"type": "Array(LowCardinality(String))", "description": "Event trigger types"},
    
    # AI Outputs
    "ai_summary": {"type": "String", "description": "AI-generated summary"},
    
    # Aggregates
    "items_needing_attention": {"type": "UInt8", "description": "Count of items needing attention"},
    "safety_issues_count": {"type": "UInt8", "description": "Count of safety issues"},
    "compliance_issues_count": {"type": "UInt8", "description": "Count of compliance issues"},
}
