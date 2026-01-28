"""SOP Compliance Audit Routes"""
from fastapi import APIRouter, Depends
from clickhouse_connect.driver import Client

from utils.common import handle_route_exceptions, success_response
from services.sop_compliance_services import process_sop_audit
from core.connection import get_clickhouse
from db.schemas import SOPComplianceAudit

router = APIRouter(tags=["SOP Compliance"])


@router.post("/sop-compliance-audit")
@handle_route_exceptions("Failed to save SOP compliance audit")
async def save_sop_compliance_audit(
    audit: SOPComplianceAudit
):
    """Store SOP compliance audit record."""
    client = get_clickhouse(audit.company_id)
    result = process_sop_audit(audit, client)
    return success_response(message="SOP compliance audit saved", inserted=result["inserted"])
