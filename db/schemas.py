from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional



class HealthResponse(BaseModel):
    status: str
    clickhouse: str
    timestamp: datetime