ATTENDANCE_RECORDS_TABLE = """
CREATE TABLE IF NOT EXISTS attendance_logs(
    -- METADATA

    -- Primary identifiers
    row_id UUID DEFAULT generateUUIDv4(),
    company_id String,
    device_id String,
    cam_id String,
    cam_name LowCardinality(String),
    site_name LowCardinality(String),
    site_id String,
    zone_names Array(String) DEFAULT [],
    
    -- Geo-Location
    latitude Float64 DEFAULT 0,
    longitude Float64 DEFAULT 0,
    country LowCardinality(String),
    state LowCardinality(String),
    district LowCardinality(String),
    city LowCardinality(String),

    -- Attendance Data
    event_type LowCardinality(String),
    person_name String,
    person_id UInt64,
    zone String,
    direction LowCardinality(String),
    confidence Float32 DEFAULT 0,
    track_id UInt32 DEFAULT 0,
    description String DEFAULT '',
    recorded_at UInt32,

    -- Secondary Indexes (Skip Indexes)
    INDEX idx_person_name person_name TYPE bloom_filter(0.01) GRANULARITY 4,
    INDEX idx_cam_id cam_id TYPE bloom_filter(0.01) GRANULARITY 4,
    INDEX idx_device_id device_id TYPE bloom_filter(0.01) GRANULARITY 4,
    INDEX idx_event_type event_type TYPE set(10) GRANULARITY 4,
    INDEX idx_zone zone TYPE set(100) GRANULARITY 4,
    INDEX idx_zone_names zone_names TYPE bloom_filter(0.01) GRANULARITY 4
)

ENGINE = MergeTree()
PARTITION BY toYYYYMM(toDateTime(recorded_at))
ORDER BY (company_id, site_id, person_id, recorded_at)
"""


SCHEMAS = [
    ("attendance_logs", ATTENDANCE_RECORDS_TABLE, False)
]
