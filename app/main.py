from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.api import api_router
from app.core.config import get_settings
from app.services.websocket import manager
from app.services.clickhouse import ClickHouseConnection

settings = get_settings()

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# CORS Code
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # TODO: restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)

# Events Router (Root Level)
from app.api.v1.endpoints import events
app.include_router(events.router) # Mounts /events and /last-events at root

# Custom Middleware
from app.core.middleware import log_requests_middleware, global_exception_handler
app.middleware("http")(log_requests_middleware)
app.exception_handler(Exception)(global_exception_handler)

@app.on_event("startup")
async def startup_event():
    if ClickHouseConnection.test_connection():
        print(f"✓ Connected to ClickHouse")
    else:
        print(f"✗ Failed to connect to ClickHouse")

@app.on_event("shutdown")
async def shutdown_event():
    ClickHouseConnection.close()

# WebSocket Endpoint
@app.websocket(f"{settings.API_V1_STR}/ws/alerts")
async def websocket_endpoint(websocket: WebSocket, site_id: str):
    await manager.connect(websocket, site_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, site_id)

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "streamguard-api"}
