import io
import re
from datetime import datetime, timezone
import zoneinfo
from typing import Any, Dict, List, Optional, Set, Tuple
from bson import ObjectId
from fastapi import HTTPException, status
import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from app.core.config import settings
from app.db.mongodb import get_database
from app.core.dependencies import enforce_assigned_department, enforce_assigned_year, get_assigned_years
from app.schemas.mentor_mapping import (
    MentorMappingConfirmRequest,
    MentorMappingPreviewResponse,
    MentorMappingResponse,
    MentorMappingRow,
)
from app.schemas.user import UserRole
from app.services.excel_service import extract_raw_rows_from_file
from app.services.student_service import build_year_filter_clause

tz_kolkata = zoneinfo.ZoneInfo(settings.TIMEZONE)


def generate_mentor_mapping_excel_template() -> bytes:
    """Generate a clean .xlsx template for Mentor-Student Mapping bulk import."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Mentor_Student_Mapping"

    headers = [
        "Mentor Name",
        "Year",
        "Section",
        "Starting Serial Number",
        "Ending Serial Number",
    ]
    ws.append(headers)

    header_fill = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")

    for col_num in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col_num)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")

    samples = [
        ["Dr. SIVA NAGESWARA RAO", "2nd Year", "A", "", ""],
        ["MOTURI SIREESHA", "2nd Year", "B", "1", "30"],
        ["MOTURI SIREESHA", "2nd Year", "B", "31", "60"],
        ["PRASAD MANCHIKANTI", "3rd Year", "A", "1", "35"],
    ]
    for row in samples:
        ws.append(row)

    for col in ws.columns:
        max_len = max(len(str(cell.value or "")) for cell in col)
        col_letter = get_column_letter(col[0].column)
        ws.column_dimensions[col_letter].width = max(max_len + 5, 20)

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()


async def get_mentor_assigned_student_ids(current_user: dict) -> Optional[List[str]]:
    """
    Returns list of student _id strings assigned to the mentor.
    Admin/coordinator callers receive None (full access). Mentors receive their
    mapped student IDs. An unconfigured mentor receives an empty list, never an
    implicit all-students scope.
    """
    role = current_user.get("role")
    if role in [UserRole.ADMIN.value, "ADMIN", "DEPARTMENT_COORDINATOR", "COORDINATOR"]:
        return None

    db = get_database()
    identifiers: Set[str] = set()
    for key in ("_id", "id", "mentor_id", "mentorId", "roll_number", "rollNumber", "email"):
        value = current_user.get(key)
        if value is not None and str(value).strip():
            identifiers.add(str(value).strip())
    emails = {value.casefold() for value in identifiers if "@" in value}
    names = {
        str(current_user.get(key) or "").strip()
        for key in ("name", "mentor_name", "mentorName")
        if str(current_user.get(key) or "").strip()
    }
    current_user_id = str(current_user.get("_id") or current_user.get("id") or "")
    unique_legacy_names: Set[str] = set()
    for name in names:
        matching_users = await db.users.find({
            "role": {"$in": [UserRole.MENTOR.value, "MENTOR"]},
            "name": {"$regex": f"^{re.escape(name)}$", "$options": "i"},
        }, {"_id": 1}).to_list(length=2)
        if len(matching_users) == 1 and str(matching_users[0]["_id"]) == current_user_id:
            unique_legacy_names.add(name)

    # The mapping importer stores users._id as a string. Include BSON ObjectId
    # variants for older records and camelCase aliases written by legacy tools.
    id_values: list[Any] = list(identifiers)
    id_values.extend(ObjectId(value) for value in identifiers if ObjectId.is_valid(value))
    identity_clauses: list[dict] = []
    if id_values:
        for field in ("mentor_id", "mentorId", "mentor_user_id", "mentorUserId"):
            identity_clauses.append({field: {"$in": id_values}})
    if emails:
        for field in ("mentor_email", "mentorEmail"):
            identity_clauses.append({field: {"$regex": f"^(?:{'|'.join(re.escape(item) for item in sorted(emails))})$", "$options": "i"}})

    mappings = []
    if identity_clauses:
        mappings = await db.mentor_student_mappings.find({"$or": identity_clauses}).to_list(length=5000)
    # Legacy imports may have no mentor ID or email. Use exact case-insensitive
    # name matching only as a fallback when stable identifiers found no rows.
    if not mappings and unique_legacy_names:
        name_clauses = [
            {field: {"$regex": f"^{re.escape(name)}$", "$options": "i"}}
            for name in unique_legacy_names
            for field in ("mentor_name", "mentorName")
        ]
        mappings = await db.mentor_student_mappings.find({"$or": name_clauses}).to_list(length=5000)

    assigned_ids: Set[str] = set()
    full_section_mappings = []
    for mapping in mappings:
        raw_student_ids = mapping.get("student_ids", mapping.get("studentIds", [])) or []
        if not raw_student_ids:
            matched_students = mapping.get("matched_students", mapping.get("matchedStudents", [])) or []
            raw_student_ids = [
                item.get("student_id") or item.get("studentId") or item.get("_id") or item.get("id") or item.get("roll_number") or item.get("rollNumber")
                if isinstance(item, dict) else item
                for item in matched_students
            ]
        for student_id in raw_student_ids:
            if student_id and str(student_id).strip():
                assigned_ids.add(str(student_id).strip())
        # A full-section mapping remains section-scoped even after roster
        # changes; include its current roster in addition to saved IDs.
        if mapping.get("is_full_section", mapping.get("isFullSection", False)):
            full_section_mappings.append(mapping)

    # Support full-section assignments when the mapping record is authoritative
    # but predates the saved student_ids list.
    for mapping in full_section_mappings:
        year = str(mapping.get("year") or "").strip()
        section = str(mapping.get("section") or "").strip()
        if not year or not section:
            continue
        section_clean = section.upper()
        section_normalized = (
            section_clean.replace("II-", "")
            .replace("I-", "")
            .replace("III-", "")
            .replace("IV-", "")
            .replace("CSE-", "")
            .replace("SECTION", "")
            .strip()
        )
        section_candidates = list({
            section_clean,
            section_normalized,
            f"CSE-{section_normalized}",
            f"II-CSE-{section_normalized}",
            f"I-CSE-{section_normalized}",
            f"III-CSE-{section_normalized}",
            f"IV-CSE-{section_normalized}",
            f"II-{section_normalized}",
        })
        section_query = {"section": {"$in": section_candidates}}
        student_query = {"$and": [build_year_filter_clause(year), section_query]}
        branch = str(mapping.get("branch") or "").strip()
        if branch:
            student_query["$and"].append({"branch": {"$regex": f"^{re.escape(branch)}$", "$options": "i"}})
        cursor = db.students.find(student_query, {"_id": 1})
        async for student in cursor:
            assigned_ids.add(str(student["_id"]))

    # Direct student fields are also synchronized by the existing admin import.
    direct_clauses: list[dict] = []
    if id_values:
        for field in ("mentor_id", "mentorId", "mentor_user_id", "mentorUserId"):
            direct_clauses.append({field: {"$in": id_values}})
    if emails:
        for field in ("mentor_email", "mentorEmail"):
            direct_clauses.append({field: {"$regex": f"^(?:{'|'.join(re.escape(item) for item in sorted(emails))})$", "$options": "i"}})
    if direct_clauses:
        students_cursor = db.students.find({"$or": direct_clauses}, {"_id": 1})
        async for student in students_cursor:
            assigned_ids.add(str(student["_id"]))
    if not assigned_ids and unique_legacy_names:
        legacy_name_clauses = [
            {field: {"$regex": f"^{re.escape(name)}$", "$options": "i"}}
            for name in unique_legacy_names
            for field in ("mentor_name", "mentorName")
        ]
        students_cursor = db.students.find({"$or": legacy_name_clauses}, {"_id": 1})
        async for student in students_cursor:
            assigned_ids.add(str(student["_id"]))

    return sorted(assigned_ids)


async def is_student_assigned_to_mentor(student_id_or_roll: str, current_user: dict) -> bool:
    """Checks if a student is assigned to the mentor."""
    # Support legacy accounts whose assignments were embedded directly on the
    # user record before mentor_student_mappings became the source of truth.
    target = (student_id_or_roll or "").strip().casefold()
    embedded = current_user.get("assigned_students") or []
    if any(str(value).strip().casefold() == target for value in embedded):
        return True
    assigned_ids = await get_mentor_assigned_student_ids(current_user)
    if assigned_ids is None:
        return True  # Admin has access to all

    db = get_database()
    clean_target = student_id_or_roll.strip()
    student_doc = None
    if ObjectId.is_valid(clean_target):
        student_doc = await db.students.find_one({"_id": ObjectId(clean_target)})
    if not student_doc:
        student_doc = await db.students.find_one({"_id": clean_target})
    if not student_doc:
        student_doc = await db.students.find_one({"roll_number": clean_target.upper()})

    if not student_doc:
        return False

    return str(student_doc["_id"]) in assigned_ids or student_doc.get("roll_number", "").upper() in assigned_ids


def normalize_string(val: Any) -> str:
    if val is None:
        return ""
    s = str(val).strip()
    if s.endswith(".0") and re.match(r"^\d+\.0$", s):
        s = s[:-2]
    s = re.sub(r"[Ââ\xa0\u200b\ufeff\r\n\t]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


async def parse_and_validate_mapping_rows(raw_rows: List[List[str]]) -> Tuple[List[MentorMappingRow], Dict[str, Any]]:
    """
    Parses raw excel rows and validates mentor, year, section, serial ranges and student matches.
    """
    db = get_database()
    if not raw_rows:
        return [], {"total": 0, "valid": 0, "invalid": 0, "students_count": 0, "conflicts": 0}

    # Locate headers in top 15 rows
    header_idx = -1
    col_map: Dict[str, int] = {}
    for idx, row in enumerate(raw_rows[:15]):
        cleaned = [re.sub(r'[^a-z0-9]', '', str(c or "").lower()) for c in row]
        temp_map = {}
        for c_i, c_val in enumerate(cleaned):
            if c_val in ["mentorname", "mentor", "facultyname", "faculty", "name"]:
                temp_map["mentor"] = c_i
            elif c_val in ["year", "academicyear", "classyear"]:
                temp_map["year"] = c_i
            elif c_val in ["section", "sec"]:
                temp_map["section"] = c_i
            elif c_val in ["startingserialnumber", "startingserial", "startserial", "startserialnumber", "fromserial", "startsno", "from", "start"]:
                temp_map["start"] = c_i
            elif c_val in ["endingserialnumber", "endingserial", "endserial", "endserialnumber", "toserial", "endsno", "to", "end"]:
                temp_map["end"] = c_i

        if "mentor" in temp_map and "section" in temp_map:
            header_idx = idx
            col_map = temp_map
            break

    if header_idx == -1:
        # Fallback default columns
        header_idx = 0
        col_map = {"mentor": 0, "year": 1, "section": 2, "start": 3, "end": 4}

    # Pre-fetch all mentors from database
    mentors_cursor = db.users.find({"role": {"$in": [UserRole.MENTOR.value, "MENTOR"]}})
    mentors_list = await mentors_cursor.to_list(length=1000)

    mentor_lookup: Dict[str, dict] = {}
    for m in mentors_list:
        m_name_norm = normalize_string(m.get("name", "")).lower()
        mentor_lookup[m_name_norm] = m
        if m.get("mentor_id"):
            mentor_lookup[str(m["mentor_id"]).lower().strip()] = m
        if m.get("roll_number"):
            mentor_lookup[str(m["roll_number"]).lower().strip()] = m
        if m.get("email"):
            mentor_lookup[str(m["email"]).lower().strip()] = m

    parsed_rows: List[MentorMappingRow] = []
    total_assigned_students: Set[str] = set()
    conflicts_count = 0

    # Track range assignments per section: (year, section) -> list of {mentor_id, start, end, row_idx}
    section_ranges: Dict[Tuple[str, str], List[dict]] = {}

    for r_idx, row_values in enumerate(raw_rows[header_idx + 1:], start=header_idx + 2):
        if not any(row_values):
            continue

        def get_col(k: str) -> str:
            idx = col_map.get(k)
            if idx is not None and idx < len(row_values):
                return normalize_string(row_values[idx])
            return ""

        raw_mentor = get_col("mentor")
        raw_year = get_col("year") or "2nd Year"
        raw_section = get_col("section")
        raw_start = get_col("start")
        raw_end = get_col("end")

        if not raw_mentor and not raw_section:
            continue

        row_errors: List[str] = []

        # 1. Validate Mentor
        if not raw_mentor:
            row_errors.append("Mentor Name is required.")

        mentor_obj = None
        if raw_mentor:
            m_key = raw_mentor.lower().strip()
            # Clean "dr.", "prof.", "mr.", "mrs.", "ms." prefixes for flexible matching
            m_clean = re.sub(r'^(dr|prof|mr|mrs|ms)\.?\s*', '', m_key)
            if m_key in mentor_lookup:
                mentor_obj = mentor_lookup[m_key]
            elif m_clean in mentor_lookup:
                mentor_obj = mentor_lookup[m_clean]
            else:
                # Partial match
                for mk, mv in mentor_lookup.items():
                    if m_clean and (m_clean in mk or mk in m_clean):
                        mentor_obj = mv
                        break

            if not mentor_obj:
                row_errors.append(f"Mentor '{raw_mentor}' not found in database. Please add mentor in Manage Mentors first.")

        # 2. Normalize Year & Section
        year_clean = raw_year
        if "1" in raw_year or "i" in raw_year.lower():
            year_clean = "1st Year"
        elif "2" in raw_year or "ii" in raw_year.lower():
            year_clean = "2nd Year"
        elif "3" in raw_year or "iii" in raw_year.lower():
            year_clean = "3rd Year"
        elif "4" in raw_year or "iv" in raw_year.lower():
            year_clean = "4th Year"

        if not raw_section:
            row_errors.append("Section is required.")
        sec_clean = raw_section.upper()

        # 3. Parse Serial Numbers
        start_serial: Optional[int] = None
        end_serial: Optional[int] = None
        is_full_section = False

        if not raw_start and not raw_end:
            is_full_section = True
        else:
            try:
                start_serial = int(raw_start) if raw_start else 1
            except ValueError:
                row_errors.append(f"Invalid Starting Serial Number: '{raw_start}'. Must be an integer.")
            try:
                end_serial = int(raw_end) if raw_end else None
            except ValueError:
                row_errors.append(f"Invalid Ending Serial Number: '{raw_end}'. Must be an integer.")

            if start_serial is not None and start_serial < 1:
                row_errors.append("Starting Serial Number must be at least 1.")

            if start_serial is not None and end_serial is not None and start_serial > end_serial:
                row_errors.append(f"Starting Serial ({start_serial}) cannot be greater than Ending Serial ({end_serial}).")

        # 4. Fetch students for (Year, Section)
        matched_students_info: List[dict] = []
        if not row_errors and sec_clean:
            # Match section variations
            sec_norm = (
                sec_clean.replace("II-", "")
                .replace("I-", "")
                .replace("III-", "")
                .replace("IV-", "")
                .replace("CSE-", "")
                .replace("SECTION", "")
                .strip()
            )
            sec_candidates = list(set([
                sec_clean,
                sec_norm,
                f"CSE-{sec_norm}",
                f"II-CSE-{sec_norm}",
                f"I-CSE-{sec_norm}",
                f"III-CSE-{sec_norm}",
                f"IV-CSE-{sec_norm}",
                f"II-{sec_norm}",
            ]))

            y_clause = build_year_filter_clause(year_clean)
            q: Dict[str, Any] = {"section": {"$in": sec_candidates}}
            if y_clause:
                q = {"$and": [q, {"$or": [{"year": year_clean}, y_clause]}]}
            else:
                q["year"] = year_clean

            students_in_sec = await db.students.find(q).sort("roll_number", 1).to_list(length=1000)
            if not students_in_sec:
                # Fallback without year constraint if section is specific
                students_in_sec = await db.students.find({"section": {"$in": sec_candidates}}).sort("roll_number", 1).to_list(length=1000)

            total_in_sec = len(students_in_sec)
            if total_in_sec == 0:
                row_errors.append(f"No students found registered in {year_clean} Section {sec_clean}.")
            else:
                if is_full_section:
                    sliced = students_in_sec
                    start_serial = 1
                    end_serial = total_in_sec
                else:
                    if end_serial is None:
                        end_serial = total_in_sec
                    s_idx = max(0, (start_serial or 1) - 1)
                    e_idx = min(total_in_sec, end_serial)
                    sliced = students_in_sec[s_idx:e_idx]
                    if end_serial > total_in_sec:
                        # Warning / note
                        pass

                for s_doc in sliced:
                    s_id_str = str(s_doc["_id"])
                    matched_students_info.append({
                        "student_id": s_id_str,
                        "roll_number": s_doc.get("roll_number", ""),
                        "name": s_doc.get("name", ""),
                    })
                    total_assigned_students.add(s_id_str)

        # 5. Overlap detection
        sec_key = (year_clean, sec_clean)
        if not row_errors and start_serial is not None and end_serial is not None and mentor_obj:
            curr_mentor_id = str(mentor_obj["_id"])
            if sec_key not in section_ranges:
                section_ranges[sec_key] = []
            else:
                for prev in section_ranges[sec_key]:
                    if prev["mentor_id"] != curr_mentor_id:
                        # Check overlap: max(start1, start2) <= min(end1, end2)
                        if max(start_serial, prev["start"]) <= min(end_serial, prev["end"]):
                            conflicts_count += 1
                            row_errors.append(
                                f"Serial range {start_serial}–{end_serial} overlaps with assigned range {prev['start']}–{prev['end']} for {prev['mentor_name']} (Row {prev['row_idx']})."
                            )

            if not row_errors:
                section_ranges[sec_key].append({
                    "mentor_id": curr_mentor_id,
                    "mentor_name": mentor_obj.get("name", raw_mentor),
                    "start": start_serial,
                    "end": end_serial,
                    "row_idx": r_idx,
                })

        row_status = "ERROR" if row_errors else "VALID"
        parsed_rows.append(MentorMappingRow(
            rowIdx=r_idx,
            mentorName=mentor_obj.get("name", raw_mentor) if mentor_obj else raw_mentor,
            mentorId=str(mentor_obj["_id"]) if mentor_obj else None,
            year=year_clean,
            section=sec_clean,
            startSerial=start_serial,
            endSerial=end_serial,
            isFullSection=is_full_section,
            status=row_status,
            errorMessage="; ".join(row_errors) if row_errors else None,
            studentCount=len(matched_students_info),
            matchedStudents=matched_students_info,
        ))

    valid_count = sum(1 for r in parsed_rows if r.status == "VALID")
    invalid_count = sum(1 for r in parsed_rows if r.status == "ERROR")

    summary = {
        "total": len(parsed_rows),
        "valid": valid_count,
        "invalid": invalid_count,
        "students_count": len(total_assigned_students),
        "conflicts": conflicts_count,
    }
    return parsed_rows, summary


async def preview_mentor_mappings(file_bytes: bytes, filename: str, current_user: Optional[dict] = None) -> MentorMappingPreviewResponse:
    """Parses workbook and generates mapping preview report."""
    raw_rows = extract_raw_rows_from_file(file_bytes, filename)
    if len(raw_rows) > settings.MAX_IMPORT_ROWS:
        raise HTTPException(status_code=413, detail=f"Import exceeds the {settings.MAX_IMPORT_ROWS} row limit.")
    rows, summary = await parse_and_validate_mapping_rows(raw_rows)
    if current_user and current_user.get("role") == UserRole.ADMIN.value:
        db = get_database()
        department = enforce_assigned_department(current_user, None)
        for row in rows:
            if row.status != "VALID":
                continue
            try:
                enforce_assigned_year(current_user, row.year)
                if department and department.casefold() not in row.section.casefold():
                    raise HTTPException(status_code=403, detail="Mapping row is outside the assigned department.")
                mentor = await db.users.find_one({"_id": ObjectId(row.mentor_id)}) if row.mentor_id and ObjectId.is_valid(row.mentor_id) else None
                if not mentor or (mentor.get("department") or mentor.get("branch") or "").casefold() != (department or "").casefold():
                    raise HTTPException(status_code=403, detail="Mapping mentor is outside the assigned department.")
            except HTTPException as exc:
                row.status = "ERROR"
                row.error_message = exc.detail
                summary["valid"] -= 1
                summary["invalid"] += 1
    return MentorMappingPreviewResponse(
        totalRows=summary["total"],
        validRows=summary["valid"],
        invalidRows=summary["invalid"],
        studentsToAssign=summary["students_count"],
        conflictsCount=summary["conflicts"],
        rows=rows,
    )


# Alias for backward/naming compatibility
preview_mentor_mapping_file = preview_mentor_mappings


async def commit_mentor_mappings(
    data_or_bytes: Any,
    current_user: Any,
    filename: Optional[str] = None,
    mode: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Commits mentor-student mappings into MongoDB.
    Supports receiving either MentorMappingConfirmRequest (with confirmed rows)
    or raw file bytes.
    """
    db = get_database()
    now_utc = datetime.now(timezone.utc)
    actor_id = str(current_user.get("_id", "")) if isinstance(current_user, dict) else str(current_user)

    valid_rows: List[Any] = []
    chosen_mode = "ADD_UPDATE"

    if isinstance(data_or_bytes, MentorMappingConfirmRequest) or hasattr(data_or_bytes, "rows"):
        chosen_mode = (getattr(data_or_bytes, "mode", None) or "ADD_UPDATE").upper()
        raw_rows_input = getattr(data_or_bytes, "rows", None) or []
        for r in raw_rows_input:
            if isinstance(r, MentorMappingRow):
                if r.status == "VALID":
                    valid_rows.append(r)
            elif isinstance(r, dict):
                if r.get("status") == "VALID":
                    # Convert to MentorMappingRow
                    valid_rows.append(MentorMappingRow(**r))
    elif isinstance(data_or_bytes, (bytes, bytearray)):
        chosen_mode = (mode or "ADD_UPDATE").upper()
        raw_rows = extract_raw_rows_from_file(data_or_bytes, filename or "uploaded.xlsx")
        if len(raw_rows) > settings.MAX_IMPORT_ROWS:
            raise HTTPException(status_code=413, detail=f"Import exceeds the {settings.MAX_IMPORT_ROWS} row limit.")
        rows, summary = await parse_and_validate_mapping_rows(raw_rows)
        valid_rows = [r for r in rows if r.status == "VALID"]
    else:
        raise HTTPException(status_code=400, detail="Invalid mapping data provided.")

    if not valid_rows:
        raise HTTPException(status_code=400, detail="No valid mapping rows to commit.")

    if isinstance(current_user, dict) and current_user.get("role") == UserRole.ADMIN.value:
        if chosen_mode == "REPLACE":
            raise HTTPException(status_code=403, detail="Only Super Admin may replace all mentor mappings.")
        department = enforce_assigned_department(current_user, None)
        ids_to_check = set()
        for row in valid_rows:
            enforce_assigned_year(current_user, row.year)
            if department and department.casefold() not in row.section.casefold():
                raise HTTPException(status_code=403, detail="Mapping row is outside the assigned department.")
            mentor = await db.users.find_one({"_id": ObjectId(row.mentor_id)}) if row.mentor_id and ObjectId.is_valid(row.mentor_id) else None
            if not mentor or (mentor.get("department") or mentor.get("branch") or "").casefold() != (department or "").casefold():
                raise HTTPException(status_code=403, detail="Mapping mentor is outside the assigned department.")
            ids_to_check.update(s.get("student_id") for s in row.matched_students if s.get("student_id"))
        object_ids = [ObjectId(item) for item in ids_to_check if ObjectId.is_valid(item)]
        students = await db.students.find({"_id": {"$in": object_ids}}).to_list(length=10000)
        if len(students) != len(object_ids):
            raise HTTPException(status_code=400, detail="Mapping contains a student record that no longer exists.")
        for student in students:
            enforce_assigned_year(current_user, student.get("year"))
            if department and (student.get("department") or student.get("branch") or "").casefold() != department.casefold():
                raise HTTPException(status_code=403, detail="Mapping student is outside the assigned department.")

    if chosen_mode == "REPLACE":
        # Unassign previous mappings and clear collection
        await db.mentor_student_mappings.delete_many({})
        await db.students.update_many({}, {"$unset": {"mentor_id": "", "mentor_name": ""}})

    # Group valid mappings by mentor
    created_count = 0
    updated_count = 0
    total_assigned = 0

    for r in valid_rows:
        if not r.mentor_id:
            continue

        mentor_u = await db.users.find_one({"_id": ObjectId(r.mentor_id)})
        mentor_name = mentor_u.get("name", r.mentor_name) if mentor_u else r.mentor_name
        mentor_email = mentor_u.get("email") if mentor_u else None

        student_ids = [s["student_id"] for s in r.matched_students if s.get("student_id")]
        total_assigned += len(student_ids)

        mapping_doc = {
            "mentor_id": r.mentor_id,
            "mentor_name": mentor_name,
            "mentor_email": mentor_email,
            "year": r.year,
            "section": r.section,
            "start_serial": r.start_serial,
            "end_serial": r.end_serial,
            "is_full_section": r.is_full_section,
            "student_count": len(student_ids),
            "student_ids": student_ids,
            "source": "excel_import",
            "updated_at": now_utc,
            "assigned_by": actor_id,
        }

        # Check existing mapping for same mentor + year + section
        existing_m = await db.mentor_student_mappings.find_one({
            "mentor_id": r.mentor_id,
            "year": r.year,
            "section": r.section,
            "start_serial": r.start_serial,
            "end_serial": r.end_serial,
        })

        if existing_m:
            await db.mentor_student_mappings.update_one(
                {"_id": existing_m["_id"]},
                {"$set": mapping_doc},
            )
            updated_count += 1
        else:
            mapping_doc["created_at"] = now_utc
            await db.mentor_student_mappings.insert_one(mapping_doc)
            created_count += 1

        # Direct synchronization on student documents
        if student_ids:
            obj_ids = [ObjectId(sid) for sid in student_ids if ObjectId.is_valid(sid)]
            if obj_ids:
                await db.students.update_many(
                    {"_id": {"$in": obj_ids}},
                    {"$set": {"mentor_id": r.mentor_id, "mentor_name": mentor_name, "updated_at": now_utc}},
                )

    # Audit log
    await db.audit_logs.insert_one({
        "actor_id": actor_id,
        "action": "IMPORT_MENTOR_STUDENT_MAPPING",
        "metadata": {
            "filename": filename,
            "mode": chosen_mode,
            "valid_rows": len(valid_rows),
            "created": created_count,
            "updated": updated_count,
            "students_assigned": total_assigned,
        },
        "created_at": now_utc,
    })

    return {
        "success": True,
        "message": f"Successfully committed mentor-student mappings: {created_count} created, {updated_count} updated, {total_assigned} students assigned.",
        "created_count": created_count,
        "updated_count": updated_count,
        "total_students_assigned": total_assigned,
    }


async def get_mentor_mappings(
    year: Optional[str] = None,
    section: Optional[str] = None,
    mentor_id: Optional[str] = None,
) -> List[MentorMappingResponse]:
    """Retrieve all active mentor-student mappings with optional filters."""
    db = get_database()
    query: Dict[str, Any] = {}
    if year:
        query["year"] = year.strip()
    if section:
        query["section"] = section.strip().upper()
    if mentor_id:
        query["mentor_id"] = mentor_id.strip()

    cursor = db.mentor_student_mappings.find(query).sort([("year", 1), ("section", 1), ("mentor_name", 1)])
    res: List[MentorMappingResponse] = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        res.append(MentorMappingResponse(**doc))
    return res


async def get_all_mentor_mappings() -> List[MentorMappingResponse]:
    """Retrieve all active mentor-student mappings."""
    return await get_mentor_mappings()


async def delete_mentor_mapping(mapping_id: str, current_user: Any) -> Dict[str, Any]:
    """Delete a mentor mapping and remove mentor references from affected students."""
    db = get_database()
    clean_id = mapping_id.strip()
    if not ObjectId.is_valid(clean_id):
        raise HTTPException(status_code=400, detail="Invalid mapping ID.")

    doc = await db.mentor_student_mappings.find_one({"_id": ObjectId(clean_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Mapping record not found.")

    student_ids = doc.get("student_ids", [])
    if student_ids:
        obj_ids = [ObjectId(sid) for sid in student_ids if ObjectId.is_valid(sid)]
        if obj_ids:
            await db.students.update_many(
                {"_id": {"$in": obj_ids}, "mentor_id": doc.get("mentor_id")},
                {"$unset": {"mentor_id": "", "mentor_name": ""}},
            )

    await db.mentor_student_mappings.delete_one({"_id": ObjectId(clean_id)})

    actor_id = str(current_user.get("_id", "")) if isinstance(current_user, dict) else str(current_user)
    actor_email = current_user.get("email") if isinstance(current_user, dict) else None

    # Audit log
    await db.audit_logs.insert_one({
        "actor_id": actor_id,
        "actor_email": actor_email,
        "action": "DELETE_MENTOR_STUDENT_MAPPING",
        "target_mapping_id": clean_id,
        "metadata": {"mentor": doc.get("mentor_name"), "students_count": len(student_ids)},
        "created_at": datetime.now(timezone.utc),
    })
    return {"success": True, "message": "Mentor mapping deleted successfully."}

