SYSTEM_HEALTH_TABLE = """
CREATE TABLE IF NOT EXISTS system_health (
    -- Primary Identifiers
    row_id              UUID DEFAULT generateUUIDv4(),
    company_id          String,
    device_id           String,
    site_id             String,
    site_name           LowCardinality(String),
    event_timestamp     UInt32,

    -- Geo-Location (Current vs Registered)
    latitude           Float64, -- Current GPS from device IP
    longitude          Float64, -- Current GPS from device IP
    reg_latitude       Float64, -- Hardcoded registered lat from mongoDB
    reg_longitude      Float64, -- Hardcoded registered lon from mongoDB
    device_ip_local    String, -- Local IP of the device
    device_ip_public   String, -- Public IP of the device
    country            LowCardinality(String),
    state              LowCardinality(String),
    district           LowCardinality(String),
    city               LowCardinality(String),

    -- Network & Performance
    primary_internet_speed   Float32, -- Mbps
    secondary_internet_speed Float32, -- Mbps
    cpu_usage_percent        Float32,
    ram_usage_percent        Float32,
    device_status            Enum8('online' = 1, 'offline' = 2, 'error' = 3, 'restart' = 4),

    -- Nested Camera Status (Parallel Arrays)
    -- This allows 1 device to report N cameras in one row
    `cameras.cam_id`         Array(String),
    `cameras.cam_name`       Array(String),
    `cameras.zone_names`     Array(Array(String)),
    `cameras.status`         Array(Enum8('online' = 1, 'offline' = 2, 'error' = 3, 'restart' = 4)),
    `cameras.fps`            Array(Float32) -- Optional: helpful to see if stream is laggy

) ENGINE = MergeTree()
PARTITION BY toYYYYMMDD(toDateTime(event_timestamp))
ORDER BY (company_id, site_id, device_id, event_timestamp)
"""

SCHEMAS = [
    ("system_health", SYSTEM_HEALTH_TABLE, False)
]

