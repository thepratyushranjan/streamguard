from fastapi import APIRouter
from core.config import get_settings

router = APIRouter(tags=["Root"])
settings = get_settings()


@router.get("/")
def root():
    return {
        "status": "running", 
        "service": "camera-event-processor",
        "database": settings.clickhouse_database
    }
