from fastapi import APIRouter, HTTPException, Depends
from clickhouse_connect.driver import Client
from datetime import datetime

from core.connection import get_clickhouse
from db.schemas import HealthResponse

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
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
