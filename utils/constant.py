# Vector Constants
VECTOR_REQUEST_TIMEOUT = 5
HTTP_OK = 200

# Video Ingest Constants
CH_COLUMNS = [
    'company_id', 'device_id',
    'cam_id', 'cam_name', 'site_name', 'site_id', 'zone_names',
    'latitude', 'longitude', 'country', 'state', 'district', 'city',
    'video_count', 'image_count',
    'event_type', 'event_status', 
    'capture_triggered', 'processed_at', 'event_timestamp',
    'detections.class_id', 'detections.label', 'detections.confidence',
    'detections.bbox_left', 'detections.bbox_top', 'detections.bbox_width', 'detections.bbox_height',
    'detections.object_id', 'detections.model_id', 'detections.track_id',
    'detections.dwell_time', 'detections.filled',
    'lpr.rc_no', 'lpr.track_id', 'lpr.confidence', 'lpr.identity_id',
    'event_triggers',
    'triaged_by', 'triage_notes', 'triage_timestamp', 'ai_insights', 'evidence_path',
    'event_accuracy_score',
    'display_label',
    'recognition.identity', 'recognition.confidence', 'recognition.identity_id'
]


# Attendance Constants
ATTENDANCE_COLUMNS = [
    # Metadata
    'company_id', 'device_id', 'cam_id', 'cam_name',
    'site_name', 'site_id', 'zone_names',
    # Geo-Location
    'latitude', 'longitude', 'country', 'state', 'district', 'city',
    # Attendance Data
    'event_type', 'person_name', 'person_id', 'zone',
    'direction', 'confidence', 'track_id', 'description', 'recorded_at',
    'total_work_hours', 'workstation_absence',
]


