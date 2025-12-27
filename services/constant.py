# Vector Constants
VECTOR_REQUEST_TIMEOUT = 5
HTTP_OK = 200

# ClickHouse Constants
CH_COLUMNS = [
    'cam_id', 'cam_name', 'site', 
    'detection_count', 'people_count', 
    'event_type', 'event_status', 
    'capture_triggered', 'processed_at', 'event_timestamp',
    'detections.class_id', 'detections.label', 'detections.confidence',
    'detections.bbox_left', 'detections.bbox_top', 'detections.bbox_width', 'detections.bbox_height',
    'event_triggers',
    'display_label',
    'recognition.identity', 'recognition.confidence', 'recognition.identity_id'
]