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


async def get_student_attendance_submission_status(
    year: str, section: str, date: Optional[str] = None
) -> Dict[str, Any]:
    """Check whether attendance for a given section and year has already been submitted for today."""
    db = get_database()
    if not date:
        date = datetime.now(tz_kolkata).strftime("%Y-%m-%d")

    req_sec = section.strip().upper()
    req_year = year.strip()

    sub = await db.student_attendance_submissions.find_one({
        "year": req_year,
        "section": req_sec,
        "date": date,
    })

    if not sub:
        return {
            "isSubmittedToday": False,
            "date": date,
            "year": req_year,
            "section": req_sec,
            "submittedBy": None,
            "submittedByRole": None,
            "submittedAt": None,
            "absentCount": 0,
            "absentRolls": [],
        }

    # Retrieve roll numbers marked as absent today
    abs_docs = await db.student_attendance.find({
        "year": req_year,
        "section": req_sec,
        "date": date,
        "status": "Absent",
    }).to_list(length=500)
    abs_rolls = [d.get("roll_number") for d in abs_docs if d.get("roll_number")]

    submitted_at_val = sub.get("submitted_at") or sub.get("updated_at")
    submitted_at_str = submitted_at_val.isoformat() if isinstance(submitted_at_val, datetime) else str(submitted_at_val or "")

    return {
        "isSubmittedToday": True,
        "date": date,
        "year": req_year,
        "section": req_sec,
        "submittedBy": sub.get("submitted_by", "CR/LR"),
        "submittedByRole": sub.get("submitted_by_role", "CR"),
        "submittedAt": submitted_at_str,
        "absentCount": sub.get("absent_count", len(abs_rolls)),
        "absentRolls": abs_rolls,
    }


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

    # Prevent duplicate submission by either CR or LR for the same section on the same calendar day
    existing_sub = await db.student_attendance_submissions.find_one({
        "year": req_year,
        "section": req_sec,
        "date": date_str,
    })
    if existing_sub:
        prev_submitter = existing_sub.get("submitted_by", "a Class Representative")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Today's attendance for {req_year} Section {req_sec} has already been submitted by {prev_submitter}. Only one submission per section is permitted each day.",
        )

    # Save absentee records
    absentee_docs = []
    absent_rolls = []
    for ab in data.absentees:
        r_num = ab.roll_number.strip().upper()
        absent_rolls.append(r_num)
        doc = {
            "date": date_str,
            "year": req_year,
            "section": req_sec,
            "roll_number": r_num,
            "student_id": ab.student_id,
            "student_name": ab.student_name.strip(),
            "student_phone": ab.student_phone,
            "parent_phone": ab.parent_phone,
            "submitted_by": f"{current_user.get('name', 'CRLR')} ({user_role})",
            "status": "Absent",
            "reason": None,
            "created_at": now_utc,
            "updated_at": now_utc,
        }
        absentee_docs.append(doc)

    if absentee_docs:
        await db.student_attendance.insert_many(absentee_docs)

    # Record submission marker
    submitter_display = f"{current_user.get('name', 'CRLR')} ({user_role})"
    sub_marker = {
        "year": req_year,
        "section": req_sec,
        "date": date_str,
        "submitted_by": submitter_display,
        "submitted_by_role": user_role,
        "submitted_by_id": str(current_user.get("_id", "")),
        "absent_count": len(absentee_docs),
        "absent_rolls": absent_rolls,
        "submitted_at": now_utc,
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
        "submitted_by": submitter_display,
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
    """Get sections belonging to a year dynamically from uploaded timetables, students, and attendance records."""
    db = get_database()
    year_clean = year.strip()
    
    # Import student service helpers
    from app.services.student_service import build_year_filter_clause

    # 1. Sections from uploaded timetables for this year
    tt_secs = await db.timetables.distinct("section", {"year": year_clean})
    
    # Also check roman numeral prefix in timetables (e.g. II-A for 2nd Year, III-A for 3rd Year)
    roman_map = {"1st Year": "I", "2nd Year": "II", "3rd Year": "III", "4th Year": "IV"}
    r_prefix = roman_map.get(year_clean)
    if r_prefix:
        all_tt_secs = await db.timetables.distinct("section")
        for s in all_tt_secs:
            if s and (s.startswith(f"{r_prefix}-") or f"-{r_prefix}-" in s):
                tt_secs.append(s)

    # 2. Sections from uploaded students for this year
    year_clause = build_year_filter_clause(year_clean)
    stu_secs = await db.students.distinct("section", year_clause) if year_clause else await db.students.distinct("section", {"year": year_clean})

    # 3. Sections from student attendance records
    att_secs = await db.student_attendance.distinct("section", {"year": year_clean})

    all_secs = sorted(list(set([s.upper().strip() for s in (tt_secs + stu_secs + att_secs) if s and s.strip()])))
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


async def save_absence_reason(record_id: str, reason: str, actor_name: str, actor_id: Optional[str] = None) -> StudentAttendanceRecordResponse:
    """Save or update the absence reason for a specific attendance record."""
    db = get_database()
    clean_id = (record_id or "").strip()

    doc = None
    if ObjectId.is_valid(clean_id):
        doc = await db.student_attendance.find_one({"_id": ObjectId(clean_id)})
    if not doc:
        doc = await db.student_attendance.find_one({"_id": clean_id})
    if not doc:
        today_date = datetime.now(tz_kolkata).strftime("%Y-%m-%d")
        doc = await db.student_attendance.find_one({
            "roll_number": clean_id.upper(),
            "date": today_date,
        })
    if not doc:
        doc = await db.student_attendance.find_one({
            "$or": [
                {"student_id": clean_id},
                {"roll_number": clean_id.upper()},
            ]
        }, sort=[("date", -1), ("created_at", -1)])
    if not doc:
        raise HTTPException(status_code=404, detail="Attendance record not found.")

    now_utc = datetime.now(timezone.utc)
    actual_id = doc["_id"]

    update_payload = {
        "reason": reason.strip(),
        "reason_updated_by": actor_name,
        "updated_at": now_utc,
    }
    if actor_id:
        update_payload["reason_updated_by_id"] = str(actor_id)

    await db.student_attendance.update_one(
        {"_id": actual_id},
        {"$set": update_payload},
    )

    updated = await db.student_attendance.find_one({"_id": actual_id})
    updated["_id"] = str(updated["_id"])
    return StudentAttendanceRecordResponse(**updated)


async def get_students_analytics_summary(year: str, section: str) -> List[StudentAnalyticsItem]:
    """Get student attendance analytics summary for a year and section."""
    db = get_database()
    year_clean = year.strip()
    sec_clean = section.strip().upper()
    sec_norm = (
        sec_clean.replace("II-", "")
        .replace("I-", "")
        .replace("III-", "")
        .replace("IV-", "")
        .replace("CSE-", "")
        .strip()
    )

    sec_candidates = list(set([
        section,
        sec_clean,
        sec_norm,
        f"CSE-{sec_norm}",
        f"II-CSE-{sec_norm}",
        f"I-CSE-{sec_norm}",
        f"III-CSE-{sec_norm}",
        f"IV-CSE-{sec_norm}",
        f"II-{sec_norm}",
        f"III-{sec_norm}",
        f"IV-{sec_norm}",
        f"I-{sec_norm}",
    ]))
    sec_candidates = [c for c in sec_candidates if c]

    from app.services.student_service import build_year_filter_clause
    year_clause = build_year_filter_clause(year_clean)

    query: Dict[str, Any] = {"section": {"$in": sec_candidates}}
    if year_clause:
        query = {"$and": [query, {"$or": [{"year": year_clean}, year_clause]}]}
    else:
        query["year"] = year_clean

    cursor = db.students.find(query).sort("roll_number", 1)
    students_docs = await cursor.to_list(length=5000)

    # If nothing matched with year, try section only as a fallback
    if not students_docs:
        students_docs = await db.students.find({"section": {"$in": sec_candidates}}).sort("roll_number", 1).to_list(length=5000)

    total_days_count = await db.student_attendance_submissions.count_documents({
        "section": {"$in": sec_candidates}
    })
    total_days = max(total_days_count, 1)

    abs_docs = await db.student_attendance.find({
        "status": "Absent",
    }).to_list(length=20000)

    abs_counts = {}
    for doc in abs_docs:
        r = doc.get("roll_number")
        if r:
            r_norm = str(r).strip().upper()
            abs_counts[r_norm] = abs_counts.get(r_norm, 0) + 1

    result = []
    for s in students_docs:
        roll = str(s.get("roll_number") or "").strip().upper()
        if not roll:
            continue
        abs_count = abs_counts.get(roll, 0)

        pct = round(((total_days - abs_count) / total_days) * 100, 1) if total_days > 0 else 100.0
        if pct < 0:
            pct = 0.0

        result.append(StudentAnalyticsItem(
            student_id=str(s.get("_id", roll)),
            student_name=s.get("name", "Student"),
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
        if not doc.get("subject"):
            doc["subject"] = "Academic Session"
        if not doc.get("faculty"):
            doc["faculty"] = "Assigned Faculty"
        if not doc.get("session"):
            doc["session"] = "Regular Class Session"
        history.append(StudentAttendanceRecordResponse(**doc))
    return history
