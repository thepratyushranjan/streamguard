from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from clickhouse_connect.driver import Client
from datetime import datetime
from typing import List, Dict, Any

from config import get_settings
from db.connection import get_clickhouse, ClickHouseConnection
from db.schemas import HealthResponse
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


@app.post("/events")
async def process_events(request: Request):
    """Receive events from Vector"""
    try:
        events = await request.json()
        
        if not isinstance(events, list):
            events = [events]
        
        processed = []
        for event in events:
            meta = event.get("meta", {})
            event_type = event.get("type")
            
            result = {
                "cam_id": meta.get("cam_id"),
                "site": meta.get("site"),
                "status": meta.get("status"),
                "event_type": event_type,
                "timestamp": meta.get("ts"),
                "processed_at": event.get("processed_at")
            }
            
            if event_type == "METRIC":
                data = event.get("data", {})
                result["people_count"] = data.get("people_count", 0)
                result["detections_count"] = len(data.get("detections", []))
            elif event_type == "EVENT":
                evt = event.get("event", {})
                result["people_count"] = evt.get("people_count", 0)
                result["detections_count"] = len(evt.get("detections", []))
                result["triggers"] = evt.get("triggers", [])
                result["capture_triggered"] = evt.get("capture_triggered", False)
            
            processed.append(result)
        
        response = {
            "success": True,
            "events_processed": len(processed),
            "events": processed
        }
        
        # Store last 10 events for debugging
        global last_events
        last_events = (last_events + processed)[-10:]
        
        print(f"✓ Processed {len(processed)} events: {[e['cam_id'] for e in processed]}")
        return response
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error: {str(e)}")