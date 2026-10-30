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
    StudentAttendanceCorrectRequest,
)
from app.schemas.user import UserRole
from app.services.student_attendance_service import (
    get_absentee_sections,
    get_absentee_students_for_section,
    get_absentee_years,
    get_student_attendance_submission_status,
    get_student_complete_history,
    get_students_analytics_summary,
    save_absence_reason,
    submit_student_attendance,
    correct_student_attendance,
)
from app.services.student_service import get_students
from app.db.mongodb import get_database
from datetime import datetime
from app.core.config import settings
import zoneinfo

router = APIRouter(tags=["Student Attendance & Analytics"])


@router.get("/admin/student-attendance/summary", response_model=ApiResponse[dict])
async def get_admin_student_attendance_summary_api(
    date: Optional[str] = Query(None), year: Optional[str] = Query(None),
    branch: Optional[str] = Query(None), section: Optional[str] = Query(None),
    session_id: Optional[str] = Query(None, alias="sessionId"),
    admin: dict = Depends(require_roles([UserRole.ADMIN])),
):
    db = get_database()
    day = date or datetime.now(zoneinfo.ZoneInfo(settings.TIMEZONE)).strftime("%Y-%m-%d")
    query = {"date": day}
    if year: query["year"] = year
    if branch: query["branch"] = branch.upper()
    if section: query["section"] = section.upper()
    if session_id:
        if session_id not in {"SESSION_1", "SESSION_2"}:
            raise HTTPException(status_code=400, detail="Invalid attendance session.")
        query["session_id"] = session_id
    records = await db.student_attendance.find(query).to_list(length=50000)
    records.extend(await db.student_attendance_sessions.find(query).to_list(length=50000))
    for record in records:
        record.setdefault("session_id", "SESSION_1")
    groups = {}
    for record in records:
        key = (record.get("year", ""), record.get("branch", ""), record.get("section", ""), record.get("session_id", "LEGACY"))
        group = groups.setdefault(key, {"year": key[0], "branch": key[1], "section": key[2], "sessionId": key[3], "present": 0, "absent": 0})
        group[record.get("status", "Absent").lower()] += 1
    local_now = datetime.now(zoneinfo.ZoneInfo(settings.TIMEZONE))
    day_timetables = await db.timetables.find({"day": local_now.strftime("%A")}).to_list(length=10000)
    for timetable in day_timetables:
        if year and timetable.get("year") != year: continue
        if section and str(timetable.get("section", "")).upper() != section.upper(): continue
        sec = str(timetable.get("section", "")).upper()
        yr = str(timetable.get("year", ""))
        if branch:
            parts = sec.split("-")
            if len(parts) < 3 or parts[-2] != branch.upper(): continue
        inferred_branch = sec.split("-")[-2] if len(sec.split("-")) >= 3 else ""
        for sid in ("SESSION_1", "SESSION_2"):
            if session_id and sid != session_id: continue
            groups.setdefault((yr, inferred_branch, sec, sid), {"year": yr, "branch": inferred_branch, "section": sec, "sessionId": sid, "present": 0, "absent": 0})
    items = []
    for group in groups.values():
        total = group["present"] + group["absent"]
        marker = await db.student_attendance_submissions.find_one({"year": group["year"], "section": group["section"], "date": day, "session_id": group["sessionId"]})
        if not marker and group["sessionId"] == "SESSION_1":
            marker = await db.student_attendance_submissions.find_one({"year": group["year"], "section": group["section"], "date": day, "session_id": {"$exists": False}})
        items.append({**group, "total": total, "attendancePercentage": round(group["present"] * 100 / total, 1) if total else 0,
                      "submittedBy": marker.get("submitted_by") if marker else None,
                      "submittedAt": marker.get("submitted_at") if marker else None,
                      "status": "Completed" if marker else "Pending"})
    return ApiResponse(success=True, data={"date": day, "sessions": items,
        "totalPresent": sum(item["present"] for item in items), "totalAbsent": sum(item["absent"] for item in items),
        "completedSubmissions": sum(item["status"] == "Completed" for item in items)})


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


@router.get("/crlr/student-attendance/status", response_model=ApiResponse[dict])
async def get_crlr_student_attendance_status_api(
    year: Optional[str] = Query(None),
    section: Optional[str] = Query(None),
    date: Optional[str] = Query(None),
    current_user: dict = Depends(require_roles([UserRole.CR, UserRole.LR, UserRole.MENTOR, UserRole.ADMIN])),
):
    """Check if attendance has already been submitted for a class section today."""
    req_year = year or current_user.get("year") or "2nd Year"
    req_sec = section or current_user.get("section") or ""
    if not req_sec:
        raise HTTPException(status_code=400, detail="Section is required to check submission status.")
    role = current_user.get("role")
    if role in [UserRole.CR.value, UserRole.LR.value] and (req_sec.strip().upper() != (current_user.get("section") or "").strip().upper() or req_year.strip() != (current_user.get("year") or "").strip()):
        raise HTTPException(status_code=403, detail="You can only view attendance status for your assigned section.")

    status_data = await get_student_attendance_submission_status(req_year, req_sec, date)
    return ApiResponse(success=True, data=status_data)


@router.post("/crlr/student-attendance", response_model=ApiResponse[dict])
async def submit_student_attendance_api(
    data: StudentAttendanceSubmitRequest,
    current_user: dict = Depends(require_roles([UserRole.CR, UserRole.LR])),
):
    """Submit today's student attendance absentees list for CRLR's assigned year & section."""
    res = await submit_student_attendance(data, current_user)
    return ApiResponse(success=True, data=res, message=res["message"])


@router.patch("/crlr/student-attendance/correct", response_model=ApiResponse[StudentAttendanceRecordResponse])
@router.post("/crlr/student-attendance/correct", response_model=ApiResponse[StudentAttendanceRecordResponse])
async def correct_student_attendance_direct_api(
    data: StudentAttendanceCorrectRequest,
    current_user: dict = Depends(require_roles([UserRole.CR, UserRole.LR, UserRole.ADMIN])),
):
    """Correct an absent student to Present with a mandatory reason."""
    updated = await correct_student_attendance(None, data, current_user)
    return ApiResponse(success=True, data=updated, message="Student attendance corrected successfully.")


@router.patch("/crlr/student-attendance/{record_id}/correct", response_model=ApiResponse[StudentAttendanceRecordResponse])
@router.patch("/student-attendance/{record_id}/correct", response_model=ApiResponse[StudentAttendanceRecordResponse])
async def correct_student_attendance_by_id_api(
    record_id: str,
    data: StudentAttendanceCorrectRequest,
    current_user: dict = Depends(require_roles([UserRole.CR, UserRole.LR, UserRole.ADMIN])),
):
    """Correct an absent student record to Present with a mandatory reason."""
    updated = await correct_student_attendance(record_id, data, current_user)
    return ApiResponse(success=True, data=updated, message="Student attendance corrected successfully.")


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
    user_role = current_user.get("role", "")
    updated = await save_absence_reason(
        record_id,
        data.reason,
        current_user.get("name", "Mentor"),
        actor_id=str(current_user.get("_id", "")),
        actor_role=user_role,
    )
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
