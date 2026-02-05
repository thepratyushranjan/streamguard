"""
Office SOP Compliance Audit Service Module
"""
from typing import Dict, Any, Optional, List
from clickhouse_connect.driver import Client

from db.schemas import (
    OfficeComplianceAudit, OfficeAIResponse,
    OFFICE_METADATA_FIELDS, OFFICE_SOP_FIELDS,
    OFFICE_CRITICAL_ALERT_FIELDS, OFFICE_HIGH_ALERT_FIELDS,
    OFFICE_MEDIUM_ALERT_FIELDS, OFFICE_LOW_ALERT_FIELDS,
    OFFICE_SCORE_FIELDS, OFFICE_COUNT_FIELDS,
    OFFICE_ZONE_FIELDS, OFFICE_ZONE_KPI_FIELDS, OFFICE_AGGREGATE_FIELDS
)
from core.connection import get_clickhouse
from utils.logger import get_logger

logger = get_logger(__name__)

# Mapping from model attribute to ClickHouse column (handles nested array fields)
_FACE_FIELD_MAP = {
    'faces_identity_id': 'faces.identity_id',
    'faces_confidence': 'faces.confidence',
    'faces_location': 'faces.location',
    'faces_timestamp_offset': 'faces.timestamp_offset'
}


def _build_column_list() -> List[str]:
    """Build ClickHouse column list from field constants."""
    columns = []
    columns.extend(OFFICE_METADATA_FIELDS)
    columns.extend(OFFICE_SOP_FIELDS)
    columns.extend(OFFICE_CRITICAL_ALERT_FIELDS)
    columns.extend(OFFICE_HIGH_ALERT_FIELDS)
    columns.extend(OFFICE_MEDIUM_ALERT_FIELDS)
    columns.extend(OFFICE_LOW_ALERT_FIELDS)
    columns.extend(OFFICE_SCORE_FIELDS)
    columns.extend(OFFICE_COUNT_FIELDS)
    columns.extend(OFFICE_ZONE_FIELDS)
    columns.extend(OFFICE_ZONE_KPI_FIELDS)
    columns.extend(_FACE_FIELD_MAP.values())
    columns.extend(['status', 'utilization', 'event_triggers'])
    columns.append('ai_summary')
    columns.extend(OFFICE_AGGREGATE_FIELDS)
    return columns


COLUMNS = _build_column_list()


def _build_audit_row(audit: OfficeComplianceAudit) -> List[Any]:
    """Build a row of values from audit model matching COLUMNS order."""
    row = []
    # Metadata
    row.extend(getattr(audit, f) for f in OFFICE_METADATA_FIELDS)
    # SOP
    row.extend(getattr(audit, f) for f in OFFICE_SOP_FIELDS)
    # Alerts
    row.extend(getattr(audit, f) for f in OFFICE_CRITICAL_ALERT_FIELDS)
    row.extend(getattr(audit, f) for f in OFFICE_HIGH_ALERT_FIELDS)
    row.extend(getattr(audit, f) for f in OFFICE_MEDIUM_ALERT_FIELDS)
    row.extend(getattr(audit, f) for f in OFFICE_LOW_ALERT_FIELDS)
    # Scores
    row.extend(getattr(audit, f) for f in OFFICE_SCORE_FIELDS)
    # Counts
    row.extend(getattr(audit, f) for f in OFFICE_COUNT_FIELDS)
    # Zone analysis
    row.extend(getattr(audit, f) for f in OFFICE_ZONE_FIELDS)
    # Zone KPIs
    row.extend(getattr(audit, f) for f in OFFICE_ZONE_KPI_FIELDS)
    # Face recognition (arrays)
    row.extend([
        audit.faces_identity_id,
        audit.faces_confidence,
        audit.faces_location,
        audit.faces_timestamp_offset
    ])
    # Classification
    row.extend([audit.status, audit.utilization, audit.event_triggers])
    # AI
    row.append(audit.ai_summary)
    # Aggregates
    row.extend(getattr(audit, f) for f in OFFICE_AGGREGATE_FIELDS)
    return row


def save_office_ai_response_to_audit(ai_response: Dict[str, Any], client: Optional[Client] = None) -> Dict[str, Any]:
    """
    Parse Office AI response and save to office_compliance_audits table.
    
    Args:
        ai_response: The AI response dictionary
        client: Optional ClickHouse client (uses singleton if not provided)
    
    Returns:
        Dict with success status and details
    """
    try:
        parsed = OfficeAIResponse.model_validate(ai_response)
        audit = parsed.to_audit()
        company_id = (audit.company_id or "").strip()
        if not company_id:
            logger.error(f"Missing company_id in Office AI response: {ai_response.get('metadata', {})}")
            return {"success": False, "error": "Missing company_id in AI response metadata"}
        
        db_client = client or get_clickhouse(company_id)
        logger.debug(f"Using ClickHouse client for company {company_id}, DB: {db_client.database}")
        result = process_office_audit(audit, db_client)
        
        # Merge triggers to video_analytics_logs if save was successful
        if result.get("success") and audit.event_triggers:
            from services.trigger_merge_service import trigger_merge_service
            merge_result = trigger_merge_service.merge_triggers(
                event_timestamp=audit.event_timestamp,
                device_id=audit.device_id,
                company_id=audit.company_id,
                triggers=audit.event_triggers
            )
            result["trigger_merge"] = merge_result
        
        return result
    except Exception as e:
        logger.error(f"Failed to save Office AI response to audit: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


def process_office_audit(audit: OfficeComplianceAudit, client: Client) -> Dict[str, Any]:
    """Process and insert Office compliance audit into ClickHouse."""
    try:
        row = [_build_audit_row(audit)]
        client.insert('office_compliance_audits', row, column_names=COLUMNS)
        return {"success": True, "inserted": 1}
    except Exception as e:
        logger.error(f"Office audit insert error: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
