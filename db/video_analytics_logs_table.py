VIDEO_ANALYTICS_LOGS_TABLE = """
CREATE TABLE IF NOT EXISTS video_analytics_logs (
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
    
    -- Event metrics
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
    `detections.model_id` Array(UInt8) DEFAULT [],
    `detections.track_id` Array(UInt32) DEFAULT [],
    `detections.dwell_time` Array(Float32) DEFAULT [],
    `detections.filled` Array(UInt8) DEFAULT [],
    
    -- LPR (License Plate Recognition) Data
    `lpr.rc_no` Array(String) DEFAULT [],
    `lpr.track_id` Array(UInt32) DEFAULT [],
    `lpr.confidence` Array(Float32) DEFAULT [],
    `lpr.identity_id` Array(UInt32) DEFAULT [],
    
    -- Event triggers
    event_triggers Array(LowCardinality(String)) DEFAULT [],

    -- Triage and AI
    triaged_by LowCardinality(String),
    triage_notes String,
    triage_timestamp UInt32,
    ai_insights String,
    evidence_path String,
    event_accuracy_score Float32 DEFAULT 0,

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
ORDER BY (site_name, cam_id, event_timestamp, row_id)
SETTINGS index_granularity = 8192
"""

SCHEMAS = [
    ("video_analytics_logs", VIDEO_ANALYTICS_LOGS_TABLE, False)
]

