# table.py

CAMERA_EVENTS_TABLE = """
CREATE TABLE IF NOT EXISTS camera_events (
    -- Primary identifiers
    cam_id UInt16,
    cam_name LowCardinality(String),
    site LowCardinality(String),
    
    -- Event metrics
    detection_count UInt16 DEFAULT 0,
    people_count UInt16 DEFAULT 0,
    
    -- Event classification
    event_type Enum8('METRIC' = 1, 'EVENT' = 2),
    event_status Enum8('SAFE' = 1, 'WARNING' = 2, 'CRITICAL' = 3),
    
    -- Flags and timestamps
    capture_triggered Bool DEFAULT false,
    processed_at UInt32,
    event_timestamp UInt32,
    
    -- Nested detection arrays
    `detections.class_id` Array(UInt8) DEFAULT [],
    `detections.label` Array(LowCardinality(String)) DEFAULT [],
    `detections.confidence` Array(Float32) DEFAULT [],
    `detections.bbox_left` Array(UInt16) DEFAULT [],
    `detections.bbox_top` Array(UInt16) DEFAULT [],
    `detections.bbox_width` Array(UInt16) DEFAULT [],
    `detections.bbox_height` Array(UInt16) DEFAULT [],
    
    -- Event triggers
    event_triggers Array(LowCardinality(String)) DEFAULT [],
    
    -- [UPDATED] Auto-calculated columns that ARE visible in the table
    event_trigger_count UInt8 DEFAULT length(event_triggers),
    high_confidence_count UInt16 DEFAULT arrayCount(x -> x > 0.7, `detections.confidence`),
    
    -- Indexes
    INDEX idx_cam_id cam_id TYPE minmax GRANULARITY 4,
    INDEX idx_event_status event_status TYPE set(4) GRANULARITY 4,
    INDEX idx_site site TYPE bloom_filter(0.01) GRANULARITY 4,
    INDEX idx_cam_name cam_name TYPE bloom_filter(0.01) GRANULARITY 4
    
) ENGINE = MergeTree()
PARTITION BY toYYYYMMDD(toDateTime(event_timestamp))
ORDER BY (site, cam_id, event_timestamp)
SETTINGS index_granularity = 8192
"""

SCHEMAS = [
    ("camera_events", CAMERA_EVENTS_TABLE, False)
]

# Column metadata for documentation/validation
COLUMN_METADATA = {
    "cam_id": {"type": "UInt16", "description": "Camera identifier", "pk": True},
    "cam_name": {"type": "LowCardinality(String)", "description": "Camera name"},
    "site": {"type": "LowCardinality(String)", "description": "Site/location", "pk": True},
    "detection_count": {"type": "UInt16", "description": "Total detections in frame"},
    "people_count": {"type": "UInt16", "description": "Number of people detected"},
    "event_type": {"type": "Enum8", "description": "METRIC=1, EVENT=2"},
    "event_status": {"type": "Enum8", "description": "SAFE=1, WARNING=2, CRITICAL=3"},
    "capture_triggered": {"type": "Bool", "description": "Whether capture was triggered"},
    "processed_at": {"type": "UInt32", "description": "Unix timestamp of processing"},
    "event_timestamp": {"type": "UInt32", "description": "Unix timestamp of event", "partition": True},
    "detections.*": {"type": "Array", "description": "Nested detection arrays"},
    "high_confidence_count": {"type": "UInt16", "description": "MATERIALIZED: count where confidence > 0.7"},
    "event_trigger_count": {"type": "UInt8", "description": "Auto-calculated: length(event_triggers)"},
    "high_confidence_count": {"type": "UInt16", "description": "Auto-calculated: count where confidence > 0.7"},
}