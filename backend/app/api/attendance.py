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
    category: Optional[str] = Query(None, description="Filter: ALL, NO_RESPONSE_10MIN, FACULTY_ABSENT, FACULTY_STATUS_UPDATED"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter: ALL, New, Acknowledged"),
    admin: dict = Depends(require_roles([UserRole.ADMIN, UserRole.DEPARTMENT_COORDINATOR, UserRole.COORDINATOR])),
):
    db = get_database()
    query = {}

    if status_filter and status_filter.upper() != "ALL":
        query["status"] = {"$regex": f"^{status_filter}$", "$options": "i"}

    if category and category.upper() != "ALL":
        cat_upper = category.strip().upper()
        if cat_upper in ["NO_RESPONSE_10MIN", "TIMEOUT", "CR_LR_TIMEOUT", "NO_RESPONSE"]:
            query["$or"] = [
                {"reason": {"$regex": "10 min", "$options": "i"}},
                {"reason": {"$regex": "no response", "$options": "i"}},
                {"type": "NO_RESPONSE_ALERT"},
            ]
        elif cat_upper in ["FACULTY_ABSENT", "ABSENT", "NOT_PRESENT"]:
            query["$or"] = [
                {"reason": {"$regex": "not available", "$options": "i"}},
                {"reason": {"$regex": "absent", "$options": "i"}},
                {"reason": {"$regex": "substitute", "$options": "i"}},
                {"type": "FACULTY_ABSENT_ALERT"},
            ]
        elif cat_upper in ["FACULTY_STATUS_UPDATED", "UPDATED", "STATUS_UPDATED"]:
            query["$or"] = [
                {"reason": {"$regex": "updated", "$options": "i"}},
                {"reason": {"$regex": "status", "$options": "i"}},
                {"reason": {"$regex": "changed", "$options": "i"}},
            ]

    cursor = db.admin_alerts.find(query).sort("created_at", -1)
    results = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        results.append(AdminAlertResponse(**doc))
    return ApiResponse(success=True, data=results)


@router.patch("/alerts/{alert_id}/acknowledge", response_model=ApiResponse[dict])
async def acknowledge_alert_api(
    alert_id: str,
    admin: dict = Depends(require_roles([UserRole.ADMIN, UserRole.DEPARTMENT_COORDINATOR, UserRole.COORDINATOR])),
):
    from bson import ObjectId
    if not ObjectId.is_valid(alert_id):
        return ApiResponse(success=False, message="Invalid Alert ID.")
    db = get_database()
    await db.admin_alerts.update_one({"_id": ObjectId(alert_id)}, {"$set": {"status": "Acknowledged"}})
    return ApiResponse(success=True, message="Alert acknowledged successfully.")

