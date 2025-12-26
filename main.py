from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from clickhouse_connect.driver import Client
from datetime import datetime
from typing import Dict, Any, List
from services.vector_services import _send_event_to_vector, _load_camera_logs, _process_results,transformer
from services.events_services import process_camera_events, get_recent_events
from config import get_settings
from db.connection import get_clickhouse, ClickHouseConnection
from db.schemas import HealthResponse, CameraEventRequest
from middleware import log_requests_middleware, global_exception_handler
import requests
import json
import os


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
    return get_recent_events()

@app.post("/events")
def process_events(
    events: List[CameraEventRequest], 
    client: Client = Depends(get_clickhouse)
):
    """
    High-performance batch insert for Camera Events.
    """
    return process_camera_events(events, client)


# Vector Trigger

@app.post("/vector")
def trigger_vector_pipeline(client: Client = Depends(get_clickhouse)):
    """
    Trigger Vector pipeline by sending events from camera_logs.json to Vector.
    Similar to send_to_vector.py but as an API endpoint.
    """
    try:
        events = _load_camera_logs()
        
        if not events:
            return {"success": True, "message": "No events to process", "results": []}
        
        # Process all events
        results = [_send_event_to_vector(event, i) for i, event in enumerate(events)]
        success_count, error_count = _process_results(results)
        
        # Convert dataclass to dict for JSON response
        results_dict = [
            {
                "event_index": r.event_index,
                **r.enriched_data,
                **({"error": r.error} if r.error else {})
            }
            for r in results
        ]

        transformed_data = transformer.transform({"results": results_dict})
        # Convert to Pydantic models and insert into ClickHouse
        camera_events = [CameraEventRequest(**item) for item in transformed_data]
        db_response = process_camera_events(camera_events, client)
        
        return {
            "success": True,
            "total_events": len(events),
            "success_count": success_count,
            "error_count": error_count,
            "transformed_data": transformed_data,
            "db_response": db_response
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to trigger Vector pipeline: {str(e)}"
        )