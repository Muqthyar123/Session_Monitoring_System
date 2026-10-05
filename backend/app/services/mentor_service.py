from datetime import datetime, timezone
import zoneinfo
from typing import List, Optional, Dict, Any
from bson import ObjectId
from fastapi import HTTPException, status
from app.core.config import settings
from app.db.mongodb import get_database
from app.schemas.mentor import (
    MentorDashboardResponse,
    MentorInfo,
    MentorSectionCard,
    MentorYearCard,
)
from app.schemas.student import StudentResponse
from app.schemas.student_attendance import StudentAttendanceRecordResponse
from app.services.student_service import (
    build_year_filter_clause,
    compute_year_from_batch,
    infer_batch_from_roll,
    sync_all_students_batch_and_year,
)

tz_kolkata = zoneinfo.ZoneInfo(settings.TIMEZONE)

STANDARD_YEARS = ["1st Year", "2nd Year", "3rd Year", "4th Year"]


async def get_mentor_dashboard_data(current_user: dict) -> MentorDashboardResponse:
    db = get_database()
    today_date = datetime.now(tz_kolkata).strftime("%Y-%m-%d")

    # Synchronize student batch and year if any were unsynced
    await sync_all_students_batch_and_year(db)

    # 1. Total students
    total_students = await db.students.count_documents({})

    # 2. Total absentees today
    total_absentees_today = await db.student_attendance.count_documents({
        "date": today_date,
        "status": "Absent",
    })

    # 3. Dynamic years in database
    db_years = await db.students.distinct("year")
    all_years = sorted(list(set([y for y in db_years if y] + STANDARD_YEARS)))

    # 4. Year counts (students + absentees today)
    year_cards: List[MentorYearCard] = []
    for y in all_years:
        y_clause = build_year_filter_clause(y)
        stu_cnt = await db.students.count_documents(y_clause) if y_clause else await db.students.count_documents({"year": y})
        abs_cnt = await db.student_attendance.count_documents({
            "year": y,
            "date": today_date,
            "status": "Absent",
        })
        year_cards.append(MentorYearCard(
            year=y,
            studentCount=stu_cnt,
            absenteeCount=abs_cnt,
        ))

    # 5. Section counts
    section_cards: List[MentorSectionCard] = []
    sections_cursor = db.students.aggregate([
        {
            "$group": {
                "_id": {"year": "$year", "section": "$section"},
                "count": {"$sum": 1},
            }
        },
        {"$sort": {"_id.year": 1, "_id.section": 1}},
    ])
    async for item in sections_cursor:
        grp = item.get("_id", {})
        y = grp.get("year") or "2nd Year"
        s = grp.get("section") or "A"
        stu_cnt = item.get("count", 0)
        abs_cnt = await db.student_attendance.count_documents({
            "year": y,
            "section": s,
            "date": today_date,
            "status": "Absent",
        })
        section_cards.append(MentorSectionCard(
            year=y,
            section=s,
            studentCount=stu_cnt,
            absenteeCount=abs_cnt,
        ))

    # If no sections in DB yet, populate default CSE-A to CSE-J for each year
    if not section_cards:
        for y in STANDARD_YEARS:
            for letter in ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J"]:
                sec_name = f"CSE-{letter}"
                section_cards.append(MentorSectionCard(
                    year=y,
                    section=sec_name,
                    studentCount=0,
                    absenteeCount=0,
                ))

    # 6. Mentor info
    mentor_info = MentorInfo(
        id=str(current_user["_id"]),
        name=current_user.get("name", "Mentor"),
        email=current_user.get("email"),
        mentorId=current_user.get("mentor_id") or current_user.get("roll_number"),
        phone=current_user.get("phone"),
        department=current_user.get("department", "CSE"),
        designation=current_user.get("designation", "Faculty Mentor"),
        role=current_user.get("role", "MENTOR"),
    )

    return MentorDashboardResponse(
        mentorInfo=mentor_info,
        totalStudents=total_students,
        totalAbsenteesToday=total_absentees_today,
        yearCounts=year_cards,
        sectionCounts=section_cards,
    )


async def get_mentor_years_summary() -> List[MentorYearCard]:
    """Retrieve dynamic list of years with total student counts."""
    db = get_database()
    today_date = datetime.now(tz_kolkata).strftime("%Y-%m-%d")

    await sync_all_students_batch_and_year(db)

    db_years = await db.students.distinct("year")
    all_years = sorted(list(set([y for y in db_years if y] + STANDARD_YEARS)))

    res: List[MentorYearCard] = []
    for y in all_years:
        y_clause = build_year_filter_clause(y)
        stu_cnt = await db.students.count_documents(y_clause) if y_clause else await db.students.count_documents({"year": y})
        abs_cnt = await db.student_attendance.count_documents({
            "year": y,
            "date": today_date,
            "status": "Absent",
        })
        res.append(MentorYearCard(
            year=y,
            studentCount=stu_cnt,
            absenteeCount=abs_cnt,
        ))
    return res


async def get_mentor_sections_summary(year: str) -> List[MentorSectionCard]:
    """Retrieve sections belonging to a year with student and today's absentee counts."""
    db = get_database()
    year_clean = year.strip()
    today_date = datetime.now(tz_kolkata).strftime("%Y-%m-%d")

    y_clause = build_year_filter_clause(year_clean)
    db_secs = await db.students.distinct("section", y_clause) if y_clause else await db.students.distinct("section", {"year": year_clean})
    if not db_secs:
        db_secs = [f"CSE-{l}" for l in ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J"]]

    res: List[MentorSectionCard] = []
    for s in sorted(list(set(db_secs))):
        s_clause = {"section": s}
        if y_clause:
            query = {"$and": [s_clause, y_clause]}
        else:
            query = {"year": year_clean, "section": s}
        stu_cnt = await db.students.count_documents(query)
        abs_cnt = await db.student_attendance.count_documents({
            "year": year_clean,
            "section": s,
            "date": today_date,
            "status": "Absent",
        })
        res.append(MentorSectionCard(
            year=year_clean,
            section=s,
            studentCount=stu_cnt,
            absenteeCount=abs_cnt,
        ))
    return res


async def search_students_global(search_term: str, limit: int = 100) -> List[StudentResponse]:
    """Global case-insensitive partial search across all students by name or roll number."""
    db = get_database()
    term = search_term.strip()
    if not term:
        return []

    query = {
        "$or": [
            {"name": {"$regex": term, "$options": "i"}},
            {"roll_number": {"$regex": term, "$options": "i"}},
            {"section": {"$regex": term, "$options": "i"}},
        ]
    }

    cursor = db.students.find(query).limit(limit).sort("roll_number", 1)
    results: List[StudentResponse] = []
    async for s in cursor:
        s["_id"] = str(s["_id"])
        if not s.get("batch") and s.get("roll_number"):
            s["batch"] = infer_batch_from_roll(s["roll_number"])
        if s.get("batch"):
            s["year"] = compute_year_from_batch(s["batch"])
        elif not s.get("year"):
            s["year"] = "2nd Year"
        results.append(StudentResponse(**s))
    return results


async def get_mentor_absentee_years_summary() -> List[MentorYearCard]:
    """Retrieve years that have absentee records today with accurate student count."""
    db = get_database()
    today_date = datetime.now(tz_kolkata).strftime("%Y-%m-%d")

    await sync_all_students_batch_and_year(db)

    att_years = await db.student_attendance.distinct("year", {"date": today_date, "status": "Absent"})
    all_years = sorted(list(set(att_years + STANDARD_YEARS)))

    res: List[MentorYearCard] = []
    for y in all_years:
        abs_cnt = await db.student_attendance.count_documents({
            "year": y,
            "date": today_date,
            "status": "Absent",
        })
        y_clause = build_year_filter_clause(y)
        stu_cnt = await db.students.count_documents(y_clause) if y_clause else await db.students.count_documents({"year": y})
        res.append(MentorYearCard(
            year=y,
            studentCount=stu_cnt,
            absenteeCount=abs_cnt,
        ))
    return res


async def get_mentor_absentee_sections_summary(year: str) -> List[MentorSectionCard]:
    """Retrieve sections belonging to a year with today's absentee counts."""
    db = get_database()
    year_clean = year.strip()
    today_date = datetime.now(tz_kolkata).strftime("%Y-%m-%d")

    att_secs = await db.student_attendance.distinct("section", {
        "year": year_clean,
        "date": today_date,
        "status": "Absent",
    })
    y_clause = build_year_filter_clause(year_clean)
    stu_secs = await db.students.distinct("section", y_clause) if y_clause else await db.students.distinct("section", {"year": year_clean})
    all_secs = sorted(list(set(att_secs + stu_secs)))
    if not all_secs:
        all_secs = [f"CSE-{l}" for l in ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J"]]

    res: List[MentorSectionCard] = []
    for s in all_secs:
        abs_cnt = await db.student_attendance.count_documents({
            "year": year_clean,
            "section": s,
            "date": today_date,
            "status": "Absent",
        })
        s_clause = {"section": s}
        query = {"$and": [s_clause, y_clause]} if y_clause else {"year": year_clean, "section": s}
        stu_cnt = await db.students.count_documents(query)
        res.append(MentorSectionCard(
            year=year_clean,
            section=s,
            studentCount=stu_cnt,
            absenteeCount=abs_cnt,
        ))
    return res


async def search_absentees_global(search_term: str, date: Optional[str] = None) -> List[StudentAttendanceRecordResponse]:
    """Global search across today's absentees by name or roll number."""
    db = get_database()
    if not date:
        date = datetime.now(tz_kolkata).strftime("%Y-%m-%d")

    term = search_term.strip()
    if not term:
        return []

    query = {
        "date": date,
        "status": "Absent",
        "$or": [
            {"student_name": {"$regex": term, "$options": "i"}},
            {"roll_number": {"$regex": term, "$options": "i"}},
            {"section": {"$regex": term, "$options": "i"}},
        ],
    }

    cursor = db.student_attendance.find(query).sort("roll_number", 1)
    results: List[StudentAttendanceRecordResponse] = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        results.append(StudentAttendanceRecordResponse(**doc))
    return results


async def update_absence_comment(
    record_id: str, comment: str, current_user: dict
) -> StudentAttendanceRecordResponse:
    """Save or update absence reason/comment by mentor."""
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
    actor_name = current_user.get("name", "Mentor")
    actual_id = doc["_id"]

    await db.student_attendance.update_one(
        {"_id": actual_id},
        {
            "$set": {
                "reason": comment.strip(),
                "reason_updated_by": actor_name,
                "reason_updated_by_id": str(current_user.get("_id", "")),
                "updated_at": now_utc,
            }
        },
    )

    # Audit log
    await db.audit_logs.insert_one({
        "actor_id": str(current_user.get("_id", "")),
        "actor_email": current_user.get("email"),
        "action": "UPDATE_ABSENCE_COMMENT",
        "target_attendance_id": str(actual_id),
        "metadata": {"comment": comment.strip(), "student": doc.get("student_name")},
        "created_at": now_utc,
    })

    updated = await db.student_attendance.find_one({"_id": actual_id})
    updated["_id"] = str(updated["_id"])
    return StudentAttendanceRecordResponse(**updated)
