from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from clickhouse_connect.driver import Client
from datetime import datetime
from typing import List, Dict, Any

from config import get_settings
from db.connection import get_clickhouse, ClickHouseConnection
from db.schemas import HealthResponse, CameraEventRequest
from middleware import log_requests_middleware, global_exception_handler

app = FastAPI(title="FastAPI + ClickHouse", version="1.0.0")
settings = get_settings()

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Trusted Host Middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]
)

# Custom Middleware
app.middleware("http")(log_requests_middleware)
app.exception_handler(Exception)(global_exception_handler)

last_events = []


@app.on_event("startup")
async def startup():
    """Test connection on startup"""
    if ClickHouseConnection.test_connection():
        print(f"✓ Connected to ClickHouse at {settings.clickhouse_host}:{settings.clickhouse_port}")
    else:
        print("✗ Failed to connect to ClickHouse")
    print("✓ FastAPI started - ready to receive events from Vector")


@app.on_event("shutdown")
async def shutdown():
    """Close connection on shutdown"""
    ClickHouseConnection.close()
    print("✓ ClickHouse connection closed")


@app.get("/")
def root():
    return {
        "status": "running", 
        "service": "camera-event-processor",
        "database": settings.clickhouse_database
    }


@app.get("/health", response_model=HealthResponse)
def health_check(client: Client = Depends(get_clickhouse)):
    """Health check endpoint"""
    try:
        client.query("SELECT 1")
        return HealthResponse(
            status="healthy",
            clickhouse="connected",
            timestamp=datetime.now()
        )
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"ClickHouse unavailable: {str(e)}")



@app.get("/last-events")
def get_last_events():
    """Get last processed events for debugging"""
    return {"count": len(last_events), "events": last_events}


# Columns matching the Insert order
CH_COLUMNS = [
    'cam_id', 'cam_name', 'site', 
    'detection_count', 'people_count', 
    'event_type', 'event_status', 
    'capture_triggered', 'processed_at', 'event_timestamp',
    'detections.class_id', 'detections.label', 'detections.confidence',
    'detections.bbox_left', 'detections.bbox_top', 'detections.bbox_width', 'detections.bbox_height',
    'event_triggers'
]

@app.post("/events")
def process_events(
    events: List[CameraEventRequest], 
    client: Client = Depends(get_clickhouse)
):
    """
    High-performance batch insert for Camera Events.
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
                payload.triggers
            ]
            rows.append(row)

        # 3. Batch Insert
        client.insert(
            'camera_events',
            rows,
            column_names=CH_COLUMNS
        )

        # 4. Update Debug Log
        global last_events
        new_event_dicts = [e.model_dump() for e in events] 
        last_events = (new_event_dicts + last_events)[:50]

        print(f"Successfully inserted {len(rows)} events.")

        return {
            "success": True, 
            "inserted": len(rows),
            "cam_ids": [r[0] for r in rows]
        }

    except Exception as e:
        print(f"Insert Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database Insert Failed: {str(e)}")