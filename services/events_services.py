from typing import List, Dict, Any
from core.connection import get_clickhouse
from fastapi import HTTPException
from clickhouse_connect.driver import Client
from db.schemas import CameraEventRequest
from utils.constant import CH_COLUMNS
from utils.logger import get_logger

logger = get_logger(__name__)

# Store last 50 events for debugging
_last_events: List[Dict[str, Any]] = []


def get_recent_events() -> Dict[str, Any]:
    """Return the last processed events for debugging."""
    return {"count": len(_last_events), "events": _last_events}


def process_camera_events(events: List[CameraEventRequest]) -> Dict[str, Any]:
    """
    Process camera events and insert them into ClickHouse.
    """
    if not events:
        return {"processed": 0}

    rows = []
    
    try:
        company_id = None
        for evt in events:
            meta = evt.meta
            payload = evt.payload
            detections = payload.detections
            
            # 1. Pivot Detections for ClickHouse Arrays
            d_cids = [d.class_id or 0 for d in detections]
            d_lbls = [d.label or "" for d in detections]
            d_confs = [d.confidence or 0.0 for d in detections]
            d_left = [d.bbox[0] if d.bbox and len(d.bbox) > 0 else 0 for d in detections]
            d_top = [d.bbox[1] if d.bbox and len(d.bbox) > 1 else 0 for d in detections]
            d_width = [d.bbox[2] if d.bbox and len(d.bbox) > 2 else 0 for d in detections]
            d_height = [d.bbox[3] if d.bbox and len(d.bbox) > 3 else 0 for d in detections]
            d_object_ids = [d.object_id or 0 for d in detections]
            
            # Extract recognition data from detections
            display_labels = [d.display_label or "" for d in detections]
            rec_identities = [d.recognition.get("identity", "") if d.recognition else "" for d in detections]
            rec_confidences = [d.recognition.get("confidence", 0.0) if d.recognition else 0.0 for d in detections]
            rec_identity_ids = [d.recognition.get("identity_id", 0) if d.recognition else 0 for d in detections]

            company_id = str(meta.company_id) if meta.company_id else None

            # 2. Build Row (ensure no None values)
            row = [
                str(meta.company_id) if meta.company_id else "",
                str(meta.device_id) if meta.device_id else "",
                meta.cam_id or 0,
                meta.cam_name or "Unknown",
                meta.site_name or "",
                meta.site_id or "",
                meta.zone_name,  # Mandatory field
                meta.latitude or 0.0,
                meta.longitude or 0.0,
                meta.country or "",
                meta.state or "",
                meta.district or "",
                len(detections),          
                payload.people_count or 0,
                payload.video_count or 0,
                payload.image_count or 0,
                evt.type or "metric",                 
                payload.status or "safe",              
                payload.capture_triggered or False,
                int(evt.processed_at or 0),
                int(meta.ts or 0),             
                d_cids,
                d_lbls,
                d_confs,
                d_left,
                d_top,
                d_width,
                d_height,
                d_object_ids,
                payload.triggers or [],
                payload.triaged_by or "",
                payload.triage_notes or "",
                int(payload.triage_timestamp or 0),
                payload.ai_insights or "",
                payload.evidence_path or "",
                display_labels,
                rec_identities,
                rec_confidences,
                rec_identity_ids
            ]
            rows.append(row)

        # 3. Batch Insert
        client = get_clickhouse(company_id)
        client.insert(
            'video_analytics_logs',
            rows,
            column_names=CH_COLUMNS
        )

        # 4. Update Debug Log
        global _last_events
        new_event_dicts = [e.model_dump() for e in events] 
        _last_events = (new_event_dicts + _last_events)[:50]

        logger.info(f"Successfully inserted {len(rows)} events")

        return {
            "success": True, 
            "inserted": len(rows),
        }

    except Exception as e:
        logger.error(f"Insert Error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Database Insert Failed: {str(e)}")