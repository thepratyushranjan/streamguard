"""Attendance Records Routes"""
from fastapi import APIRouter
from typing import Union, List

from utils.common import handle_route_exceptions, success_response
from services.attendance_records_services import process_attendance_record
from core.connection import get_clickhouse
from db.schemas import AttendanceRequest, AttendanceRecord

router = APIRouter(tags=["Attendance Records"])


@router.post("/attendance-records")
@handle_route_exceptions("Failed to save attendance record")
async def save_attendance_record(
    payload: Union[AttendanceRequest, List[AttendanceRequest]],
):
    """
    Receive and store attendance events.

    Accepts both a single AttendanceRequest object and a list.
    Each request is flattened via AttendanceRecord.from_request()
    before being persisted to ClickHouse.
    """
    items = payload if isinstance(payload, list) else [payload]

    total_inserted = 0
    for item in items:
        record = AttendanceRecord.from_request(item)

        company_id = (record.company_id or "").strip()
        if not company_id:
            continue

        client = get_clickhouse(company_id)
        result = process_attendance_record(record, client)
        total_inserted += result.get("inserted", 0)

    return success_response(
        message="Attendance record(s) saved successfully",
        inserted=total_inserted,
    )
