"""Triage Service - Updates triage fields in video_analytics_logs."""
import time
from typing import Dict, Any, Optional
from core.connection import get_clickhouse
from utils.logger import get_logger

logger = get_logger(__name__)

# Reuse escape pattern from trigger_merge_service
def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'")


def update_triage(
    event_timestamp: int,
    company_id: str,
    triaged_by: Optional[str] = None,
    triage_timestamp: Optional[int] = None,
    ai_insights: Optional[str] = None,
    triage_notes: Optional[str] = None
) -> Dict[str, Any]:
    """
    Update triage fields for a video_analytics_logs record.
    
    Args:
        event_timestamp: Event timestamp for matching (WHERE clause)
        company_id: Company ID for matching (WHERE clause)
        triaged_by: User who triaged (optional)
        triage_timestamp: Triage time (auto-set when triaged_by is provided)
        ai_insights: AI insights text (optional)
        triage_notes: Additional triage notes (optional)
    """
    # Auto-set triage_timestamp when triaged_by is provided
    if triaged_by is not None and triage_timestamp is None:
        triage_timestamp = int(time.time())

    # String fields that need escaping
    string_fields = {
        "triaged_by": triaged_by,
        "ai_insights": ai_insights,
        "triage_notes": triage_notes,
    }
    logger.info(f"string_fields: {string_fields}, triage_timestamp: {triage_timestamp}")
    
    updates = [
        f"{field} = '{_escape(value)}'" for field, value in string_fields.items() if value is not None
    ]
    
    # Handle integer field separately (no escaping/quoting needed)
    if triage_timestamp is not None:
        updates.append(f"triage_timestamp = {triage_timestamp}")
    
    client = get_clickhouse(company_id)
    where = f"event_timestamp = {event_timestamp} AND company_id = '{_escape(company_id)}'"
    
    count = client.query(f"SELECT count(*) FROM video_analytics_logs WHERE {where}").result_rows[0][0]
    if count == 0:
        return {"success": False, "reason": "No matching record found"}
    
    client.command(f"ALTER TABLE video_analytics_logs UPDATE {', '.join(updates)} WHERE {where}")
    logger.info(f"[TRIAGE] Updated ts={event_timestamp}, company={company_id}")
    
    return {"success": True}
