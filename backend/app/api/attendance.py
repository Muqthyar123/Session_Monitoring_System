from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from app.core.dependencies import get_current_user, require_roles
from app.schemas.attendance import (
    AdminAlertResponse,
    AttendanceRecordResponse,
    AttendanceSubmitRequest,
)
from app.schemas.common import ApiResponse
from app.schemas.session import ClassSessionResponse
from app.schemas.user import UserRole
from app.services.attendance_service import submit_attendance
from app.db.mongodb import get_database

router = APIRouter(prefix="/attendance", tags=["Attendance Management"])


@router.post("", response_model=ApiResponse[ClassSessionResponse])
async def submit_attendance_api(
    data: AttendanceSubmitRequest,
    current_user: dict = Depends(get_current_user),
):
    session_res = await submit_attendance(data, current_user)
    return ApiResponse(
        success=True, data=session_res, message="Faculty attendance recorded successfully."
    )


@router.get("/my", response_model=ApiResponse[List[AttendanceRecordResponse]])
async def get_my_attendance_records_api(
    current_user: dict = Depends(get_current_user),
):
    db = get_database()
    cursor = db.attendance_records.find({"user_id": current_user["id"]}).sort("created_at", -1)
    results = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        results.append(AttendanceRecordResponse(**doc))
    return ApiResponse(success=True, data=results)


@router.get("/alerts", response_model=ApiResponse[List[AdminAlertResponse]])
async def get_admin_alerts_api(
    admin: dict = Depends(require_roles([UserRole.ADMIN])),
):
    db = get_database()
    cursor = db.admin_alerts.find().sort("created_at", -1)
    results = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        results.append(AdminAlertResponse(**doc))
    return ApiResponse(success=True, data=results)
