SYSTEM_HEALTH_TABLE = """
CREATE TABLE IF NOT EXISTS system_health (
    -- Primary Identifiers
    row_id              UUID DEFAULT generateUUIDv4(),
    company_id          String,
    device_id           String,
    site_id             String,
    site_name           LowCardinality(String),
    cam_id              UInt16,
    cam_name            LowCardinality(String),
    event_timestamp     DateTime,

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

    -- Network & Performance
    primary_internet_speed   Float32, -- Mbps
    secondary_internet_speed Float32, -- Mbps
    cpu_usage_percent        UInt8,
    ram_usage_percent        UInt8,
    device_status            Enum8('online' = 1, 'offline' = 2, 'error' = 3),

    -- Nested Camera Status (Parallel Arrays)
    -- This allows 1 device to report N cameras in one row
    `cameras.cam_id`   Array(UInt16),
    `cameras.status`   Array(Enum8('online' = 1, 'offline' = 2, 'error' = 3)),
    `cameras.fps`      Array(UInt8) -- Optional: helpful to see if stream is laggy

) ENGINE = MergeTree()
PARTITION BY toDate(event_timestamp)
ORDER BY (company_id, site_id, device_id, event_timestamp)
"""

SCHEMAS = [
    ("system_health", SYSTEM_HEALTH_TABLE, False)
]

# Column metadata for documentation/validation
COLUMN_METADATA = {
    "row_id": {"type": "UUID", "description": "Unique row identifier", "pk": True},
    "company_id": {"type": "String", "description": "Company identifier"},
    "device_id": {"type": "String", "description": "Device identifier"},
    "site_id": {"type": "String", "description": "Unique site ID"},
    "site_name": {"type": "LowCardinality(String)", "description": "Site/location name"},
    "cam_id": {"type": "UInt16", "description": "Camera identifier"},
    "cam_name": {"type": "LowCardinality(String)", "description": "Camera name"},
    "event_timestamp": {"type": "DateTime", "description": "Timestamp of event", "partition": True},
    "latitude": {"type": "Float64", "description": "Current GPS latitude from device IP"},
    "longitude": {"type": "Float64", "description": "Current GPS longitude from device IP"},
    "reg_latitude": {"type": "Float64", "description": "Registered latitude from MongoDB"},
    "reg_longitude": {"type": "Float64", "description": "Registered longitude from MongoDB"},
    "device_ip_local": {"type": "String", "description": "Local IP of the device"},
    "device_ip_public": {"type": "String", "description": "Public IP of the device"},
    "country": {"type": "LowCardinality(String)", "description": "Country"},
    "state": {"type": "LowCardinality(String)", "description": "State"},
    "district": {"type": "LowCardinality(String)", "description": "District"},
    "primary_internet_speed": {"type": "Float32", "description": "Primary internet speed in Mbps"},
    "secondary_internet_speed": {"type": "Float32", "description": "Secondary internet speed in Mbps"},
    "cpu_usage_percent": {"type": "UInt8", "description": "CPU usage percentage (0-100)"},
    "ram_usage_percent": {"type": "UInt8", "description": "RAM usage percentage (0-100)"},
    "device_status": {"type": "Enum8", "description": "Device status (online=1, offline=2, error=3)"},
    "cameras.cam_id": {"type": "Array(UInt16)", "description": "Array of camera IDs"},
    "cameras.status": {"type": "Array(Enum8)", "description": "Array of camera statuses (online=1, offline=2, error=3)"},
    "cameras.fps": {"type": "Array(UInt8)", "description": "Array of camera FPS values"},
}
