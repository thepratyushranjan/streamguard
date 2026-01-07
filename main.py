from fastapi import FastAPI, HTTPException, Request, Depends, BackgroundTasks
import os
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from clickhouse_connect.driver import Client
from datetime import datetime
from typing import Dict, Any, List, Union
from services.vector_services import transformer, extract_enriched_data
from services.events_services import process_camera_events, get_recent_events
from services.validation_service import validation_service
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


@app.on_event("startup")
async def startup():
    """Test connection on startup and initialize services"""
    if ClickHouseConnection.test_connection():
        print(f"✓ Connected to ClickHouse at {settings.clickhouse_host}:{settings.clickhouse_port}")
    else:
        print("✗ Failed to connect to ClickHouse")
    
    # Initialize validation service HTTP client
    await validation_service.initialize()
    print("✓ FastAPI started - ready to receive events from Vector")


@app.on_event("shutdown")
async def shutdown():
    """Close connections on shutdown"""
    await validation_service.shutdown()
    ClickHouseConnection.close()
    print("✓ ClickHouse connection closed")


# Vector Trigger

@app.post("/vector")
async def trigger_vector_pipeline(
    events: Union[List[Dict[str, Any]], Dict[str, Any]], 
    client: Client = Depends(get_clickhouse)
):
    """
    Trigger Vector pipeline by receiving events directly in body.
    """
    try:
        # Normalize single event to list
        if isinstance(events, dict):
            events = [events]
            
        if not events:
            return {"success": True, "message": "No events to process", "results": []}
        
        # Process all events
        results_dict = [
            {
                "event_index": i + 1,
                **extract_enriched_data(event)
            }
            for i, event in enumerate(events)
        ]
        print(f'''payload_input: {results_dict}''')
        transformed_data = transformer.transform({"results": results_dict})
        print(f'''payload_transformed: {transformed_data}''')

        # Schedule async validation tasks (fire-and-forget, non-blocking)
        # Only validate events with type "event" or "ai-info"
        if transformed_data and transformed_data[0].get("type", "").lower() in ("event", "ai-info"):
            validation_service.schedule_validation_tasks(transformed_data)
            
        # Convert to Pydantic models and insert into ClickHouse
        camera_events = [CameraEventRequest(**item) for item in transformed_data]
        db_response = process_camera_events(camera_events, client)
        
        return {
            "success": True,
            "total_events": len(events),
            "db_response": db_response
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process vector pipeline: {str(e)}"
        )