from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Literal, Dict, Any, Union
from datetime import datetime

# --- Health & Generic ---
class HealthResponse(BaseModel):
    status: str
    clickhouse: str
    timestamp: datetime

# --- Event Ingestion Models (from original schemas.py) ---
class Detection(BaseModel):
    class_id: int
    label: str
    confidence: float
    bbox: List[int] = Field(..., min_items=4, max_items=4) # [left, top, width, height]

class EventData(BaseModel):
    people_count: int = 0
    detections: List[Detection] = []
    triggers: List[str] = []
    capture_triggered: bool = False

class EventMeta(BaseModel):
    cam_id: int
    site: str
    status: Literal['SAFE', 'WARNING', 'CRITICAL']
    ts: float # Unix timestamp
    cam_name: Optional[str] = "Unknown"

    @field_validator('status', mode='before')
    def uppercase_status(cls, v):
        return v.upper() if isinstance(v, str) else v

class CameraEventRequest(BaseModel):
    type: Literal['METRIC', 'EVENT']
    processed_at: float
    meta: EventMeta
    data: Optional[EventData] = None
    event: Optional[EventData] = None

    @property
    def payload(self) -> EventData:
        return self.data or self.event or EventData()

# --- White Label API Models ---

class SiteMetric(BaseModel):
    activeSensors: int
    openAlerts: int
    trafficCount: int
    peakDensity: int
    complianceScore: int = 100 # Placeholder

class SiteSummaryResponse(BaseModel):
    siteId: str
    status: Literal["ONLINE", "OFFLINE"]
    metrics: SiteMetric

class AnalyticsDistributionItem(BaseModel):
    label: str
    value: int
    percentage: float

class AnalyticsTrafficSeries(BaseModel):
    key: str
    data: List[int]

class AnalyticsTrafficResponse(BaseModel):
    timestamps: List[str]
    series: List[AnalyticsTrafficSeries]

class EventMetadata(BaseModel):
    detectedObjects: List[str]
    confidence: float
    snapshotUrl: Optional[str] = None

class FrontEndEvent(BaseModel):
    id: str
    timestamp: datetime
    sourceId: str
    sourceName: str
    type: Literal["SECURITY", "SAFETY", "OPERATIONS"]
    subType: str
    severity: Literal["CRITICAL", "WARNING", "INFO"]
    metadata: EventMetadata
    
class EventListResponse(BaseModel):
    events: List[FrontEndEvent]
