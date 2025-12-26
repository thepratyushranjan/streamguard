from fastapi import APIRouter, HTTPException, Depends
from app.models.schemas import CameraEventRequest, EventData
from app.services.clickhouse import get_clickhouse
from clickhouse_connect.driver import Client
from datetime import datetime
from app.services.websocket import manager
import json

router = APIRouter()

@router.post("/events")
async def ingest_event(
    event: CameraEventRequest,
    client: Client = Depends(get_clickhouse)
):
    try:
        # 1. Process Data
        # Flatten structure for ClickHouse
        # Schema: (site, cam_id, cam_name, event_timestamp, event_type, event_status, 
        #          event_triggers, detections.label, detections.confidence, detections.bbox, people_count)
        
        payload = event.payload
        
        # Prepare arrays for detections - flatten for ClickHouse Nested-like structure
        det_class_ids = []
        det_labels = []
        det_confs = []
        det_lefts = []
        det_tops = []
        det_widths = []
        det_heights = []
        
        for det in payload.detections:
            det_class_ids.append(det.class_id)
            det_labels.append(det.label)
            det_confs.append(det.confidence)
            # bbox is [left, top, width, height]
            if det.bbox and len(det.bbox) == 4:
                det_lefts.append(int(det.bbox[0]))
                det_tops.append(int(det.bbox[1]))
                det_widths.append(int(det.bbox[2]))
                det_heights.append(int(det.bbox[3]))
            else:
                det_lefts.append(0)
                det_tops.append(0)
                det_widths.append(0)
                det_heights.append(0)

        # 2. Insert into ClickHouse
        # Columns based on db/table.py
        
        row = [
            event.meta.cam_id,
            event.meta.cam_name or "Unknown",
            event.meta.site,
            len(det_labels), # detection_count
            payload.people_count,
            event.type, # event_type Enum
            event.meta.status, # event_status Enum
            payload.capture_triggered,
            int(event.processed_at),
            int(event.meta.ts),
            det_class_ids,
            det_labels,
            det_confs,
            det_lefts,
            det_tops,
            det_widths,
            det_heights,
            payload.triggers
        ]
        
        client.insert('camera_events', [row], column_names=[
            'cam_id', 'cam_name', 'site', 
            'detection_count', 'people_count', 
            'event_type', 'event_status', 
            'capture_triggered', 'processed_at', 'event_timestamp',
            'detections.class_id', 'detections.label', 'detections.confidence',
            'detections.bbox_left', 'detections.bbox_top', 'detections.bbox_width', 'detections.bbox_height',
            'event_triggers'
        ])
        
        # 3. WebSocket Broadcast
        # Broadcast to specific site room
        ws_message = {
            "type": "ALERT" if event.meta.status != "SAFE" else "UPDATE",
            "data": event.dict()
        }
        await manager.broadcast(ws_message, event.meta.site)
        
        return {"status": "ok", "id": f"{event.meta.site}_{event.meta.ts}"}
        
    except Exception as e:
        print(f"Error processing event: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/last-events")
def get_last_events(limit: int = 10, client: Client = Depends(get_clickhouse)):
    # Debug endpoint
    query = f"""
    SELECT * FROM camera_events ORDER BY event_timestamp DESC LIMIT {limit}
    """
    result = client.query(query)
    return {"columns": result.column_names, "data": result.result_rows}
