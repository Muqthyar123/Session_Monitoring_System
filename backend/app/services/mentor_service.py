from datetime import datetime, timezone
import zoneinfo
from typing import List, Optional, Dict, Any, Set, Tuple
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
from app.schemas.user import UserRole
from app.services.mentor_mapping_service import (
    get_mentor_assigned_student_ids,
    is_student_assigned_to_mentor,
)
from app.services.planned_absence_service import batch_get_active_planned_absences_map
from app.services.student_service import (
    build_year_filter_clause,
    compute_year_from_batch,
    infer_batch_from_roll,
    sync_all_students_batch_and_year,
)

tz_kolkata = zoneinfo.ZoneInfo(settings.TIMEZONE)
STANDARD_YEARS = ["1st Year", "2nd Year", "3rd Year", "4th Year"]


async def _get_mentor_scoped_filter(current_user: Optional[dict]) -> Tuple[Optional[Dict[str, Any]], Optional[List[str]], Optional[List[str]]]:
    """
    Returns (student_filter_clause, assigned_ids, assigned_rolls) for DB queries.
    If current_user has ADMIN role or is None, returns (None, None, None) which means unrestricted.
    """
    if not current_user:
        return None, None, None

    role = current_user.get("role")
    if role in [UserRole.ADMIN.value, "ADMIN", "DEPARTMENT_COORDINATOR", "COORDINATOR"]:
        return None, None, None

    assigned_ids = await get_mentor_assigned_student_ids(current_user)
    if assigned_ids is None:
        return None, None, None

    if not assigned_ids:
        # Mentor has 0 assigned students
        return {"_id": {"$in": []}}, [], []

    valid_oids = [ObjectId(sid) for sid in assigned_ids if ObjectId.is_valid(sid)]
    db = get_database()
    # Fetch rolls for attendance queries
    rolls_cursor = db.students.find({"_id": {"$in": valid_oids}}, {"roll_number": 1})
    assigned_rolls = []
    async for doc in rolls_cursor:
        if doc.get("roll_number"):
            assigned_rolls.append(doc["roll_number"].upper().strip())

    student_filter = {"_id": {"$in": valid_oids}}
    return student_filter, assigned_ids, assigned_rolls


async def get_mentor_dashboard_data(current_user: dict) -> MentorDashboardResponse:
    db = get_database()
    today_date = datetime.now(tz_kolkata).strftime("%Y-%m-%d")

    # Synchronize student batch and year if any were unsynced
    await sync_all_students_batch_and_year(db)

    stu_filter, assigned_ids, assigned_rolls = await _get_mentor_scoped_filter(current_user)

    if stu_filter is not None and not assigned_ids:
        # Mentor has no assigned students
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
            totalStudents=0,
            totalAbsenteesToday=0,
            yearCounts=[],
            sectionCounts=[],
        )

    # 1. Total students
    base_stu_query = stu_filter if stu_filter else {}
    total_students = await db.students.count_documents(base_stu_query)

    # 2. Total absentees today
    att_today_query: Dict[str, Any] = {"date": today_date, "status": "Absent"}
    if assigned_ids is not None and assigned_rolls is not None:
        att_today_query["$or"] = [
            {"student_id": {"$in": assigned_ids}},
            {"roll_number": {"$in": assigned_rolls}},
        ]
    total_absentees_today = await db.student_attendance.count_documents(att_today_query)

    # 3. Dynamic years
    db_years = await db.students.distinct("year", base_stu_query)
    all_years = sorted(list(set([y for y in db_years if y] + (STANDARD_YEARS if stu_filter is None else []))))
    if not all_years and stu_filter is None:
        all_years = STANDARD_YEARS

    # 4. Year counts
    year_cards: List[MentorYearCard] = []
    for y in all_years:
        y_clause = build_year_filter_clause(y)
        clauses = [c for c in [base_stu_query, y_clause if y_clause else {"year": y}] if c]
        stu_q = {"$and": clauses} if len(clauses) > 1 else (clauses[0] if clauses else {})
        stu_cnt = await db.students.count_documents(stu_q)

        abs_q: Dict[str, Any] = {"year": y, "date": today_date, "status": "Absent"}
        if assigned_ids is not None and assigned_rolls is not None:
            abs_q["$or"] = [
                {"student_id": {"$in": assigned_ids}},
                {"roll_number": {"$in": assigned_rolls}},
            ]
        abs_cnt = await db.student_attendance.count_documents(abs_q)
        year_cards.append(MentorYearCard(
            year=y,
            studentCount=stu_cnt,
            absenteeCount=abs_cnt,
        ))

    # 5. Section counts
    match_stage = {"$match": base_stu_query} if base_stu_query else None
    pipeline: List[Dict[str, Any]] = []
    if match_stage:
        pipeline.append(match_stage)
    pipeline.extend([
        {
            "$group": {
                "_id": {"year": "$year", "section": "$section"},
                "count": {"$sum": 1},
            }
        },
        {"$sort": {"_id.year": 1, "_id.section": 1}},
    ])
    sections_cursor = db.students.aggregate(pipeline)
    section_cards: List[MentorSectionCard] = []
    async for item in sections_cursor:
        grp = item.get("_id", {})
        y = grp.get("year") or "2nd Year"
        s = grp.get("section") or "A"
        stu_cnt = item.get("count", 0)

        abs_sec_q: Dict[str, Any] = {
            "year": y,
            "section": s,
            "date": today_date,
            "status": "Absent",
        }
        if assigned_ids is not None and assigned_rolls is not None:
            abs_sec_q["$or"] = [
                {"student_id": {"$in": assigned_ids}},
                {"roll_number": {"$in": assigned_rolls}},
            ]
        abs_cnt = await db.student_attendance.count_documents(abs_sec_q)
        section_cards.append(MentorSectionCard(
            year=y,
            section=s,
            studentCount=stu_cnt,
            absenteeCount=abs_cnt,
        ))

    # Fallback if unassigned admin
    if not section_cards and stu_filter is None:
        for y in STANDARD_YEARS:
            for letter in ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J"]:
                sec_name = f"CSE-{letter}"
                section_cards.append(MentorSectionCard(
                    year=y,
                    section=sec_name,
                    studentCount=0,
                    absenteeCount=0,
                ))

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


async def get_mentor_years_summary(current_user: Optional[dict] = None) -> List[MentorYearCard]:
    """Retrieve list of years with student counts scoped by mentor assignment."""
    db = get_database()
    today_date = datetime.now(tz_kolkata).strftime("%Y-%m-%d")

    await sync_all_students_batch_and_year(db)

    stu_filter, assigned_ids, assigned_rolls = await _get_mentor_scoped_filter(current_user)
    if stu_filter is not None and not assigned_ids:
        return []

    base_stu_query = stu_filter if stu_filter else {}
    db_years = await db.students.distinct("year", base_stu_query)
    all_years = sorted(list(set([y for y in db_years if y] + (STANDARD_YEARS if stu_filter is None else []))))
    if not all_years and stu_filter is None:
        all_years = STANDARD_YEARS

    res: List[MentorYearCard] = []
    for y in all_years:
        y_clause = build_year_filter_clause(y)
        clauses = [c for c in [base_stu_query, y_clause if y_clause else {"year": y}] if c]
        stu_q = {"$and": clauses} if len(clauses) > 1 else (clauses[0] if clauses else {})
        stu_cnt = await db.students.count_documents(stu_q)

        abs_q: Dict[str, Any] = {"year": y, "date": today_date, "status": "Absent"}
        if assigned_ids is not None and assigned_rolls is not None:
            abs_q["$or"] = [
                {"student_id": {"$in": assigned_ids}},
                {"roll_number": {"$in": assigned_rolls}},
            ]
        abs_cnt = await db.student_attendance.count_documents(abs_q)
        res.append(MentorYearCard(
            year=y,
            studentCount=stu_cnt,
            absenteeCount=abs_cnt,
        ))
    return res


async def get_mentor_sections_summary(year: str, current_user: Optional[dict] = None) -> List[MentorSectionCard]:
    """Retrieve sections belonging to a year scoped by mentor assignment."""
    db = get_database()
    year_clean = year.strip()
    today_date = datetime.now(tz_kolkata).strftime("%Y-%m-%d")

    stu_filter, assigned_ids, assigned_rolls = await _get_mentor_scoped_filter(current_user)
    if stu_filter is not None and not assigned_ids:
        return []

    base_stu_query = stu_filter if stu_filter else {}
    y_clause = build_year_filter_clause(year_clean)
    clauses = [c for c in [base_stu_query, y_clause if y_clause else {"year": year_clean}] if c]
    sec_q = {"$and": clauses} if len(clauses) > 1 else (clauses[0] if clauses else {})

    db_secs = await db.students.distinct("section", sec_q)
    if not db_secs and stu_filter is None:
        db_secs = [f"CSE-{l}" for l in ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J"]]

    res: List[MentorSectionCard] = []
    for s in sorted(list(set(db_secs))):
        s_clause = {"section": s}
        all_clauses = [c for c in [sec_q, s_clause] if c]
        stu_cnt = await db.students.count_documents({"$and": all_clauses} if len(all_clauses) > 1 else all_clauses[0])

        abs_q: Dict[str, Any] = {
            "year": year_clean,
            "section": s,
            "date": today_date,
            "status": "Absent",
        }
        if assigned_ids is not None and assigned_rolls is not None:
            abs_q["$or"] = [
                {"student_id": {"$in": assigned_ids}},
                {"roll_number": {"$in": assigned_rolls}},
            ]
        abs_cnt = await db.student_attendance.count_documents(abs_q)
        res.append(MentorSectionCard(
            year=year_clean,
            section=s,
            studentCount=stu_cnt,
            absenteeCount=abs_cnt,
        ))
    return res


async def get_mentor_students_list(
    year: Optional[str] = None,
    section: Optional[str] = None,
    search: Optional[str] = None,
    current_user: Optional[dict] = None,
    limit: int = 1000,
) -> List[StudentResponse]:
    """Retrieve students scoped by mentor permissions and enriched with planned absences."""
    db = get_database()
    stu_filter, assigned_ids, assigned_rolls = await _get_mentor_scoped_filter(current_user)
    if stu_filter is not None and not assigned_ids:
        return []

    clauses: List[Dict[str, Any]] = []
    if stu_filter:
        clauses.append(stu_filter)

    if year:
        y_clause = build_year_filter_clause(year.strip())
        if y_clause:
            clauses.append(y_clause)
        else:
            clauses.append({"year": year.strip()})

    if section:
        clauses.append({"section": section.strip().upper()})

    if search:
        s_term = search.strip()
        clauses.append({
            "$or": [
                {"name": {"$regex": s_term, "$options": "i"}},
                {"roll_number": {"$regex": s_term, "$options": "i"}},
                {"section": {"$regex": s_term, "$options": "i"}},
            ]
        })

    query = {"$and": clauses} if len(clauses) > 1 else (clauses[0] if clauses else {})
    cursor = db.students.find(query).sort("roll_number", 1).limit(limit)

    student_docs: List[Dict[str, Any]] = []
    id_list: List[str] = []
    roll_list: List[str] = []
    async for s in cursor:
        s["_id"] = str(s["_id"])
        id_list.append(s["_id"])
        if s.get("roll_number"):
            roll_list.append(s["roll_number"].upper())
        student_docs.append(s)

    # Batch lookup active planned absences for today
    today_date = datetime.now(tz_kolkata).strftime("%Y-%m-%d")
    planned_map = await batch_get_active_planned_absences_map(id_list + roll_list, today_date)

    results: List[StudentResponse] = []
    for s in student_docs:
        if not s.get("batch") and s.get("roll_number"):
            s["batch"] = infer_batch_from_roll(s["roll_number"])
        if s.get("batch"):
            s["year"] = compute_year_from_batch(s["batch"])
        elif not s.get("year"):
            s["year"] = "2nd Year"

        # Check planned absence
        sid = s["_id"]
        sroll = (s.get("roll_number") or "").upper()
        pa = planned_map.get(sid) or (planned_map.get(sroll) if sroll else None)
        if pa:
            s["is_planned_absence"] = True
            s["planned_absence_reason"] = pa.get("reason")
            s["planned_absence_range"] = f"{pa.get('start_date')} to {pa.get('end_date')}"
            s["planned_absence_id"] = str(pa.get("_id") or pa.get("id"))
        else:
            s["is_planned_absence"] = False
            s["planned_absence_reason"] = None
            s["planned_absence_range"] = None
            s["planned_absence_id"] = None

        results.append(StudentResponse(**s))

    return results


async def search_students_global(
    search_term: str, current_user: Optional[dict] = None, limit: int = 100
) -> List[StudentResponse]:
    """Global case-insensitive partial search scoped by mentor assignment."""
    return await get_mentor_students_list(search=search_term, current_user=current_user, limit=limit)


async def get_mentor_absentee_years_summary(current_user: Optional[dict] = None) -> List[MentorYearCard]:
    """Retrieve years that have absentee records today scoped by mentor assignment."""
    db = get_database()
    today_date = datetime.now(tz_kolkata).strftime("%Y-%m-%d")

    await sync_all_students_batch_and_year(db)

    stu_filter, assigned_ids, assigned_rolls = await _get_mentor_scoped_filter(current_user)
    if stu_filter is not None and not assigned_ids:
        return []

    base_stu_query = stu_filter if stu_filter else {}
    att_today_query: Dict[str, Any] = {"date": today_date, "status": "Absent"}
    if assigned_ids is not None and assigned_rolls is not None:
        att_today_query["$or"] = [
            {"student_id": {"$in": assigned_ids}},
            {"roll_number": {"$in": assigned_rolls}},
        ]

    att_years = await db.student_attendance.distinct("year", att_today_query)
    stu_years = await db.students.distinct("year", base_stu_query)
    all_years = sorted(list(set(att_years + stu_years + (STANDARD_YEARS if stu_filter is None else []))))
    if not all_years and stu_filter is None:
        all_years = STANDARD_YEARS

    res: List[MentorYearCard] = []
    for y in all_years:
        abs_q = dict(att_today_query)
        abs_q["year"] = y
        abs_cnt = await db.student_attendance.count_documents(abs_q)

        y_clause = build_year_filter_clause(y)
        clauses = [c for c in [base_stu_query, y_clause if y_clause else {"year": y}] if c]
        stu_q = {"$and": clauses} if len(clauses) > 1 else (clauses[0] if clauses else {})
        stu_cnt = await db.students.count_documents(stu_q)

        res.append(MentorYearCard(
            year=y,
            studentCount=stu_cnt,
            absenteeCount=abs_cnt,
        ))
    return res


async def get_mentor_absentee_sections_summary(year: str, current_user: Optional[dict] = None) -> List[MentorSectionCard]:
    """Retrieve sections belonging to a year with today's absentee counts scoped by mentor assignment."""
    db = get_database()
    year_clean = year.strip()
    today_date = datetime.now(tz_kolkata).strftime("%Y-%m-%d")

    stu_filter, assigned_ids, assigned_rolls = await _get_mentor_scoped_filter(current_user)
    if stu_filter is not None and not assigned_ids:
        return []

    base_stu_query = stu_filter if stu_filter else {}
    att_today_query: Dict[str, Any] = {
        "year": year_clean,
        "date": today_date,
        "status": "Absent",
    }
    if assigned_ids is not None and assigned_rolls is not None:
        att_today_query["$or"] = [
            {"student_id": {"$in": assigned_ids}},
            {"roll_number": {"$in": assigned_rolls}},
        ]

    att_secs = await db.student_attendance.distinct("section", att_today_query)
    y_clause = build_year_filter_clause(year_clean)
    clauses = [c for c in [base_stu_query, y_clause if y_clause else {"year": year_clean}] if c]
    sec_q = {"$and": clauses} if len(clauses) > 1 else (clauses[0] if clauses else {})

    stu_secs = await db.students.distinct("section", sec_q)
    all_secs = sorted(list(set(att_secs + stu_secs)))
    if not all_secs and stu_filter is None:
        all_secs = [f"CSE-{l}" for l in ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J"]]

    res: List[MentorSectionCard] = []
    for s in all_secs:
        abs_q = dict(att_today_query)
        abs_q["section"] = s
        abs_cnt = await db.student_attendance.count_documents(abs_q)

        s_clause = {"section": s}
        all_clauses = [c for c in [sec_q, s_clause] if c]
        stu_cnt = await db.students.count_documents({"$and": all_clauses} if len(all_clauses) > 1 else all_clauses[0])

        res.append(MentorSectionCard(
            year=year_clean,
            section=s,
            studentCount=stu_cnt,
            absenteeCount=abs_cnt,
        ))
    return res


async def get_mentor_scoped_absentees(
    year: str,
    section: str,
    date: Optional[str] = None,
    current_user: Optional[dict] = None,
) -> List[StudentAttendanceRecordResponse]:
    """Retrieve absentee students for a section, scoped to mentor assignments and enriched with planned absences."""
    db = get_database()
    target_date = date.strip() if date else datetime.now(tz_kolkata).strftime("%Y-%m-%d")

    stu_filter, assigned_ids, assigned_rolls = await _get_mentor_scoped_filter(current_user)
    if stu_filter is not None and not assigned_ids:
        return []

    query: Dict[str, Any] = {
        "year": year.strip(),
        "section": section.strip().upper(),
        "date": target_date,
        "status": "Absent",
    }
    if assigned_ids is not None and assigned_rolls is not None:
        query["$or"] = [
            {"student_id": {"$in": assigned_ids}},
            {"roll_number": {"$in": assigned_rolls}},
        ]

    cursor = db.student_attendance.find(query).sort("roll_number", 1)

    records: List[Dict[str, Any]] = []
    id_list: List[str] = []
    roll_list: List[str] = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        if doc.get("student_id"):
            id_list.append(str(doc["student_id"]))
        if doc.get("roll_number"):
            roll_list.append(str(doc["roll_number"]).upper())
        records.append(doc)

    # Enrich with planned absence
    planned_map = await batch_get_active_planned_absences_map(id_list + roll_list, target_date)

    results: List[StudentAttendanceRecordResponse] = []
    for doc in records:
        sid = str(doc.get("student_id") or "")
        sroll = str(doc.get("roll_number") or "").upper()
        pa = planned_map.get(sid) or (planned_map.get(sroll) if sroll else None)
        if pa:
            doc["is_planned_absence"] = True
            doc["planned_absence_reason"] = pa.get("reason")
            doc["planned_absence_range"] = f"{pa.get('start_date')} to {pa.get('end_date')}"
            doc["planned_absence_id"] = str(pa.get("_id") or pa.get("id"))
        else:
            doc["is_planned_absence"] = False
            doc["planned_absence_reason"] = None
            doc["planned_absence_range"] = None
            doc["planned_absence_id"] = None
        results.append(StudentAttendanceRecordResponse(**doc))

    return results


async def search_absentees_global(
    search_term: str,
    date: Optional[str] = None,
    current_user: Optional[dict] = None,
) -> List[StudentAttendanceRecordResponse]:
    """Global search across absentees scoped by mentor assignment."""
    db = get_database()
    target_date = date.strip() if date else datetime.now(tz_kolkata).strftime("%Y-%m-%d")
    term = search_term.strip()
    if not term:
        return []

    stu_filter, assigned_ids, assigned_rolls = await _get_mentor_scoped_filter(current_user)
    if stu_filter is not None and not assigned_ids:
        return []

    search_clause = {
        "$or": [
            {"student_name": {"$regex": term, "$options": "i"}},
            {"roll_number": {"$regex": term, "$options": "i"}},
            {"section": {"$regex": term, "$options": "i"}},
        ]
    }

    base_query: Dict[str, Any] = {
        "date": target_date,
        "status": "Absent",
    }

    clauses = [base_query, search_clause]
    if assigned_ids is not None and assigned_rolls is not None:
        clauses.append({
            "$or": [
                {"student_id": {"$in": assigned_ids}},
                {"roll_number": {"$in": assigned_rolls}},
            ]
        })

    query = {"$and": clauses}
    cursor = db.student_attendance.find(query).sort("roll_number", 1)

    records: List[Dict[str, Any]] = []
    id_list: List[str] = []
    roll_list: List[str] = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        if doc.get("student_id"):
            id_list.append(str(doc["student_id"]))
        if doc.get("roll_number"):
            roll_list.append(str(doc["roll_number"]).upper())
        records.append(doc)

    planned_map = await batch_get_active_planned_absences_map(id_list + roll_list, target_date)

    results: List[StudentAttendanceRecordResponse] = []
    for doc in records:
        sid = str(doc.get("student_id") or "")
        sroll = str(doc.get("roll_number") or "").upper()
        pa = planned_map.get(sid) or (planned_map.get(sroll) if sroll else None)
        if pa:
            doc["is_planned_absence"] = True
            doc["planned_absence_reason"] = pa.get("reason")
            doc["planned_absence_range"] = f"{pa.get('start_date')} to {pa.get('end_date')}"
            doc["planned_absence_id"] = str(pa.get("_id") or pa.get("id"))
        else:
            doc["is_planned_absence"] = False
            doc["planned_absence_reason"] = None
            doc["planned_absence_range"] = None
            doc["planned_absence_id"] = None
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

    # Check RBAC
    user_role = current_user.get("role", "")
    if user_role == UserRole.MENTOR.value or user_role == "MENTOR":
        is_assigned = await is_student_assigned_to_mentor(str(doc.get("student_id") or doc.get("roll_number")), current_user)
        if not is_assigned:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. You can only update absence notes for your assigned students.",
            )

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
