"""
SOP Compliance Audit Service Module
"""
from typing import Dict, Any, Optional, List
from clickhouse_connect.driver import Client

from db.schemas import (
    SOPComplianceAudit, AIResponse,
    METADATA_FIELDS, SOP_FIELDS, SAFETY_FIELDS, OPERATIONS_FIELDS,
    SCORE_FIELDS, BEHAVIORAL_INT_FIELDS, COUNT_FIELDS, AGGREGATE_FIELDS
)
from core.connection import get_clickhouse
from utils.logger import get_logger

logger = get_logger(__name__)

# Mapping from model attribute to ClickHouse column (handles nested array fields)
_VEHICLE_FIELD_MAP = {
    'vehicles_type': 'vehicles.type',
    'vehicles_plate': 'vehicles.plate', 
    'vehicles_confidence': 'vehicles.confidence'
}

# Build column list dynamically from schema field constants (DRY)
def _build_column_list() -> List[str]:
    """Build ClickHouse column list from field constants."""
    columns = []
    columns.extend(METADATA_FIELDS)
    columns.extend(SOP_FIELDS)
    columns.extend(SAFETY_FIELDS)
    columns.extend(OPERATIONS_FIELDS)
    columns.extend(SCORE_FIELDS)
    columns.append('overall_score')
    columns.append('customer_present')
    columns.extend(BEHAVIORAL_INT_FIELDS)
    columns.extend(COUNT_FIELDS)
    columns.append('media_analyzed')
    columns.extend(_VEHICLE_FIELD_MAP.values())
    columns.extend(['status', 'utilization', 'event_triggers'])
    columns.append('ai_summary')
    columns.extend(AGGREGATE_FIELDS)
    return columns

COLUMNS = _build_column_list()


def _build_audit_row(audit: SOPComplianceAudit) -> List[Any]:
    """Build a row of values from audit model matching COLUMNS order."""
    row = []
    # Metadata
    row.extend(getattr(audit, f) for f in METADATA_FIELDS)
    # SOP
    row.extend(getattr(audit, f) for f in SOP_FIELDS)
    # Safety
    row.extend(getattr(audit, f) for f in SAFETY_FIELDS)
    # Operations
    row.extend(getattr(audit, f) for f in OPERATIONS_FIELDS)
    # Scores
    row.extend(getattr(audit, f) for f in SCORE_FIELDS)
    row.append(audit.overall_score)
    # Behavioral
    row.append(audit.customer_present)
    row.extend(getattr(audit, f) for f in BEHAVIORAL_INT_FIELDS)
    # Counts
    row.extend(getattr(audit, f) for f in COUNT_FIELDS)
    row.append(audit.media_analyzed)
    # Vehicles (arrays)
    row.extend([audit.vehicles_type, audit.vehicles_plate, audit.vehicles_confidence])
    # Classification
    row.extend([audit.status, audit.utilization, audit.event_triggers])
    # AI
    row.append(audit.ai_summary)
    # Aggregates
    row.extend(getattr(audit, f) for f in AGGREGATE_FIELDS)
    return row


def save_ai_response_to_audit(ai_response: Dict[str, Any], client: Optional[Client] = None) -> Dict[str, Any]:
    """
    Parse AI response and save to sop_compliance_audits table.
    Also merges AI-info triggers into matching video_analytics_logs record.
    
    Args:
        ai_response: The AI response dictionary
        client: Optional ClickHouse client (uses singleton if not provided)
    
    Returns:
        Dict with success status and details
    """
    try:
        parsed = AIResponse.model_validate(ai_response)
        audit = parsed.to_audit()
        company_id = (audit.company_id or "").strip()
        if not company_id:
            logger.error(f"Missing company_id in AI response: {ai_response.get('metadata', {})}")
            return {"success": False, "error": "Missing company_id in AI response metadata"}
        
        db_client = client or get_clickhouse(company_id)
        logger.debug(f"Using ClickHouse client for company {company_id}, DB: {db_client.database}")
        result = process_sop_audit(audit, db_client)
        
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
        logger.error(f"Failed to save AI response to audit: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


def process_sop_audit(audit: SOPComplianceAudit, client: Client) -> Dict[str, Any]:
    """Process and insert SOP compliance audit into ClickHouse."""
    try:
        row = [_build_audit_row(audit)]
        client.insert('sop_compliance_audits', row, column_names=COLUMNS)
        return {"success": True, "inserted": 1}
    except Exception as e:
        logger.error(f"SOP audit insert error: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
