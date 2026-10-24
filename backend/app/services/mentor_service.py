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

import re

tz_kolkata = zoneinfo.ZoneInfo(settings.TIMEZONE)
STANDARD_YEARS = ["1st Year", "2nd Year", "3rd Year", "4th Year"]


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
    # 1. Configured sections in db.sections
    configured_sec_docs = await db.sections.find({"year": year_clean}).to_list(100)
    configured_secs: List[str] = []
    seen: Set[str] = set()
    for doc in configured_sec_docs:
        s_name = doc.get("section_name") or doc.get("section") or ""
        code = _clean_section_code(s_name)
        if code and code not in seen:
            seen.add(code)
            configured_secs.append(code)

    # 2. Check student sections enrolled in this year
    y_clause = build_year_filter_clause(year_clean)
    clauses = [c for c in [base_stu_query, y_clause if y_clause else {"year": year_clean}] if c]
    sec_q = {"$and": clauses} if len(clauses) > 1 else (clauses[0] if clauses else {})
    stu_secs_raw = await db.students.distinct("section", sec_q)
    stu_clean_secs = {_clean_section_code(x) for x in stu_secs_raw if x}

    if configured_secs:
        all_secs = list(configured_secs)
        for cs in sorted(list(stu_clean_secs)):
            if cs not in seen:
                cnt = await db.students.count_documents({"year": year_clean, "$or": _get_section_query_clauses(cs)})
                if cnt >= 5:
                    seen.add(cs)
                    all_secs.append(cs)
        return sorted(all_secs)
    elif stu_clean_secs:
        return sorted(list(stu_clean_secs))
    else:
        if "2" in year_clean:
            return [f"CSE-{l}" for l in ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J"]]
        elif "3" in year_clean:
            return [f"CSE-{l}" for l in ["C1", "C2", "C3", "C4", "C5", "C6", "C7", "G1", "G2", "G3", "G4"]]
        elif "4" in year_clean:
            return [f"CSE-{l}" for l in ["C1", "C2", "C3", "C4", "C5", "G1", "G2"]]
        return [f"CSE-{l}" for l in ["A", "B", "C", "D", "E"]]


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
    active_pa_keys = await _get_active_planned_absence_keys(today_date)

    res: List[MentorSectionCard] = []
    for s in all_secs:
        s_variants = _get_section_query_clauses(s)
        stu_clauses = [c for c in [sec_q, {"$or": s_variants}] if c]
        stu_cnt = await db.students.count_documents({"$and": stu_clauses} if len(stu_clauses) > 1 else stu_clauses[0])

        abs_clauses: List[Dict[str, Any]] = [
            {"year": year_clean},
            {"$or": s_variants},
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
        abs_cnt = await db.student_attendance.count_documents({"$and": abs_clauses})
        res.append(MentorSectionCard(
            year=year_clean,
            section=s,
            studentCount=stu_cnt,
            absenteeCount=abs_cnt,
        ))
    return res


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
        abs_cnt = await db.student_attendance.count_documents({"$and": abs_clauses})
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
        abs_cnt = await db.student_attendance.count_documents({"$and": abs_clauses})
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
        abs_cnt = await db.student_attendance.count_documents({"$and": abs_clauses})

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

    cursor = db.student_attendance.find({"$and": query_clauses}).sort("roll_number", 1)

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
