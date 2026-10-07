from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status, HTTPException
from app.core.dependencies import require_roles
from app.schemas.common import ApiResponse
from app.schemas.mentor import (
    MentorCommentRequest,
    MentorDashboardResponse,
    MentorSectionCard,
    MentorYearCard,
)
from app.schemas.student import StudentResponse
from app.schemas.student_attendance import (
    AbsenteeReasonSaveRequest,
    StudentAttendanceRecordResponse,
)
from app.schemas.user import UserRole
from app.services.mentor_service import (
    get_mentor_absentee_sections_summary,
    get_mentor_absentee_years_summary,
    get_mentor_dashboard_data,
    get_mentor_scoped_absentees,
    get_mentor_sections_summary,
    get_mentor_students_list,
    get_mentor_years_summary,
    search_absentees_global,
    search_students_global,
    update_absence_comment,
)
from app.services.student_attendance_service import (
    save_absence_reason,
)

router = APIRouter(prefix="/mentor", tags=["Mentor Portal Endpoints"])


@router.get("/dashboard", response_model=ApiResponse[MentorDashboardResponse])
async def get_mentor_dashboard_api(
    current_user: dict = Depends(require_roles([UserRole.MENTOR, UserRole.ADMIN])),
):
    """Retrieve complete overview statistics for Mentor Dashboard scoped by mentor assignments."""
    data = await get_mentor_dashboard_data(current_user)
    return ApiResponse(success=True, data=data)


# ----------------------------------------------------
# ALL STUDENTS ENDPOINTS
# ----------------------------------------------------

@router.get("/students/years", response_model=ApiResponse[List[MentorYearCard]])
async def get_mentor_students_years_api(
    current_user: dict = Depends(require_roles([UserRole.MENTOR, UserRole.ADMIN])),
):
    """Retrieve list of academic years scoped by mentor assignments."""
    data = await get_mentor_years_summary(current_user)
    return ApiResponse(success=True, data=data)


@router.get("/students/sections", response_model=ApiResponse[List[MentorSectionCard]])
async def get_mentor_students_sections_api(
    year: str = Query(..., description="Academic Year"),
    current_user: dict = Depends(require_roles([UserRole.MENTOR, UserRole.ADMIN])),
):
    """Retrieve sections belonging to a year scoped by mentor assignments."""
    data = await get_mentor_sections_summary(year, current_user)
    return ApiResponse(success=True, data=data)


@router.get("/students", response_model=ApiResponse[List[StudentResponse]])
async def get_mentor_students_api(
    year: Optional[str] = Query(None),
    section: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    current_user: dict = Depends(require_roles([UserRole.MENTOR, UserRole.ADMIN])),
):
    """Retrieve students filtered by year and section, scoped by mentor assignments and enriched with planned absences."""
    students = await get_mentor_students_list(year=year, section=section, search=search, current_user=current_user)
    return ApiResponse(success=True, data=students)


@router.get("/students/search", response_model=ApiResponse[List[StudentResponse]])
async def search_mentor_students_global_api(
    q: str = Query(..., min_length=1, description="Search term for name or roll number"),
    current_user: dict = Depends(require_roles([UserRole.MENTOR, UserRole.ADMIN])),
):
    """Global search across assigned students by name or roll number."""
    results = await search_students_global(q, current_user=current_user)
    return ApiResponse(success=True, data=results)


# ----------------------------------------------------
# ABSENTEES ENDPOINTS
# ----------------------------------------------------

@router.get("/absentees/years", response_model=ApiResponse[List[MentorYearCard]])
async def get_mentor_absentees_years_api(
    current_user: dict = Depends(require_roles([UserRole.MENTOR, UserRole.ADMIN])),
):
    """Retrieve academic years with today's absentee counts scoped by mentor assignments."""
    data = await get_mentor_absentee_years_summary(current_user)
    return ApiResponse(success=True, data=data)


@router.get("/absentees/sections", response_model=ApiResponse[List[MentorSectionCard]])
async def get_mentor_absentees_sections_api(
    year: str = Query(...),
    current_user: dict = Depends(require_roles([UserRole.MENTOR, UserRole.ADMIN])),
):
    """Retrieve sections belonging to a year with today's absentee counts scoped by mentor assignments."""
    data = await get_mentor_absentee_sections_summary(year, current_user)
    return ApiResponse(success=True, data=data)


@router.get("/absentees", response_model=ApiResponse[List[StudentAttendanceRecordResponse]])
async def get_mentor_absentees_api(
    year: str = Query(...),
    section: str = Query(...),
    date: Optional[str] = Query(None),
    current_user: dict = Depends(require_roles([UserRole.MENTOR, UserRole.ADMIN])),
):
    """Retrieve today's absentee students for a specific year and section, scoped by mentor assignments."""
    records = await get_mentor_scoped_absentees(year, section, date, current_user=current_user)
    return ApiResponse(success=True, data=records)


@router.get("/absentees/search", response_model=ApiResponse[List[StudentAttendanceRecordResponse]])
async def search_mentor_absentees_global_api(
    q: str = Query(..., min_length=1, description="Search term for name or roll number"),
    date: Optional[str] = Query(None),
    current_user: dict = Depends(require_roles([UserRole.MENTOR, UserRole.ADMIN])),
):
    """Global search across today's absentees by name or roll number scoped by mentor assignments."""
    results = await search_absentees_global(q, date=date, current_user=current_user)
    return ApiResponse(success=True, data=results)


@router.patch("/absentees/{record_id}/comment", response_model=ApiResponse[StudentAttendanceRecordResponse])
async def update_absence_comment_patch_api(
    record_id: str,
    data: MentorCommentRequest,
    current_user: dict = Depends(require_roles([UserRole.MENTOR, UserRole.ADMIN])),
):
    """Save or update absence reason / follow-up comment by mentor."""
    updated = await update_absence_comment(record_id, data.comment, current_user)
    return ApiResponse(success=True, data=updated, message="Absence reason saved successfully.")


@router.put("/absentees/{record_id}/reason", response_model=ApiResponse[StudentAttendanceRecordResponse])
async def update_absence_reason_put_api(
    record_id: str,
    data: AbsenteeReasonSaveRequest,
    current_user: dict = Depends(require_roles([UserRole.MENTOR, UserRole.ADMIN])),
):
    """Save or update absence reason (compatibility endpoint)."""
    updated = await save_absence_reason(record_id, data.reason, current_user.get("name", "Mentor"))
    return ApiResponse(success=True, data=updated, message="Absence reason saved successfully.")
