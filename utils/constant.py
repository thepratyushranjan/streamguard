# Vector Constants
VECTOR_REQUEST_TIMEOUT = 5
HTTP_OK = 200

# ClickHouse Constants
CH_COLUMNS = [
    'company_id', 'device_id',
    'cam_id', 'cam_name', 'site_name', 'site_id', 'zone_name',
    'latitude', 'longitude', 'country', 'state', 'district',
    'detection_count', 'people_count', 'video_count', 'image_count',
    'event_type', 'event_status', 
    'capture_triggered', 'processed_at', 'event_timestamp',
    'detections.class_id', 'detections.label', 'detections.confidence',
    'detections.bbox_left', 'detections.bbox_top', 'detections.bbox_width', 'detections.bbox_height',
    'detections.object_id',
    'event_triggers',
    'triaged_by', 'triage_notes', 'triage_timestamp', 'ai_insights', 'evidence_path',
    'display_label',
    'recognition.identity', 'recognition.confidence', 'recognition.identity_id'
]