from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status, HTTPException
from app.core.dependencies import get_current_user, require_roles
from app.schemas.common import ApiResponse
from app.schemas.student import StudentResponse
from app.schemas.student_attendance import (
    AbsenteeReasonSaveRequest,
    StudentAnalyticsItem,
    StudentAttendanceRecordResponse,
    StudentAttendanceSubmitRequest,
)
from app.schemas.user import UserRole
from app.services.student_attendance_service import (
    get_absentee_sections,
    get_absentee_students_for_section,
    get_absentee_years,
    get_student_complete_history,
    get_students_analytics_summary,
    save_absence_reason,
    submit_student_attendance,
)
from app.services.student_service import get_students

router = APIRouter(tags=["Student Attendance & Analytics"])


# ----------------------------------------------------
# CRLR STUDENT ATTENDANCE ENDPOINTS
# ----------------------------------------------------

@router.get("/crlr/students", response_model=ApiResponse[List[StudentResponse]])
async def get_crlr_assigned_students_api(
    current_user: dict = Depends(require_roles([UserRole.CR, UserRole.LR])),
):
    """Fetch all students belonging to the logged-in CRLR's assigned year & section."""
    user_sec = current_user.get("section")
    user_year = current_user.get("year")

    if not user_sec:
        raise HTTPException(status_code=400, detail="CRLR user has no assigned section.")

    students = await get_students(year=user_year, section=user_sec, limit=1000)
    return ApiResponse(success=True, data=students)


@router.post("/crlr/student-attendance", response_model=ApiResponse[dict])
async def submit_student_attendance_api(
    data: StudentAttendanceSubmitRequest,
    current_user: dict = Depends(require_roles([UserRole.CR, UserRole.LR])),
):
    """Submit today's student attendance absentees list for CRLR's assigned year & section."""
    res = await submit_student_attendance(data, current_user)
    return ApiResponse(success=True, data=res, message=res["message"])


# ----------------------------------------------------
# MENTOR ABSENTEE & REASON ENDPOINTS
# ----------------------------------------------------

@router.get("/mentor/absentees/years", response_model=ApiResponse[List[str]])
async def get_absentee_years_api(
    current_user: dict = Depends(require_roles([UserRole.MENTOR, UserRole.ADMIN])),
):
    """Retrieve dynamic list of years available for absentees."""
    years = await get_absentee_years()
    return ApiResponse(success=True, data=years)


@router.get("/mentor/absentees/sections", response_model=ApiResponse[List[str]])
async def get_absentee_sections_api(
    year: str = Query(...),
    current_user: dict = Depends(require_roles([UserRole.MENTOR, UserRole.ADMIN])),
):
    """Retrieve sections belonging to a year dynamically."""
    sections = await get_absentee_sections(year)
    return ApiResponse(success=True, data=sections)


@router.get("/mentor/absentees", response_model=ApiResponse[List[StudentAttendanceRecordResponse]])
async def get_absentee_students_api(
    year: str = Query(...),
    section: str = Query(...),
    date: Optional[str] = Query(None),
    current_user: dict = Depends(require_roles([UserRole.MENTOR, UserRole.ADMIN])),
):
    """Retrieve today's absentee students for a specific year and section."""
    records = await get_absentee_students_for_section(year, section, date)
    return ApiResponse(success=True, data=records)


@router.put("/mentor/absentees/{record_id}/reason", response_model=ApiResponse[StudentAttendanceRecordResponse])
async def update_absence_reason_api(
    record_id: str,
    data: AbsenteeReasonSaveRequest,
    current_user: dict = Depends(require_roles([UserRole.MENTOR, UserRole.ADMIN])),
):
    """Save or update absence reason for a student attendance record."""
    updated = await save_absence_reason(record_id, data.reason, current_user.get("name", "Mentor"))
    return ApiResponse(success=True, data=updated, message="Absence reason saved successfully.")


# ----------------------------------------------------
# STUDENT ATTENDANCE ANALYTICS ENDPOINTS
# ----------------------------------------------------

@router.get("/analytics/student-summary", response_model=ApiResponse[List[StudentAnalyticsItem]])
async def get_student_analytics_summary_api(
    year: str = Query(...),
    section: str = Query(...),
    current_user: dict = Depends(require_roles([UserRole.MENTOR, UserRole.ADMIN])),
):
    """Get student cards with total absences & attendance percentage for a section."""
    summary = await get_students_analytics_summary(year, section)
    return ApiResponse(success=True, data=summary)


@router.get("/analytics/student-history", response_model=ApiResponse[List[StudentAttendanceRecordResponse]])
async def get_student_complete_history_api(
    roll_number: str = Query(..., alias="rollNumber"),
    current_user: dict = Depends(require_roles([UserRole.MENTOR, UserRole.ADMIN])),
):
    """Get complete absence history for a student sorted newest first."""
    history = await get_student_complete_history(roll_number)
    return ApiResponse(success=True, data=history)
