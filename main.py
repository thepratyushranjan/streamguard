from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from api.routes import (
    root_router,
    health_router, 
    events_router,
    vector_router,
    vector_office_router,
    system_health_router,
    sop_compliance_router,
)
from core.config import get_settings
from core.connection import ClickHouseConnection
from services.validation_service import validation_service
from services.trigger_merge_service import trigger_merge_service
from core.middleware import log_requests_middleware, global_exception_handler
from utils.logger import get_logger

logger = get_logger(__name__)

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


# Include Routers
app.include_router(root_router)
app.include_router(health_router)
app.include_router(events_router)
app.include_router(vector_router)
app.include_router(vector_office_router)
app.include_router(system_health_router)
app.include_router(sop_compliance_router)


@app.on_event("startup")
async def startup():
    # """Test connection on startup and initialize services"""
    # if ClickHouseConnection.test_connection():
    #     logger.info(f"Connected to ClickHouse at {settings.clickhouse_host}:{settings.clickhouse_port}")
    # else:
    #     logger.error("Failed to connect to ClickHouse")
    
    # Initialize validation service HTTP client
    await validation_service.initialize()
    
    # Start trigger merge retry worker
    await trigger_merge_service.start_worker()
    
    logger.info("FastAPI started - ready to receive events from Vector")


@app.on_event("shutdown")
async def shutdown():
    """Close connections on shutdown"""
    await validation_service.shutdown()
    await trigger_merge_service.stop_worker()
    ClickHouseConnection.close()
    logger.info("ClickHouse connection closed")