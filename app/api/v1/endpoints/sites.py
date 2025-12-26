from fastapi import APIRouter, Depends, Query, HTTPException
from typing import List, Literal
from app.core.security import get_api_key
from app.services.clickhouse import get_clickhouse
from clickhouse_connect.driver import Client
from app.models.schemas import (
    SiteSummaryResponse, SiteMetric, 
    AnalyticsDistributionItem, AnalyticsTrafficResponse, AnalyticsTrafficSeries,
    EventListResponse, FrontEndEvent, EventMetadata
)
from datetime import datetime
import json

router = APIRouter()

@router.get("/{siteId}/summary", response_model=SiteSummaryResponse)
def get_site_summary(
    siteId: str, 
    client: Client = Depends(get_clickhouse),
    _: str = Depends(get_api_key)
):
    # Active Sensors (Last 5 mins)
    q_sensors = f"""
    SELECT uniq(cam_id) FROM camera_events 
    WHERE site = '{siteId}' AND event_timestamp > toUnixTimestamp(now() - INTERVAL 5 MINUTE)
    """
    active_sensors = client.query(q_sensors).first_row[0]

    # Open Alerts (Last 24h, WARNING/CRITICAL)
    q_alerts = f"""
    SELECT count() FROM camera_events 
    WHERE site = '{siteId}' 
    AND event_status IN ('WARNING', 'CRITICAL')
    AND event_timestamp > toUnixTimestamp(now() - INTERVAL 24 HOUR)
    """
    open_alerts = client.query(q_alerts).first_row[0]
    
    # Traffic Count (Today)
    q_traffic = f"""
    SELECT sum(people_count) FROM camera_events 
    WHERE site = '{siteId}' 
    AND toYYYYMMDD(toDateTime(event_timestamp)) = toYYYYMMDD(now())
    """
    traffic_count = client.query(q_traffic).first_row[0]
    
    # Peak Density (Today)
    q_peak = f"""
    SELECT max(people_count) FROM camera_events 
    WHERE site = '{siteId}' 
    AND toYYYYMMDD(toDateTime(event_timestamp)) = toYYYYMMDD(now())
    """
    peak_density = client.query(q_peak).first_row[0]

    metrics = SiteMetric(
        activeSensors=int(active_sensors),
        openAlerts=int(open_alerts),
        trafficCount=int(traffic_count or 0),
        peakDensity=int(peak_density or 0),
        complianceScore=95 # Mock for now
    )
    
    return SiteSummaryResponse(
        siteId=siteId,
        status="ONLINE" if active_sensors > 0 else "OFFLINE",
        metrics=metrics
    )

@router.get("/{siteId}/analytics/{viewType}")
def get_site_analytics(
    siteId: str, 
    viewType: Literal["distribution", "traffic-flow"],
    range: Literal["12h", "24h", "7d", "30d"] = "24h",
    client: Client = Depends(get_clickhouse),
    _: str = Depends(get_api_key)
):
    # Determine time window
    time_filters = {
        "12h": "12 HOUR",
        "24h": "24 HOUR",
        "7d": "7 DAY",
        "30d": "30 DAY"
    }
    time_filter = time_filters.get(range, "24 HOUR")
    
    if viewType == "distribution":
        query = f"""
        SELECT 
            arrayJoin(`detections.label`) as label,
            count() as value
        FROM camera_events
        WHERE site = '{siteId}'
        AND event_timestamp > toUnixTimestamp(now() - INTERVAL {time_filter})
        GROUP BY label
        ORDER BY value DESC
        """
        result = client.query(query)
        total = sum(row[1] for row in result.result_rows)
        
        response = []
        for row in result.result_rows:
            label, value = row
            response.append(AnalyticsDistributionItem(
                label=label,
                value=value,
                percentage=round((value / total) * 100, 2) if total > 0 else 0
            ))
        return response
        
    elif viewType == "traffic-flow":
        query = f"""
        SELECT 
            toStartOfHour(toDateTime(event_timestamp)) as period,
            sum(people_count)
        FROM camera_events
        WHERE site = '{siteId}'
        AND event_timestamp > toUnixTimestamp(now() - INTERVAL {time_filter})
        GROUP BY period
        ORDER BY period
        """
        result = client.query(query)
        
        timestamps = []
        values = []
        for row in result.result_rows:
            timestamps.append(row[0].strftime("%Y-%m-%dT%H:%M:%S"))
            values.append(row[1])
            
        return AnalyticsTrafficResponse(
            timestamps=timestamps,
            series=[AnalyticsTrafficSeries(key="traffic", data=values)]
        )

@router.get("/{siteId}/events", response_model=EventListResponse)
def get_site_events(
    siteId: str,
    limit: int = 50,
    severity: Literal["CRITICAL", "WARNING", "INFO"] = None,
    client: Client = Depends(get_clickhouse),
    _: str = Depends(get_api_key)
):
    where_clauses = [f"site = '{siteId}'"]
    
    if severity:
        if severity == "INFO":
            where_clauses.append("event_status = 'SAFE'")
        else:
            where_clauses.append(f"event_status = '{severity}'")
            
    where_str = " AND ".join(where_clauses)
    
    query = f"""
    SELECT 
        site, cam_id, cam_name, event_timestamp, event_type, event_status, 
        event_triggers, `detections.label`, `detections.confidence`
    FROM camera_events
    WHERE {where_str}
    ORDER BY event_timestamp DESC
    LIMIT {limit}
    """
    
    result = client.query(query)
    events = []
    
    for row in result.result_rows:
        (site, cam_id, cam_name, ts, e_type, status, triggers, det_labels, det_confs) = row
        
        mapped_severity = "INFO"
        if status == "CRITICAL": mapped_severity = "CRITICAL"
        elif status == "WARNING": mapped_severity = "WARNING"
            
        evt_type = "SECURITY" if e_type == "EVENT" else "OPERATIONS"
        
        # Determine subtype
        sub_type = "GENERAL"
        if triggers and len(triggers) > 0:
            sub_type = triggers[0]
        elif e_type == "METRIC":
            sub_type = "TRAFFIC_UPDATE"
            
        avg_conf = sum(det_confs)/len(det_confs) if det_confs else 0.0
            
        events.append(FrontEndEvent(
            id=f"{site}_{cam_id}_{ts}",
            timestamp=datetime.fromtimestamp(ts),
            sourceId=str(cam_id),
            sourceName=cam_name,
            type=evt_type,
            subType=sub_type,
            severity=mapped_severity,
            metadata=EventMetadata(
                detectedObjects=list(set(det_labels)), # Unique labels
                confidence=float(avg_conf),
                snapshotUrl=None 
            )
        ))
        
    return EventListResponse(events=events)
