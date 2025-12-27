from typing import List, Dict, Any
from fastapi import HTTPException
from clickhouse_connect.driver import Client
from db.schemas import CameraEventRequest
from services.constant import CH_COLUMNS

# Store last 50 events for debugging
_last_events: List[Dict[str, Any]] = []

def get_recent_events() -> Dict[str, Any]:
    """Return the last processed events for debugging."""
    return {"count": len(_last_events), "events": _last_events}

def process_camera_events(events: List[CameraEventRequest], client: Client) -> Dict[str, Any]:
    """
    Process camera events and insert them into ClickHouse.
    """
    if not events:
        return {"processed": 0}

    rows = []
    
    try:
        for evt in events:
            meta = evt.meta
            payload = evt.payload
            detections = payload.detections
            
            # 1. Pivot Detections for ClickHouse Arrays
            d_cids = [d.class_id for d in detections]
            d_lbls = [d.label for d in detections]
            d_confs = [d.confidence for d in detections]
            d_left = [d.bbox[0] for d in detections]
            d_top = [d.bbox[1] for d in detections]
            d_width = [d.bbox[2] for d in detections]
            d_height = [d.bbox[3] for d in detections]

            # 2. Build Row
            row = [
                meta.cam_id,
                meta.cam_name,
                meta.site,
                len(detections),          
                payload.people_count,
                evt.type,                 
                meta.status,              
                payload.capture_triggered,
                int(evt.processed_at),
                int(meta.ts),             
                d_cids,
                d_lbls,
                d_confs,
                d_left,
                d_top,
                d_width,
                d_height,
                payload.triggers,
                [r.display_label for r in payload.recognitions],
                [r.identity for r in payload.recognitions],
                [r.confidence for r in payload.recognitions],
                [r.identity_id for r in payload.recognitions]
            ]
            rows.append(row)

        # 3. Batch Insert
        client.insert(
            'camera_events',
            rows,
            column_names=CH_COLUMNS
        )

        # 4. Update Debug Log
        global _last_events
        new_event_dicts = [e.model_dump() for e in events] 
        _last_events = (new_event_dicts + _last_events)[:50]

        print(f"Successfully inserted {len(rows)} events.")

        return {
            "success": True, 
            "inserted": len(rows),
        }

    except Exception as e:
        print(f"Insert Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database Insert Failed: {str(e)}")