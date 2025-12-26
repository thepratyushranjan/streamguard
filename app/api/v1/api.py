from fastapi import APIRouter
from app.api.v1.endpoints import sites

api_router = APIRouter()
api_router.include_router(sites.router, prefix="/sites", tags=["sites"])
