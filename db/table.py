# table.py

VIDEO_ANALYTICS_LOGS_TABLE = """
CREATE TABLE IF NOT EXISTS video_analytics_logs (
    -- Primary identifiers
    event_id UUID DEFAULT generateUUIDv4(),
    cam_id UInt16,
    cam_name LowCardinality(String),
    site_name LowCardinality(String),
    site_id String,
    
    -- Geo-Location
    latitude Float64 DEFAULT 0,
    longitude Float64 DEFAULT 0,
    country LowCardinality(String),
    state LowCardinality(String),
    district LowCardinality(String),
    
    -- Event metrics
    detection_count UInt16 DEFAULT 0,
    people_count UInt16 DEFAULT 0,
    video_count UInt16 DEFAULT 0,
    image_count UInt16 DEFAULT 0,
    
    -- Event classification
    event_type Enum8('metric' = 1, 'event' = 2, 'ai-info'=3),
    event_status Enum8('safe' = 1, 'warning' = 2, 'critical' = 3, 'emergency' = 4,'triaged' = 5),
    
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
    `detections.object_id` Array(UInt16) DEFAULT [],
    
    -- Event triggers
    event_triggers Array(LowCardinality(String)) DEFAULT [],

    -- Triage and AI
    triaged_by LowCardinality(String),
    triage_notes String,
    triage_timestamp UInt16,
    ai_insights String,
    evidence_path String,

    -- Recognition Data
    display_label Array(LowCardinality(String)) DEFAULT [],
    `recognition.identity` Array(LowCardinality(String)) DEFAULT [],
    `recognition.confidence` Array(Float32) DEFAULT [],
    `recognition.identity_id` Array(UInt32) DEFAULT [],
    
    -- [UPDATED] Auto-calculated columns that ARE visible in the table
    event_trigger_count UInt8 DEFAULT length(event_triggers),
    high_confidence_count UInt16 DEFAULT arrayCount(x -> x > 0.7, `detections.confidence`),
    
    -- Indexes
    INDEX idx_cam_id cam_id TYPE minmax GRANULARITY 4,
    INDEX idx_event_status event_status TYPE set(4) GRANULARITY 4,
    INDEX idx_site_name site_name TYPE bloom_filter(0.01) GRANULARITY 4,
    INDEX idx_cam_name cam_name TYPE bloom_filter(0.01) GRANULARITY 4
    
) ENGINE = MergeTree()
PARTITION BY toYYYYMMDD(toDateTime(event_timestamp))
ORDER BY (site_name, cam_id, event_timestamp, event_id)
SETTINGS index_granularity = 8192
"""

SCHEMAS = [
    ("video_analytics_logs", VIDEO_ANALYTICS_LOGS_TABLE, False)
]

# Column metadata for documentation/validation
COLUMN_METADATA = {
    "event_id": {"type": "UUID", "description": "Unique event identifier", "pk": True},
    "cam_id": {"type": "UInt16", "description": "Camera identifier", "pk": True},
    "cam_name": {"type": "LowCardinality(String)", "description": "Camera name"},
    "site_name": {"type": "LowCardinality(String)", "description": "Site/location name", "pk": True},
    "site_id": {"type": "String", "description": "Site ID"},
    "latitude": {"type": "Float64", "description": "Latitude"},
    "longitude": {"type": "Float64", "description": "Longitude"},
    "country": {"type": "String", "description": "Country"},
    "state": {"type": "String", "description": "State"},
    "district": {"type": "String", "description": "District"},
    "detection_count": {"type": "UInt16", "description": "Total detections in frame"},
    "people_count": {"type": "UInt16", "description": "Number of people detected"},
    "video_count": {"type": "UInt16", "description": "Number of videos captured"},
    "image_count": {"type": "UInt16", "description": "Number of images captured"},
    "event_type": {"type": "Enum8", "description": "Event type (metric=1, event=2, ai-info=3)"},
    "event_status": {"type": "Enum8", "description": "Event status (safe=1, warning=2, critical=3, emergency=4, triaged=5)"},
    "capture_triggered": {"type": "Bool", "description": "Whether capture was triggered"},
    "processed_at": {"type": "UInt16", "description": "Timestamp of processing"},
    "event_timestamp": {"type": "UInt16", "description": "Timestamp of event", "partition": True},
    "detections.*": {"type": "Array", "description": "Nested detection arrays"},
    "detections.object_id": {"type": "Array(String)", "description": "Object IDs for detections"},
    "triaged_by": {"type": "String", "description": "User who triaged the event"},
    "triage_notes": {"type": "String", "description": "Notes from triage"},
    "ai_insights": {"type": "String", "description": "AI generated insights"},
    "evidence_path": {"type": "String", "description": "Path to evidence file"},
    "event_trigger_count": {"type": "UInt8", "description": "Auto-calculated: length(event_triggers)"},
    "high_confidence_count": {"type": "UInt16", "description": "Auto-calculated: count where confidence > 0.7"},
    "display_label": {"type": "LowCardinality(String)", "description": "Display label for the event"},
    "recognition.identity": {"type": "LowCardinality(String)", "description": "Recognized identity name"},
    "recognition.confidence": {"type": "Float32", "description": "Confidence score of recognition"},
    "recognition.identity_id": {"type": "UInt32", "description": "ID of the recognized identity"},
}