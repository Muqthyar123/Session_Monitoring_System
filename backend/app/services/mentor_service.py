from datetime import datetime, timezone
import asyncio
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
)

import re

tz_kolkata = zoneinfo.ZoneInfo(settings.TIMEZONE)
STANDARD_YEARS = ["1st Year", "2nd Year", "3rd Year", "4th Year"]


async def _find_attendance(db, query: Dict[str, Any]) -> List[dict]:
    legacy = await db.student_attendance.find(query).to_list(length=50000)
    for row in legacy:
        row.setdefault("session_id", "SESSION_1")
    session_records = await db.student_attendance_sessions.find(query).to_list(length=50000)
    return legacy + session_records


async def _count_attendance(db, query: Dict[str, Any]) -> int:
    return (await db.student_attendance.count_documents(query)) + (await db.student_attendance_sessions.count_documents(query))


def _clean_section_code(sec: str) -> str:
    """Normalize section code, e.g. 'II-CSE-B' -> 'CSE-B', 'B' -> 'CSE-B', 'CSE-J' -> 'CSE-J', 'III-CSE-C1' -> 'CSE-C1'."""
    s = (sec or "").strip().upper()
    # Strip Roman year prefix if present: e.g. II-CSE-A -> CSE-A, III-CSE-C1 -> CSE-C1, IV-CSE-C4 -> CSE-C4
    s = re.sub(r'^(I{1,3}|IV|V|VI|[1-4])\s*[-_]\s*', '', s)
    # If bare single letter like 'A' or 'J', format as 'CSE-A', 'CSE-J'
    if len(s) == 1 and s.isalpha():
        s = f"CSE-{s}"
    elif re.match(r'^[CG]\d+$', s):
        s = f"CSE-{s}"
    return s


def _normalize_year_label(value: str) -> Optional[str]:
    token = re.sub(r"[^a-z0-9]", "", (value or "").lower())
    if token.startswith(("4", "iv", "fourth")):
        return "4th Year"
    if token.startswith(("3", "iii", "third")):
        return "3rd Year"
    if token.startswith(("2", "ii", "second")):
        return "2nd Year"
    if token.startswith(("1", "i", "first")):
        return "1st Year"
    return None


def _get_section_query_clauses(sec: str) -> List[Dict[str, Any]]:
    clean = _clean_section_code(sec)
    raw = (sec or "").strip()
    raw_tail = raw.split("-")[-1].strip().upper()
    clean_tail = clean.split("-")[-1].strip().upper()
    return [
        {"section": clean},
        {"section": raw},
        {"section": clean_tail},
        {"section": raw_tail},
        {"section": f"CSE-{clean_tail}"},
        {"section": f"II-CSE-{clean_tail}"},
        {"section": f"III-CSE-{clean_tail}"},
        {"section": f"IV-CSE-{clean_tail}"},
        {"section": {"$regex": f"(^|-){re.escape(clean_tail)}$", "$options": "i"}},
    ]


async def _get_active_planned_absence_keys(date_str: str) -> Set[str]:
    db = get_database()
    cursor = db.planned_absences.find({
        "status": "ACTIVE",
        "start_date": {"$lte": date_str},
        "end_date": {"$gte": date_str},
    }, {"student_id": 1, "roll_number": 1})
    keys: Set[str] = set()
    async for doc in cursor:
        if doc.get("student_id"):
            keys.add(str(doc["student_id"]))
        if doc.get("roll_number"):
            keys.add(str(doc["roll_number"]).upper().strip())
    return keys


async def _get_canonical_sections_for_year(year_clean: str, base_stu_query: Optional[Dict[str, Any]] = None) -> List[str]:
    db = get_database()
    target_year = _normalize_year_label(year_clean)
    if not target_year:
        return []

    sections: Set[str] = set()

    # 1. Timetable inventory
    timetable_docs = await db.timetables.find({}).to_list(length=10000)
    for timetable in timetable_docs:
        if _normalize_year_label(timetable.get("year") or "") != target_year:
            continue
        code = _clean_section_code(timetable.get("section") or "")
        if code:
            sections.add(code)

    # 2. Persisted student roster (ensure all enrolled students map to their respective section card)
    query_clauses = [build_year_filter_clause(target_year)]
    if base_stu_query:
        query_clauses.insert(0, base_stu_query)
    roster_query = {"$and": query_clauses} if len(query_clauses) > 1 else query_clauses[0]
    for raw_section in await db.students.distinct("section", roster_query):
        code = _clean_section_code(raw_section or "")
        if code:
            sections.add(code)

    # 3. Fallback to registered sections if none found yet
    if not sections:
        sec_docs = await db.sections.find({"is_active": {"$ne": False}}).to_list(length=1000)
        for s_doc in sec_docs:
            if _normalize_year_label(s_doc.get("year") or "") != target_year:
                continue
            code = _clean_section_code(s_doc.get("section_name") or s_doc.get("sectionName") or "")
            if code:
                sections.add(code)

    return sorted(sections)


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


async def get_mentor_sections_summary(year: str, current_user: Optional[dict] = None) -> List[MentorSectionCard]:
    """Retrieve sections belonging to a year scoped by mentor assignment with deduplication."""
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

    all_secs = await _get_canonical_sections_for_year(year_clean, base_stu_query)
    if not all_secs:
        return []
    active_pa_keys = await _get_active_planned_absence_keys(today_date)

    student_counts = {section: 0 for section in all_secs}
    student_cursor = db.students.find(sec_q, {"section": 1})
    async for student in student_cursor:
        code = _clean_section_code(student.get("section") or "")
        if code in student_counts:
            student_counts[code] += 1

    section_variants = [clause for section in all_secs for clause in _get_section_query_clauses(section)]
    attendance_clauses: List[Dict[str, Any]] = [
        {"year": year_clean},
        {"$or": section_variants},
        {"date": today_date},
        {"status": "Absent"},
    ]
    if assigned_ids is not None and assigned_rolls is not None:
        attendance_clauses.append({"$or": [
            {"student_id": {"$in": assigned_ids}},
            {"roll_number": {"$in": assigned_rolls}},
        ]})
    if active_pa_keys:
        attendance_clauses.append({"$nor": [
            {"student_id": {"$in": list(active_pa_keys)}},
            {"roll_number": {"$in": list(active_pa_keys)}},
        ]})
    attendance_counts = {section: 0 for section in all_secs}
    attendance_rows = await _find_attendance(db, {"$and": attendance_clauses})
    for record in attendance_rows:
        code = _clean_section_code(record.get("section") or "")
        if code in attendance_counts:
            attendance_counts[code] += 1

    res: List[MentorSectionCard] = []
    for s in all_secs:
        res.append(MentorSectionCard(
            year=year_clean,
            section=s,
            studentCount=student_counts[s],
            absenteeCount=attendance_counts[s],
        ))
    return res


async def get_mentor_dashboard_data(current_user: dict) -> MentorDashboardResponse:
    db = get_database()
    today_date = datetime.now(tz_kolkata).strftime("%Y-%m-%d")

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

    # 2. Total absentees today (excluding active planned leaves)
    active_pa_keys = await _get_active_planned_absence_keys(today_date)
    att_today_query: Dict[str, Any] = {"date": today_date, "status": "Absent"}
    if assigned_ids is not None and assigned_rolls is not None:
        att_today_query["$or"] = [
            {"student_id": {"$in": assigned_ids}},
            {"roll_number": {"$in": assigned_rolls}},
        ]
    if active_pa_keys:
        att_today_query["$nor"] = [
            {"student_id": {"$in": list(active_pa_keys)}},
            {"roll_number": {"$in": list(active_pa_keys)}},
        ]
    total_absentees_today = await _count_attendance(db, att_today_query)

    # Session-wise attendance snapshot from persisted MongoDB records.
    session_query: Dict[str, Any] = {"date": today_date}
    if assigned_ids is not None and assigned_rolls is not None:
        session_query["$or"] = [{"student_id": {"$in": assigned_ids}}, {"roll_number": {"$in": assigned_rolls}}]
    today_records = await _find_attendance(db, session_query)
    session_summaries = []
    for session_id, label in (("SESSION_1", "Before Lunch"), ("SESSION_2", "After Lunch")):
        rows = [row for row in today_records if row.get("session_id") == session_id]
        present = sum(1 for row in rows if row.get("status") == "Present")
        absent = sum(1 for row in rows if row.get("status") == "Absent")
        pairs = {(row.get("year"), row.get("section")) for row in rows}
        markers = []
        for year_value, section_value in pairs:
            marker = await db.student_attendance_submissions.find_one({"year": year_value, "section": section_value, "date": today_date, "session_id": session_id})
            if marker:
                markers.append(marker)
        session_summaries.append({"sessionId": session_id, "label": label, "present": present, "absent": absent,
            "total": present + absent, "attendancePercentage": round(present * 100 / (present + absent), 1) if present + absent else 0,
            "completedSubmissions": len(markers), "submissionDetails": [{"year": marker.get("year"), "section": marker.get("section"), "submittedBy": marker.get("submitted_by"), "submittedAt": marker.get("submitted_at")} for marker in markers]})
    absent_sessions_by_student: Dict[str, set] = {}
    for row in today_records:
        if row.get("status") == "Absent":
            absent_sessions_by_student.setdefault(str(row.get("student_id") or row.get("roll_number")), set()).add(row.get("session_id"))
    absent_both = sum(1 for values in absent_sessions_by_student.values() if {"SESSION_1", "SESSION_2"}.issubset(values))
    absent_one = sum(1 for values in absent_sessions_by_student.values() if len(values) == 1)

    # 3. Dynamic years
    db_years = await db.students.distinct("year", base_stu_query)
    all_years = sorted(list(set([y for y in db_years if y] + (STANDARD_YEARS if stu_filter is None else []))))
    if not all_years and stu_filter is None:
        all_years = STANDARD_YEARS

    # 4. Year counts
    year_cards: List[MentorYearCard] = []
    for y in all_years:
        y_clause = build_year_filter_clause(y)
        canonical_sections = await _get_canonical_sections_for_year(y, base_stu_query)
        if not canonical_sections:
            continue
        year_clauses = [c for c in [base_stu_query, y_clause if y_clause else {"year": y}] if c]
        year_q = {"$and": year_clauses} if len(year_clauses) > 1 else (year_clauses[0] if year_clauses else {})
        stu_cnt = await db.students.count_documents(year_q)
        section_clauses = [clause for section in canonical_sections for clause in _get_section_query_clauses(section)]
        mapped_q = {"$and": [year_q, {"$or": section_clauses}]}
        mapped_count = await db.students.count_documents(mapped_q)

        abs_clauses = [
            {"year": y},
            {"date": today_date},
            {"status": "Absent"},
        ]
        if assigned_ids is not None and assigned_rolls is not None:
            abs_clauses.append({
                "$or": [
                    {"student_id": {"$in": assigned_ids}},
                    {"roll_number": {"$in": assigned_rolls}},
                ]
            })
        if active_pa_keys:
            abs_clauses.append({
                "$nor": [
                    {"student_id": {"$in": list(active_pa_keys)}},
                    {"roll_number": {"$in": list(active_pa_keys)}},
                ]
            })
        abs_cnt = await _count_attendance(db, {"$and": abs_clauses})
        year_cards.append(MentorYearCard(
            year=y,
            studentCount=stu_cnt,
            absenteeCount=abs_cnt,
        ))

    # 5. Section counts (canonical sections for each year, deduplicated)
    section_cards: List[MentorSectionCard] = []
    for y in all_years:
        sec_list = await get_mentor_sections_summary(y, current_user)
        section_cards.extend(sec_list)

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
        attendanceSessions=session_summaries,
        absentBothSessions=absent_both,
        absentOneSession=absent_one,
    )


async def get_mentor_years_summary(current_user: Optional[dict] = None) -> List[MentorYearCard]:
    """Retrieve list of years with student counts scoped by mentor assignment."""
    db = get_database()
    today_date = datetime.now(tz_kolkata).strftime("%Y-%m-%d")

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

        active_pa_keys = await _get_active_planned_absence_keys(today_date)
        abs_clauses = [
            {"year": y},
            {"date": today_date},
            {"status": "Absent"},
        ]
        if assigned_ids is not None and assigned_rolls is not None:
            abs_clauses.append({
                "$or": [
                    {"student_id": {"$in": assigned_ids}},
                    {"roll_number": {"$in": assigned_rolls}},
                ]
            })
        if active_pa_keys:
            abs_clauses.append({
                "$nor": [
                    {"student_id": {"$in": list(active_pa_keys)}},
                    {"roll_number": {"$in": list(active_pa_keys)}},
                ]
            })
        abs_cnt = await _count_attendance(db, {"$and": abs_clauses})
        res.append(MentorYearCard(
            year=y,
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
        clauses.append({"$or": _get_section_query_clauses(section.strip())})

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

    # Derive cards from both the timetable inventory and persisted student roster.
    # This keeps uploaded student years discoverable even when timetable data is
    # incomplete, while the student count below still scopes cards to real records.
    timetable_years, roster_years = await asyncio.gather(
        db.timetables.distinct("year"),
        db.students.distinct("year", base_stu_query),
    )
    all_years = sorted({
        normalized
        for raw_year in timetable_years + roster_years
        if (normalized := _normalize_year_label(raw_year or ""))
    }, key=lambda item: STANDARD_YEARS.index(item) if item in STANDARD_YEARS else len(STANDARD_YEARS))

    active_pa_keys = await _get_active_planned_absence_keys(today_date)
    res: List[MentorYearCard] = []
    for y in all_years:
        abs_clauses = [
            {"year": y},
            {"date": today_date},
            {"status": "Absent"},
        ]
        if assigned_ids is not None and assigned_rolls is not None:
            abs_clauses.append({
                "$or": [
                    {"student_id": {"$in": assigned_ids}},
                    {"roll_number": {"$in": assigned_rolls}},
                ]
            })
        if active_pa_keys:
            abs_clauses.append({
                "$nor": [
                    {"student_id": {"$in": list(active_pa_keys)}},
                    {"roll_number": {"$in": list(active_pa_keys)}},
                ]
            })
        abs_cnt = await _count_attendance(db, {"$and": abs_clauses})

        y_clause = build_year_filter_clause(y)
        clauses = [c for c in [base_stu_query, y_clause if y_clause else {"year": y}] if c]
        stu_q = {"$and": clauses} if len(clauses) > 1 else (clauses[0] if clauses else {})
        stu_cnt = await db.students.count_documents(stu_q)

        canonical_sections = await _get_canonical_sections_for_year(y, base_stu_query)
        section_clauses = [
            clause
            for section_doc in canonical_sections
            for clause in _get_section_query_clauses(section_doc)
        ]
        mapped_count = await db.students.count_documents({"$and": [stu_q, {"$or": section_clauses}]}) if section_clauses else 0

        if stu_filter is not None and stu_cnt == 0:
            continue

        res.append(MentorYearCard(
            year=y,
            studentCount=stu_cnt,
            absenteeCount=abs_cnt,
            unassignedStudentCount=max(0, stu_cnt - mapped_count),
        ))
    return res


async def get_mentor_absentee_sections_summary(year: str, current_user: Optional[dict] = None) -> List[MentorSectionCard]:
    """Retrieve sections belonging to a year with today's absentee counts scoped by mentor assignment."""
    return await get_mentor_sections_summary(year, current_user)


async def get_mentor_scoped_absentees(
    year: str,
    section: str,
    date: Optional[str] = None,
    current_user: Optional[dict] = None,
    include_planned: bool = False,
) -> List[StudentAttendanceRecordResponse]:
    """Retrieve absentee students for a section, scoped to mentor assignments and excluding active planned absences."""
    db = get_database()
    target_date = date.strip() if date else datetime.now(tz_kolkata).strftime("%Y-%m-%d")

    stu_filter, assigned_ids, assigned_rolls = await _get_mentor_scoped_filter(current_user)
    if stu_filter is not None and not assigned_ids:
        return []

    sec_variants = _get_section_query_clauses(section)
    query_clauses: List[Dict[str, Any]] = [
        {"year": year.strip()},
        {"$or": sec_variants},
        {"date": target_date},
        {"status": "Absent"},
    ]
    if assigned_ids is not None and assigned_rolls is not None:
        query_clauses.append({
            "$or": [
                {"student_id": {"$in": assigned_ids}},
                {"roll_number": {"$in": assigned_rolls}},
            ]
        })

    records: List[Dict[str, Any]] = []
    id_list: List[str] = []
    roll_list: List[str] = []
    for doc in sorted(await _find_attendance(db, {"$and": query_clauses}), key=lambda row: row.get("roll_number", "")):
        doc["_id"] = str(doc["_id"])
        if doc.get("student_id"):
            id_list.append(str(doc["student_id"]))
        if doc.get("roll_number"):
            roll_list.append(str(doc["roll_number"]).upper())
        records.append(doc)

    # Check active planned absences
    planned_map = await batch_get_active_planned_absences_map(id_list + roll_list, target_date)

    results: List[StudentAttendanceRecordResponse] = []
    for doc in records:
        sid = str(doc.get("student_id") or "")
        sroll = str(doc.get("roll_number") or "").upper()
        pa = planned_map.get(sid) or (planned_map.get(sroll) if sroll else None)
        # CRITICAL USER RULE:
        # If student has an active planned absence covering this date, exclude from Today's Absentees unless include_planned=True!
        if pa:
            if not include_planned:
                continue
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
    """Global search across absentees scoped by mentor assignment, excluding active planned absences."""
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
    records: List[Dict[str, Any]] = []
    id_list: List[str] = []
    roll_list: List[str] = []
    for doc in sorted(await _find_attendance(db, query), key=lambda row: row.get("roll_number", "")):
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
            continue
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
        today_date = datetime.now(tz_kolkata).strftime("%Y-%m-%d")
        doc = await db.student_attendance.find_one({
            "roll_number": clean_id.upper(),
            "date": today_date,
        })
        if not doc:
            doc = await db.student_attendance_sessions.find_one({"roll_number": clean_id.upper(), "date": today_date})
            if doc: source_collection = db.student_attendance_sessions
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

    # Check RBAC
    user_role = current_user.get("role", "")
    if user_role == UserRole.MENTOR.value or user_role == "MENTOR":
        is_assigned = await is_student_assigned_to_mentor(str(doc.get("student_id") or doc.get("roll_number")), current_user)
        if not is_assigned:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. You can only update absence notes for your assigned students.",
            )

    # Locking rule: If reason is already saved and non-empty, do not allow resubmission for mentors
    if doc.get("reason") and str(doc.get("reason")).strip():
        if user_role in [UserRole.MENTOR.value, "MENTOR"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Absence note has already been recorded and cannot be modified again.",
            )

    now_utc = datetime.now(timezone.utc)
    actor_name = current_user.get("name", "Mentor")
    actual_id = doc["_id"]

    await source_collection.update_one(
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

    updated = await source_collection.find_one({"_id": actual_id})
    updated["_id"] = str(updated["_id"])
    return StudentAttendanceRecordResponse(**updated)
