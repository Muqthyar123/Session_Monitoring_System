from datetime import datetime, timezone
import zoneinfo
from typing import List, Optional, Dict, Any
from bson import ObjectId
from fastapi import HTTPException, status
from app.core.config import settings
from app.db.mongodb import get_database
from app.schemas.student_attendance import (
    StudentAttendanceSubmitRequest,
    StudentAttendanceRecordResponse,
    StudentAnalyticsItem,
)

tz_kolkata = zoneinfo.ZoneInfo(settings.TIMEZONE)


async def submit_student_attendance(
    data: StudentAttendanceSubmitRequest, current_user: dict
) -> Dict[str, Any]:
    """Submit daily student attendance for CRLR's assigned year & section."""
    db = get_database()
    now_local = datetime.now(tz_kolkata)
    now_utc = datetime.now(timezone.utc)
    date_str = now_local.strftime("%Y-%m-%d")

    user_role = current_user.get("role")
    user_sec = (current_user.get("section") or "").strip().upper()
    user_year = (current_user.get("year") or "").strip()

    # Enforce role and assigned section for CRLR
    if user_role in ["CR", "LR"]:
        if user_sec and data.section.strip().upper() != user_sec:
            raise HTTPException(
                status_code=403,
                detail=f"Access forbidden: You can only submit attendance for your assigned section ({user_sec}).",
            )

    req_sec = data.section.strip().upper()
    req_year = data.year.strip()

    # Check if attendance was already submitted today for this year + section
    existing_sub = await db.student_attendance_submissions.find_one({
        "year": req_year,
        "section": req_sec,
        "date": date_str,
    })
    if existing_sub:
        # Update existing submission records
        await db.student_attendance.delete_many({
            "year": req_year,
            "section": req_sec,
            "date": date_str,
        })

    # Save absentee records
    absentee_docs = []
    for ab in data.absentees:
        doc = {
            "date": date_str,
            "year": req_year,
            "section": req_sec,
            "roll_number": ab.roll_number.strip().upper(),
            "student_id": ab.student_id,
            "student_name": ab.student_name.strip(),
            "student_phone": ab.student_phone,
            "parent_phone": ab.parent_phone,
            "submitted_by": current_user.get("name", "CRLR"),
            "status": "Absent",
            "reason": None,
            "created_at": now_utc,
            "updated_at": now_utc,
        }
        absentee_docs.append(doc)

    if absentee_docs:
        await db.student_attendance.insert_many(absentee_docs)

    # Record submission marker
    sub_marker = {
        "year": req_year,
        "section": req_sec,
        "date": date_str,
        "submitted_by": current_user.get("name", "CRLR"),
        "absent_count": len(absentee_docs),
        "updated_at": now_utc,
    }
    await db.student_attendance_submissions.update_one(
        {"year": req_year, "section": req_sec, "date": date_str},
        {"$set": sub_marker},
        upsert=True,
    )

    return {
        "message": f"Successfully submitted attendance for {req_year} Section {req_sec}.",
        "date": date_str,
        "absent_count": len(absentee_docs),
    }


async def get_absentee_years() -> List[str]:
    """Dynamically get years available in student attendance or students DB."""
    db = get_database()
    att_years = await db.student_attendance.distinct("year")
    stu_years = await db.students.distinct("year")
    
    all_years = sorted(list(set([y for y in (att_years + stu_years) if y])))
    if not all_years:
        all_years = ["1st Year", "2nd Year", "3rd Year", "4th Year"]
    return all_years


async def get_absentee_sections(year: str) -> List[str]:
    """Get sections belonging to a year dynamically."""
    db = get_database()
    att_secs = await db.student_attendance.distinct("section", {"year": year})
    stu_secs = await db.students.distinct("section", {"year": year})
    
    all_secs = sorted(list(set([s.upper() for s in (att_secs + stu_secs) if s])))
    return all_secs


async def get_absentee_students_for_section(year: str, section: str, date: Optional[str] = None) -> List[StudentAttendanceRecordResponse]:
    """Get list of absentee students for a specific year and section on a date (default today)."""
    db = get_database()
    if not date:
        date = datetime.now(tz_kolkata).strftime("%Y-%m-%d")

    cursor = db.student_attendance.find({
        "year": year,
        "section": section.upper(),
        "date": date,
        "status": "Absent",
    }).sort("roll_number", 1)

    absentees = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        absentees.append(StudentAttendanceRecordResponse(**doc))
    return absentees


async def save_absence_reason(record_id: str, reason: str, actor_name: str) -> StudentAttendanceRecordResponse:
    """Save or update the absence reason for a specific attendance record."""
    db = get_database()
    if not ObjectId.is_valid(record_id):
        raise HTTPException(status_code=400, detail="Invalid Record ID.")

    doc = await db.student_attendance.find_one({"_id": ObjectId(record_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Attendance record not found.")

    now_utc = datetime.now(timezone.utc)
    await db.student_attendance.update_one(
        {"_id": ObjectId(record_id)},
        {
            "$set": {
                "reason": reason.strip(),
                "reason_updated_by": actor_name,
                "updated_at": now_utc,
            }
        },
    )

    updated = await db.student_attendance.find_one({"_id": ObjectId(record_id)})
    updated["_id"] = str(updated["_id"])
    return StudentAttendanceRecordResponse(**updated)


async def get_students_analytics_summary(year: str, section: str) -> List[StudentAnalyticsItem]:
    """Get student attendance analytics summary for a year and section."""
    db = get_database()
    year_clean = year.strip()
    sec_clean = section.strip().upper()

    students = await db.students.find({"year": year_clean, "section": sec_clean}).to_list(length=1000)
    total_days_count = await db.student_attendance_submissions.count_documents({"year": year_clean, "section": sec_clean})
    total_days = max(total_days_count, 1)

    result = []
    for s in students:
        roll = s["roll_number"]
        abs_count = await db.student_attendance.count_documents({
            "year": year_clean,
            "section": sec_clean,
            "roll_number": roll,
            "status": "Absent",
        })

        pct = round(((total_days - abs_count) / total_days) * 100, 1) if total_days > 0 else 100.0
        if pct < 0:
            pct = 0.0

        result.append(StudentAnalyticsItem(
            student_id=str(s["_id"]),
            student_name=s["name"],
            roll_number=roll,
            year=year_clean,
            section=sec_clean,
            student_phone=s.get("student_phone"),
            parent_phone=s.get("parent_phone"),
            total_absences=abs_count,
            total_days=total_days,
            attendance_percentage=pct,
        ))

    result.sort(key=lambda x: x.roll_number)
    return result


async def get_student_complete_history(roll_number: str) -> List[StudentAttendanceRecordResponse]:
    """Get complete absence history for a student sorted newest first."""
    db = get_database()
    roll_clean = roll_number.strip().upper()

    cursor = db.student_attendance.find({"roll_number": roll_clean}).sort("date", -1)
    history = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        history.append(StudentAttendanceRecordResponse(**doc))
    return history
