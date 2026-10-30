from datetime import datetime, timezone
import re
import zoneinfo
from typing import List, Optional, Dict, Any
from bson import ObjectId
from fastapi import HTTPException, status
from app.core.config import settings
from app.db.mongodb import get_database
from app.schemas.student_attendance import (
    StudentAttendanceSubmitRequest,
    StudentAttendanceRecordResponse,
    StudentAttendanceCorrectRequest,
    StudentAnalyticsItem,
)
from app.schemas.user import UserRole

tz_kolkata = zoneinfo.ZoneInfo(settings.TIMEZONE)


def _attendance_collection(db, session_id: str):
    # The historical collection has a deployed daily unique index. Keep it
    # intact for SESSION_1; SESSION_2 uses an additive collection.
    return db.student_attendance if session_id == "SESSION_1" else db.student_attendance_sessions


async def _attendance_records(db, query: Dict[str, Any], session_id: Optional[str] = None) -> List[dict]:
    collections = [(db.student_attendance_sessions, None)] if session_id == "SESSION_2" else [(db.student_attendance, "SESSION_1")] if session_id == "SESSION_1" else [(db.student_attendance, "SESSION_1"), (db.student_attendance_sessions, None)]
    results = []
    for collection, default_session in collections:
        docs = await collection.find(query).to_list(length=50000)
        if default_session:
            for doc in docs:
                doc.setdefault("session_id", default_session)
        results.extend(docs)
    return results


def _minutes_of_day(value: str) -> Optional[int]:
    match = re.match(r"^\s*(\d{1,2}):(\d{2})(?:\s*([AP]M))?\s*$", str(value or ""), re.I)
    if not match:
        return None
    hour, minute = int(match.group(1)), int(match.group(2))
    meridiem = (match.group(3) or "").upper()
    if minute > 59:
        return None
    if meridiem:
        if hour < 1 or hour > 12:
            return None
        hour = hour % 12 + (12 if meridiem == "PM" else 0)
    elif hour > 23:
        return None
    return hour * 60 + minute


def _clock_label(minutes: int) -> str:
    hour, minute = divmod(minutes, 60)
    return datetime(2000, 1, 1, hour, minute).strftime("%I:%M %p")


async def get_attendance_windows(year: str, section: str, now_local: Optional[datetime] = None) -> Dict[str, Any]:
    """Derive today's two windows from the largest free interval in the uploaded timetable."""
    db = get_database()
    now_local = now_local or datetime.now(tz_kolkata)
    day_name = now_local.strftime("%A")
    query = {"year": year.strip(), "section": section.strip().upper(), "day": day_name}
    periods = await db.timetables.find(query).to_list(length=500)
    if not periods:
        return {"configured": False, "reason": f"No timetable is configured for {year}, Section {section}, {day_name}."}
    parsed = []
    for period in periods:
        start, end = _minutes_of_day(period.get("start_time")), _minutes_of_day(period.get("end_time"))
        if start is not None and end is not None and start < end:
            parsed.append((start, end, period))
    parsed.sort(key=lambda row: (row[0], row[1]))
    if len(parsed) < 2:
        return {"configured": False, "reason": "The timetable needs at least two valid class periods to derive the lunch interval."}
    gaps = [(parsed[i + 1][0] - parsed[i][1], parsed[i][1], parsed[i + 1][0]) for i in range(len(parsed) - 1) if parsed[i + 1][0] > parsed[i][1]]
    if not gaps:
        return {"configured": False, "reason": "The timetable has no lunch break interval. Please check its class times."}
    _, lunch_start, lunch_end = max(gaps, key=lambda gap: gap[0])
    day_start, day_end = parsed[0][0], max(row[1] for row in parsed)
    if not (day_start < lunch_start < lunch_end < day_end):
        return {"configured": False, "reason": "The timetable lunch interval is invalid. Please check class and lunch times."}
    current = now_local.hour * 60 + now_local.minute
    windows = [
        {"sessionId": "SESSION_1", "label": "Before Lunch", "startMinutes": day_start, "endMinutes": lunch_start},
        {"sessionId": "SESSION_2", "label": "After Lunch", "startMinutes": lunch_end, "endMinutes": day_end},
    ]
    for item in windows:
        item["startTime"] = _clock_label(item.pop("startMinutes"))
        item["endTime"] = _clock_label(item.pop("endMinutes"))
        start_value = _minutes_of_day(item["startTime"])
        end_value = _minutes_of_day(item["endTime"])
        item["isOpen"] = start_value <= current < end_value
    day_token = day_name.lower()
    return {"configured": True, "date": now_local.strftime("%Y-%m-%d"), "day": day_name,
            "workingDay": day_token in {str(p.get("day", "")).lower() for p in periods}, "windows": windows,
            "timetableUpdatedAt": max((p.get("updated_at") for p in periods if p.get("updated_at")), default=None)}


async def get_student_attendance_submission_status(
    year: str, section: str, date: Optional[str] = None
) -> Dict[str, Any]:
    """Check whether attendance for a given section and year has already been submitted for today."""
    db = get_database()
    if not date:
        date = datetime.now(tz_kolkata).strftime("%Y-%m-%d")

    req_sec = section.strip().upper()
    req_year = year.strip()

    windows = await get_attendance_windows(req_year, req_sec)
    subs = await db.student_attendance_submissions.find({
        "year": req_year,
        "section": req_sec,
        "date": date,
    }).to_list(length=4)
    by_session = {sub.get("session_id", "SESSION_1"): sub for sub in subs}
    for window in windows.get("windows", []):
        sub = by_session.get(window["sessionId"])
        window["isSubmitted"] = bool(sub)
        window["submittedBy"] = sub.get("submitted_by") if sub else None
        window["submittedByRole"] = sub.get("submitted_by_role") if sub else None
        window["submittedAt"] = (sub.get("submitted_at").isoformat() if isinstance(sub.get("submitted_at"), datetime) else sub.get("submitted_at")) if sub else None
        window["absentCount"] = sub.get("absent_count", 0) if sub else 0
        window["absentRolls"] = sub.get("absent_rolls", []) if sub else []
        window["status"] = "submitted" if sub else ("open" if window.get("isOpen") else "not_available")
    return {
        "isSubmittedToday": len(by_session) == 2,
        "date": date,
        "year": req_year,
        "section": req_sec,
        "sessions": windows.get("windows", []),
        "timetable": windows,
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

    # Enforce role and exact assigned year/section for CRLR.
    if user_role in ["CR", "LR"]:
        if not user_sec or not user_year or data.section.strip().upper() != user_sec or data.year.strip() != user_year:
            raise HTTPException(
                status_code=403,
                detail=f"Access forbidden: You can only submit attendance for your assigned section ({user_sec}).",
            )

    req_sec = data.section.strip().upper()
    req_year = data.year.strip()
    session_id = data.session_id

    windows = await get_attendance_windows(req_year, req_sec, now_local)
    if not windows.get("configured"):
        raise HTTPException(status_code=400, detail=windows.get("reason", "Timetable configuration needs attention."))
    target_window = next((w for w in windows["windows"] if w["sessionId"] == session_id), None)
    if not target_window:
        raise HTTPException(status_code=400, detail="Attendance session is invalid.")
    if not target_window["isOpen"]:
        raise HTTPException(status_code=403, detail=f"{target_window['label']} attendance is available only from {target_window['startTime']} to {target_window['endTime']} ({settings.TIMEZONE}).")

    # Prevent duplicate submission by either CR or LR for the same section on the same calendar day
    existing_query = {"year": req_year, "section": req_sec, "date": date_str, "session_id": session_id}
    existing_sub = await db.student_attendance_submissions.find_one(existing_query)
    if not existing_sub and session_id == "SESSION_1":
        existing_sub = await db.student_attendance_submissions.find_one({"year": req_year, "section": req_sec, "date": date_str, "session_id": {"$exists": False}})
    if existing_sub:
        prev_submitter = existing_sub.get("submitted_by", "a Class Representative")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"{session_id} attendance has already been submitted by {prev_submitter}.",
        )

    students = await db.students.find({"year": req_year, "section": req_sec}).to_list(length=5000)
    if not students:
        raise HTTPException(status_code=400, detail="No students are configured for this year and section.")
    absentees_by_roll = {ab.roll_number.strip().upper(): ab for ab in data.absentees}
    known_rolls = {str(s.get("roll_number", "")).strip().upper() for s in students}
    if set(absentees_by_roll) - known_rolls:
        raise HTTPException(status_code=400, detail="Attendance includes students outside your assigned section.")
    attendance_docs = []
    absent_rolls = list(absentees_by_roll)
    for student in students:
        r_num = str(student.get("roll_number", "")).strip().upper()
        if not r_num:
            continue
        ab = absentees_by_roll.get(r_num)
        doc = {
            "date": date_str, "year": req_year, "section": req_sec, "session_id": session_id,
            "branch": student.get("branch"),
            "roll_number": r_num,
            "student_id": str(student.get("_id", "")),
            "student_name": student.get("name", ""),
            "student_phone": student.get("student_phone"), "parent_phone": student.get("parent_phone"),
            "submitted_by": f"{current_user.get('name', 'CRLR')} ({user_role})",
            "submitted_by_id": str(current_user.get("id") or current_user.get("_id") or ""),
            "submitted_by_role": user_role,
            "status": "Absent" if ab else "Present", "reason": None,
            "created_at": now_utc, "updated_at": now_utc,
        }
        attendance_docs.append(doc)

    # Record submission marker
    submitter_display = f"{current_user.get('name', 'CRLR')} ({user_role})"
    sub_marker = {
        "year": req_year,
        "section": req_sec,
        "date": date_str,
        "session_id": session_id,
        "submitted_by": submitter_display,
        "submitted_by_role": user_role,
        "submitted_by_id": str(current_user.get("_id", "")),
        "absent_count": len(absent_rolls),
        "absent_rolls": absent_rolls,
        "timetable_updated_at": windows.get("timetableUpdatedAt"),
        "submitted_at": now_utc,
        "updated_at": now_utc,
    }
    try:
        await db.student_attendance_submissions.insert_one(sub_marker)
    except Exception:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"{session_id} attendance was already submitted. Refresh to see its status.") from None
    try:
        await _attendance_collection(db, session_id).insert_many(attendance_docs)
    except Exception:
        await db.student_attendance_submissions.delete_one({"year": req_year, "section": req_sec, "date": date_str, "session_id": session_id, "submitted_by_id": str(current_user.get("id") or current_user.get("_id") or "")})
        raise HTTPException(status_code=409, detail="Attendance could not be committed. Refresh and try again.") from None

    return {
        "message": f"Successfully submitted {session_id} attendance for {req_year} Section {req_sec}.",
        "date": date_str,
        "absent_count": len(absent_rolls),
        "submitted_by": submitter_display,
        "session_id": session_id,
    }


async def get_absentee_years() -> List[str]:
    """Dynamically get years available in student attendance or students DB."""
    db = get_database()
    att_years = await db.student_attendance.distinct("year")
    att_years += await db.student_attendance_sessions.distinct("year")
    stu_years = await db.students.distinct("year")
    
    def normalize_year(raw: str) -> Optional[str]:
        token = re.sub(r"[^a-z0-9]", "", raw.lower())
        for aliases, canonical in (
            ({"1", "1st", "1styear", "first", "firstyear", "i", "iyear"}, "1st Year"),
            ({"2", "2nd", "2ndyear", "second", "secondyear", "ii", "iiyear"}, "2nd Year"),
            ({"3", "3rd", "3rdyear", "third", "thirdyear", "iii", "iiiyear"}, "3rd Year"),
            ({"4", "4th", "4thyear", "fourth", "fourthyear", "iv", "ivyear"}, "4th Year"),
            ({"graduated", "alumni"}, "Graduated"),
        ):
            if token in aliases:
                return canonical
        return None
    order = {"1st Year": 0, "2nd Year": 1, "3rd Year": 2, "4th Year": 3, "Graduated": 4}
    all_years = {normalize_year(str(y)) for y in att_years + stu_years if y}
    return sorted((year for year in all_years if year), key=lambda year: order.get(year, 99))


async def get_absentee_sections(year: str) -> List[str]:
    """Get sections belonging to a year dynamically from uploaded timetables, students, and attendance records."""
    db = get_database()
    year_clean = year.strip()
    
    # Import student service helpers
    from app.services.student_service import build_year_filter_clause

    # Sections come from the timetable inventory where available. Student records
    # are a fallback for installations that have not uploaded timetables yet.
    tt_secs = await db.timetables.distinct("section", {"year": year_clean})
    
    # Also check roman numeral prefix in timetables (e.g. II-A for 2nd Year, III-A for 3rd Year)
    roman_map = {"1st Year": "I", "2nd Year": "II", "3rd Year": "III", "4th Year": "IV"}
    r_prefix = roman_map.get(year_clean)
    if r_prefix:
        all_tt_secs = await db.timetables.distinct("section")
        for s in all_tt_secs:
            if s and (s.startswith(f"{r_prefix}-") or f"-{r_prefix}-" in s):
                tt_secs.append(s)

    year_clause = build_year_filter_clause(year_clean)
    stu_secs = await db.students.distinct("section", year_clause) if year_clause else await db.students.distinct("section", {"year": year_clean})
    source_secs = tt_secs or stu_secs
    all_secs = sorted(list(set([s.upper().strip() for s in source_secs if s and s.strip()])))
    return all_secs


async def get_absentee_students_for_section(year: str, section: str, date: Optional[str] = None) -> List[StudentAttendanceRecordResponse]:
    """Get list of absentee students for a specific year and section on a date (default today)."""
    db = get_database()
    if not date:
        date = datetime.now(tz_kolkata).strftime("%Y-%m-%d")

    query = {
        "year": year,
        "section": section.upper(),
        "date": date,
        "status": "Absent",
    }
    docs = await _attendance_records(db, query)
    absentees = []
    for doc in sorted(docs, key=lambda d: (d.get("roll_number", ""), d.get("session_id", "SESSION_1"))):
        doc["_id"] = str(doc["_id"])
        absentees.append(StudentAttendanceRecordResponse(**doc))
    return absentees


async def save_absence_reason(
    record_id: str,
    reason: str,
    actor_name: str,
    actor_id: Optional[str] = None,
    actor_role: Optional[str] = None,
) -> StudentAttendanceRecordResponse:
    """Save or update the absence reason for a specific attendance record."""
    db = get_database()
    clean_id = (record_id or "").strip()

    doc = None
    source_collection = db.student_attendance
    if ObjectId.is_valid(clean_id):
        doc = await db.student_attendance.find_one({"_id": ObjectId(clean_id)})
        if not doc:
            doc = await db.student_attendance_sessions.find_one({"_id": ObjectId(clean_id)})
            if doc: source_collection = db.student_attendance_sessions
    if not doc:
        doc = await db.student_attendance.find_one({"_id": clean_id})
        if not doc:
            doc = await db.student_attendance_sessions.find_one({"_id": clean_id})
            if doc: source_collection = db.student_attendance_sessions
    if not doc:
        doc = await db.student_attendance_sessions.find_one({"roll_number": clean_id.upper(), "date": datetime.now(tz_kolkata).strftime("%Y-%m-%d")})
        if doc: source_collection = db.student_attendance_sessions
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
            doc = await db.student_attendance_sessions.find_one({"$or": [{"student_id": clean_id}, {"roll_number": clean_id.upper()}]}, sort=[("date", -1), ("created_at", -1)])
            if doc: source_collection = db.student_attendance_sessions
    if not doc:
        raise HTTPException(status_code=404, detail="Attendance record not found.")

    # Locking rule: If reason is already saved and non-empty, do not allow resubmission for mentors
    if doc.get("reason") and str(doc.get("reason")).strip():
        if actor_role in [UserRole.MENTOR.value, "MENTOR"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Absence reason has already been recorded and cannot be modified again.",
            )

    now_utc = datetime.now(timezone.utc)
    actual_id = doc["_id"]

    update_payload = {
        "reason": reason.strip(),
        "reason_updated_by": actor_name,
        "updated_at": now_utc,
    }
    if actor_id:
        update_payload["reason_updated_by_id"] = str(actor_id)

    await source_collection.update_one(
        {"_id": actual_id},
        {"$set": update_payload},
    )

    updated = await source_collection.find_one({"_id": actual_id})
    updated["_id"] = str(updated["_id"])
    return StudentAttendanceRecordResponse(**updated)


async def correct_student_attendance(
    record_id: Optional[str],
    data: StudentAttendanceCorrectRequest,
    current_user: dict,
) -> StudentAttendanceRecordResponse:
    """CR/LR and Admin can correct an absent student to Present with a mandatory audit reason."""
    db = get_database()
    now_local = datetime.now(tz_kolkata)
    now_utc = datetime.now(timezone.utc)
    user_role = current_user.get("role")
    user_sec = (current_user.get("section") or "").strip().upper()
    user_name = current_user.get("name", "Class Representative")
    user_id = str(current_user.get("_id", ""))

    # 1. Validate mandatory reason (reject empty or whitespace-only, min length 5)
    reason_str = (data.reason or "").strip()
    if len(reason_str) < 5:
        raise HTTPException(
            status_code=400,
            detail="A detailed mandatory reason is required to correct attendance (minimum 5 characters).",
        )

    # 2. Locate record by record_id or roll_number + date
    clean_id = (record_id or "").strip()
    doc = None
    source_collection = db.student_attendance
    if clean_id and ObjectId.is_valid(clean_id):
        doc = await db.student_attendance.find_one({"_id": ObjectId(clean_id)})
        if not doc:
            doc = await db.student_attendance_sessions.find_one({"_id": ObjectId(clean_id)})
            if doc: source_collection = db.student_attendance_sessions
    if not doc and clean_id:
        doc = await db.student_attendance.find_one({"_id": clean_id})
        if not doc:
            doc = await db.student_attendance_sessions.find_one({"_id": clean_id})
            if doc: source_collection = db.student_attendance_sessions
    if not doc and data.roll_number:
        r_clean = data.roll_number.strip().upper()
        target_date = data.date or now_local.strftime("%Y-%m-%d")
        query = {
            "roll_number": r_clean,
            "date": target_date,
        }
        if data.session_id:
            query["session_id"] = data.session_id
        doc = await db.student_attendance.find_one(query)
        if not doc and data.session_id == "SESSION_2":
            doc = await db.student_attendance_sessions.find_one(query)
            if doc: source_collection = db.student_attendance_sessions
    if not doc and clean_id:
        r_clean = clean_id.upper()
        target_date = data.date or now_local.strftime("%Y-%m-%d")
        query = {
            "roll_number": r_clean,
            "date": target_date,
        }
        if data.session_id:
            query["session_id"] = data.session_id
        doc = await db.student_attendance.find_one(query)
        if not doc and data.session_id == "SESSION_2":
            doc = await db.student_attendance_sessions.find_one(query)
            if doc: source_collection = db.student_attendance_sessions
    if not doc and data.roll_number:
        r_clean = data.roll_number.strip().upper()
        doc = await db.student_attendance.find_one({
            "roll_number": r_clean,
        }, sort=[("date", -1), ("created_at", -1)])
        if not doc:
            doc = await db.student_attendance_sessions.find_one({"roll_number": r_clean}, sort=[("date", -1), ("created_at", -1)])
            if doc: source_collection = db.student_attendance_sessions

    if not doc:
        raise HTTPException(status_code=404, detail="Student attendance record not found for correction.")

    # 3. RBAC & Section Authorization
    rec_sec = (doc.get("section") or "").strip().upper()
    rec_year = (doc.get("year") or "").strip()
    rec_date = doc.get("date") or now_local.strftime("%Y-%m-%d")
    roll_number = doc.get("roll_number")

    if user_role in ["CR", "LR"]:
        if user_sec and rec_sec != user_sec:
            raise HTTPException(
                status_code=403,
                detail=f"Access forbidden: You can only correct attendance for your assigned section ({user_sec}).",
            )

    # 4. Status update & Audit preservation
    new_status = data.new_status.strip().title() if data.new_status else "Present"
    old_status = doc.get("status", "Absent")

    actual_id = doc["_id"]
    update_payload = {
        "status": new_status,
        "original_status": doc.get("original_status") or old_status,
        "correction_reason": reason_str,
        "corrected_by": f"{user_name} ({user_role})",
        "corrected_by_role": user_role,
        "corrected_by_id": user_id,
        "corrected_at": now_utc,
        "updated_at": now_utc,
    }

    await source_collection.update_one(
        {"_id": actual_id},
        {"$set": update_payload},
    )

    # 5. Update student_attendance_submissions aggregate counts for the section
    if new_status == "Present" and old_status == "Absent":
        # Decrement absent count and remove roll number from absent_rolls
        await db.student_attendance_submissions.update_one(
            {"year": rec_year, "section": rec_sec, "date": rec_date, "session_id": doc.get("session_id")},
            {
                "$pull": {"absent_rolls": roll_number},
                "$inc": {"absent_count": -1},
                "$set": {"updated_at": now_utc},
            },
        )
        # Ensure absent_count doesn't drop below 0
        await db.student_attendance_submissions.update_one(
            {"year": rec_year, "section": rec_sec, "date": rec_date, "session_id": doc.get("session_id"), "absent_count": {"$lt": 0}},
            {"$set": {"absent_count": 0}},
        )

    # 6. Record Audit Log
    await db.audit_logs.insert_one({
        "actor_id": user_id,
        "actor_name": user_name,
        "actor_role": user_role,
        "action": "CORRECT_STUDENT_ATTENDANCE",
        "attendance_record_id": str(actual_id),
        "roll_number": roll_number,
        "year": rec_year,
        "section": rec_sec,
        "date": rec_date,
        "old_status": old_status,
        "new_status": new_status,
        "reason": reason_str,
        "created_at": now_utc,
    })

    updated = await source_collection.find_one({"_id": actual_id})
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

    distinct_dates = await db.student_attendance_submissions.distinct(
        "date", {"year": year_clean, "section": {"$in": sec_candidates}}
    )
    distinct_dates += await db.student_attendance_sessions.distinct("date", {"year": year_clean, "section": {"$in": sec_candidates}})
    total_days = len(distinct_dates) if distinct_dates else 0
    if total_days == 0:
        att_dates = await db.student_attendance.distinct("date", {"year": year_clean, "section": {"$in": sec_candidates}})
        att_dates += await db.student_attendance_sessions.distinct("date", {"year": year_clean, "section": {"$in": sec_candidates}})
        total_days = len(att_dates) if att_dates else 0

    student_rolls = [str(doc.get("roll_number") or "").strip().upper() for doc in students_docs]
    abs_query = {
        "year": year_clean,
        "section": {"$in": sec_candidates},
        "status": "Absent",
        "roll_number": {"$in": student_rolls},
    }
    abs_docs = await _attendance_records(db, abs_query) if student_rolls else []

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

        effective_days = max(total_days, abs_count, 1) if (total_days > 0 or abs_count > 0) else 0
        if effective_days == 0:
            pct = 100.0
        else:
            present_days = max(0, effective_days - abs_count)
            pct = round((present_days / effective_days) * 100, 1)

        result.append(StudentAnalyticsItem(
            student_id=str(s.get("_id", roll)),
            student_name=s.get("name", "Student"),
            roll_number=roll,
            year=year_clean,
            section=sec_clean,
            student_phone=s.get("student_phone"),
            parent_phone=s.get("parent_phone"),
            total_absences=abs_count,
            total_days=effective_days,
            attendance_percentage=pct,
        ))

    result.sort(key=lambda x: x.roll_number)
    return result


async def get_student_complete_history(roll_number: str) -> List[StudentAttendanceRecordResponse]:
    """Get complete absence history for a student sorted newest first."""
    db = get_database()
    roll_clean = roll_number.strip().upper()

    records = await _attendance_records(db, {"roll_number": roll_clean})
    history = []
    for doc in sorted(records, key=lambda d: d.get("date", ""), reverse=True):
        doc["_id"] = str(doc["_id"])
        if not doc.get("subject"):
            doc["subject"] = "Academic Session"
        if not doc.get("faculty"):
            doc["faculty"] = "Assigned Faculty"
        if not doc.get("session"):
            doc["session"] = "Regular Class Session"
        history.append(StudentAttendanceRecordResponse(**doc))
    return history
