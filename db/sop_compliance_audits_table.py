SOP_COMPLIANCE_AUDITS_TABLE = """
CREATE TABLE IF NOT EXISTS sop_compliance_audits (
    -- 1. Metadata & Identifiers
    event_id            UUID DEFAULT generateUUIDv4(),
    site_id             String,
    site_name           LowCardinality(String),
    cam_id              UInt16,
    cam_name            LowCardinality(String),
    event_timestamp     DateTime,

    -- 2. Geo-Location
    latitude            Float64 DEFAULT 0,
    longitude           Float64 DEFAULT 0,
    country             LowCardinality(String),
    state               LowCardinality(String),
    district            LowCardinality(String),

    -- 3. Safety Violation Flags (0 = Safe, 1 = Violation)
    du_cover_open       UInt8 DEFAULT 0,
    manhole_open        UInt8 DEFAULT 0,
    fuel_plastic_bottle UInt8 DEFAULT 0,
    foreign_objects     UInt8 DEFAULT 0,

    -- 4. Quality & Behavioral KPIs (Using Nullable)
    uniform_score       Nullable(Float32),
    hygiene_score       Nullable(Float32),
    cleanliness_score   Nullable(Float32),

    -- Behavioral: 1 = Success, 0 = Fail, NULL = No Opportunity
    greeting_detected   Nullable(UInt8),
    show_zero_detected  Nullable(UInt8),

    -- 5. Contextual Data
    ai_summary          String,
    evidence_path       String,

    -- 6. Dashboard Aggregates
    items_needing_attention UInt8

) ENGINE = ReplacingMergeTree()
PARTITION BY toYYYYMM(event_timestamp)
ORDER BY (site_id, event_timestamp, cam_id)
"""

SCHEMAS = [
    ("sop_compliance_audits", SOP_COMPLIANCE_AUDITS_TABLE, False)
]

# Column metadata for documentation/validation
COLUMN_METADATA = {
    "event_id": {"type": "UUID", "description": "Unique event identifier", "pk": True},
    "site_id": {"type": "String", "description": "Unique site ID"},
    "site_name": {"type": "LowCardinality(String)", "description": "Site/location name"},
    "cam_id": {"type": "UInt16", "description": "Camera identifier", "pk": True},
    "cam_name": {"type": "LowCardinality(String)", "description": "Camera name"},
    "event_timestamp": {"type": "DateTime", "description": "Timestamp of event", "partition": True},
    "latitude": {"type": "Float64", "description": "Latitude coordinate"},
    "longitude": {"type": "Float64", "description": "Longitude coordinate"},
    "country": {"type": "LowCardinality(String)", "description": "Country"},
    "state": {"type": "LowCardinality(String)", "description": "State"},
    "district": {"type": "LowCardinality(String)", "description": "District"},
    "du_cover_open": {"type": "UInt8", "description": "DU cover open violation flag (0 = Safe, 1 = Violation)"},
    "manhole_open": {"type": "UInt8", "description": "Manhole open violation flag (0 = Safe, 1 = Violation)"},
    "fuel_plastic_bottle": {"type": "UInt8", "description": "Fuel plastic bottle violation flag (0 = Safe, 1 = Violation)"},
    "foreign_objects": {"type": "UInt8", "description": "Foreign objects violation flag (0 = Safe, 1 = Violation)"},
    "uniform_score": {"type": "Nullable(Float32)", "description": "Uniform compliance score (0.0 to 1.0)"},
    "hygiene_score": {"type": "Nullable(Float32)", "description": "Hygiene compliance score (0.0 to 1.0)"},
    "cleanliness_score": {"type": "Nullable(Float32)", "description": "Cleanliness compliance score (0.0 to 1.0)"},
    "greeting_detected": {"type": "Nullable(UInt8)", "description": "Greeting detected (1 = Success, 0 = Fail, NULL = No Opportunity)"},
    "show_zero_detected": {"type": "Nullable(UInt8)", "description": "Show zero detected (1 = Success, 0 = Fail, NULL = No Opportunity)"},
    "ai_summary": {"type": "String", "description": "Detailed reasoning from LLM"},
    "evidence_path": {"type": "String", "description": "URL to the 20s video or specific image"},
    "items_needing_attention": {"type": "UInt8", "description": "Count of violations (sum of binary flags where value = 1)"},
}
