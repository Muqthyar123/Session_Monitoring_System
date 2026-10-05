import csv
import io
import re
from datetime import datetime, time, timezone
from typing import Any, Dict, List, Optional, Tuple
from bson import ObjectId
import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from pydantic import EmailStr, TypeAdapter
from app.core.security import hash_password
from app.db.mongodb import get_database
from app.schemas.user import UserRole
from app.services.student_service import compute_year_from_batch, find_crlr_for_student, infer_batch_from_roll

email_adapter = TypeAdapter(EmailStr)

DAYS_OF_WEEK = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]


# ----------------------------------------------------
# CR/LR EXCEL PROCESSING
# ----------------------------------------------------

def generate_crlr_excel_template() -> bytes:
    """Generate a clean .xlsx template for CR/LR user import."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "CR_LR_Import_Template"

    headers = ["Name", "Roll Number", "Email", "Phone", "Role", "Year", "Section"]
    ws.append(headers)

    # Styling header
    header_fill = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")

    for col_num in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col_num)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")

    # Sample rows
    samples = [
        ["Rahul Kumar", "22CS2A01", "rahul.kumar@example.com", "9876543210", "CR", "2nd Year", "II-A"],
        ["Sneha Sharma", "22CS2A02", "sneha.sharma@example.com", "9876543211", "LR", "2nd Year", "II-A"],
        ["Vikram Singh", "21CS3B01", "vikram.singh@example.com", "9876543212", "CR", "3rd Year", "III-B"],
    ]
    for row in samples:
        ws.append(row)

    # Adjust column widths
    for col in ws.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        col_letter = get_column_letter(col[0].column)
        ws.column_dimensions[col_letter].width = max(max_len + 4, 15)

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()


async def parse_and_import_crlr_excel(
    file_bytes: bytes, filename: str, actor_id: str
) -> Dict[str, Any]:
    """Parse CR/LR Excel workbook and safely import users."""
    if not filename.lower().endswith(".xlsx"):
        raise ValueError("Invalid file format. Only .xlsx Excel workbooks are supported.")

    try:
        wb = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=True)
    except Exception as e:
        raise ValueError(f"Failed to read Excel file: {str(e)}")

    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        raise ValueError("Excel file is empty.")

    header_row = [str(cell).strip() if cell is not None else "" for cell in rows[0]]
    expected_cols = ["name", "roll number", "email", "phone", "role", "year", "section"]
    col_map = {}
    for idx, h in enumerate(header_row):
        h_norm = h.lower()
        if h_norm in expected_cols:
            col_map[h_norm] = idx

    missing_cols = [c for c in ["name", "email", "role", "year", "section"] if c not in col_map]
    if missing_cols:
        raise ValueError(f"Missing required columns in Excel: {', '.join(missing_cols)}")

    db = get_database()

    # Pre-fetch existing emails and roll numbers for fast duplicate checking
    existing_users = await db.users.find({}, {"email": 1, "roll_number": 1}).to_list(length=10000)
    existing_emails = {u["email"].lower(): str(u["_id"]) for u in existing_users if "email" in u}
    existing_rolls = {u["roll_number"].upper(): str(u["_id"]) for u in existing_users if u.get("roll_number")}

    seen_emails_in_file = set()
    seen_rolls_in_file = set()

    total_rows = 0
    created_count = 0
    updated_count = 0
    failed_count = 0
    errors = []

    default_password_hash = hash_password("demo1234")

    for row_idx, row_values in enumerate(rows[1:], start=2):
        if not any(row_values):
            continue  # Skip completely empty rows

        total_rows += 1
        row_str_num = f"Row {row_idx}"

        def get_val(col_name: str) -> str:
            idx = col_map.get(col_name)
            if idx is not None and idx < len(row_values) and row_values[idx] is not None:
                return str(row_values[idx]).strip()
            return ""

        name = get_val("name")
        email = get_val("email").lower()
        role = get_val("role").upper()
        roll = get_val("roll number").upper()
        phone = get_val("phone")
        year = get_val("year")
        section = get_val("section").upper()

        row_errors = []

        if not name:
            row_errors.append("Name is required.")
        if not email:
            row_errors.append("Email is required.")
        else:
            try:
                email_adapter.validate_python(email)
            except Exception:
                row_errors.append(f"Invalid email format: '{email}'.")

        if role not in [UserRole.CR.value, UserRole.LR.value]:
            row_errors.append(f"Role must be CR or LR (got '{role}').")

        if not year:
            row_errors.append("Year is required.")
        if not section:
            row_errors.append("Section is required.")

        # Duplicate checks in file
        if email in seen_emails_in_file:
            row_errors.append(f"Duplicate email '{email}' within Excel file.")
        else:
            if email:
                seen_emails_in_file.add(email)

        if roll:
            if roll in seen_rolls_in_file:
                row_errors.append(f"Duplicate roll number '{roll}' within Excel file.")
            else:
                seen_rolls_in_file.add(roll)

        if row_errors:
            failed_count += 1
            errors.append({"row": row_idx, "errors": row_errors})
            continue

        now = datetime.now(timezone.utc)

        # Check if updating or creating
        if email in existing_emails:
            # Update existing user
            u_id = existing_emails[email]
            update_fields = {
                "name": name,
                "role": role,
                "year": year,
                "section": section,
                "updated_at": now,
            }
            if roll:
                update_fields["roll_number"] = roll
            if phone:
                update_fields["phone"] = phone

            await db.users.update_one({"_id": db.users.find_one({"email": email})["_id"]}, {"$set": update_fields})
            updated_count += 1
        elif roll and roll in existing_rolls:
            # Update existing user by roll number
            update_fields = {
                "name": name,
                "email": email,
                "role": role,
                "year": year,
                "section": section,
                "updated_at": now,
            }
            if phone:
                update_fields["phone"] = phone
            await db.users.update_one({"roll_number": roll}, {"$set": update_fields})
            updated_count += 1
        else:
            # Create new user
            new_user_doc = {
                "name": name,
                "email": email,
                "password_hash": default_password_hash,
                "role": role,
                "roll_number": roll if roll else None,
                "phone": phone if phone else None,
                "year": year,
                "section": section,
                "is_active": True,
                "created_at": now,
                "updated_at": now,
            }
            res = await db.users.insert_one(new_user_doc)
            existing_emails[email] = str(res.inserted_id)
            if roll:
                existing_rolls[roll] = str(res.inserted_id)
            created_count += 1

    # Log audit entry
    await db.audit_logs.insert_one(
        {
            "actor_id": actor_id,
            "action": "IMPORT_CRLR_EXCEL",
            "metadata": {
                "total_rows": total_rows,
                "created": created_count,
                "updated": updated_count,
                "failed": failed_count,
            },
            "created_at": datetime.now(timezone.utc),
        }
    )

    return {
        "total_rows": total_rows,
        "created": created_count,
        "updated": updated_count,
        "failed": failed_count,
        "errors": errors,
    }


# ----------------------------------------------------
# TIMETABLE EXCEL PROCESSING
# ----------------------------------------------------

def generate_timetable_excel_template() -> bytes:
    """Generate a clean .xlsx template for Timetable import."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Class_Timetables"

    headers = [
        "Year",
        "Section",
        "Day",
        "Period",
        "Start Time",
        "End Time",
        "Subject",
        "Faculty",
        "Room",
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
        ["2nd Year", "II-A", "Monday", 1, "09:10", "10:00", "Database Management Systems", "Dr. A. Sharma", "B-204"],
        ["2nd Year", "II-A", "Monday", 2, "10:00", "10:50", "Database Management Systems", "Dr. A. Sharma", "B-204"],
        ["2nd Year", "II-A", "Monday", 3, "10:50", "11:40", "Database Management Systems", "Dr. A. Sharma", "B-204"],
        ["2nd Year", "II-A", "Monday", 4, "11:40", "12:30", "Operating Systems", "Prof. R. Verma", "B-205"],
        ["2nd Year", "II-B", "Monday", 1, "09:10", "10:00", "Computer Networks", "Dr. K. Patel", "C-101"],
        ["3rd Year", "III-A", "Monday", 1, "09:10", "10:00", "Software Engineering", "Prof. M. Iyer", "A-302"],
    ]
    for row in samples:
        ws.append(row)

    for col in ws.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        col_letter = get_column_letter(col[0].column)
        ws.column_dimensions[col_letter].width = max(max_len + 4, 14)

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()


def _format_time_str(val: Any) -> str:
    """Helper to convert Excel time object or string to HH:MM format."""
    if isinstance(val, (datetime, time)):
        return val.strftime("%H:%M")
    val_str = str(val).strip()
    match = re.match(r"^(\d{1,2}):(\d{2})", val_str)
    if match:
        h, m = int(match.group(1)), int(match.group(2))
        return f"{h:02d}:{m:02d}"
    return val_str


def _get_cell_value(ws: openpyxl.worksheet.worksheet.Worksheet, row: int, col: int) -> Any:
    """Safely get cell value, handling openpyxl MergedCell instances by fetching top-left value."""
    cell = ws.cell(row=row, column=col)
    val = getattr(cell, "value", None)
    if val is not None:
        return val
    for rng in ws.merged_cells.ranges:
        if rng.min_row <= row <= rng.max_row and rng.min_col <= col <= rng.max_col:
            return ws.cell(row=rng.min_row, column=rng.min_col).value
    return None


def _parse_time_range(time_str: str, period_num: int) -> Tuple[str, str]:
    """Parse time string like '09:10 - 10:00' or '01:30 - 02:20' into 12-hour HH:MM format."""
    parts = re.split(r"\s*[-–toTO]\s*", str(time_str).strip())
    if len(parts) != 2:
        return "", ""

    def convert_time(t_raw: str) -> str:
        t_clean = str(t_raw).strip()
        m = re.match(r"^(\d{1,2}):(\d{2})", t_clean)
        if not m:
            return ""
        h, m_val = int(m.group(1)), int(m.group(2))
        if h > 12:
            h -= 12
        return f"{h:02d}:{m_val:02d}"

    return convert_time(parts[0]), convert_time(parts[1])


def extract_faculty_names_from_str(text: Any) -> List[str]:
    """
    Extracts individual faculty names from a timetable/legend text.
    Rule:
    1. If ':' is present, the faculty name(s) start strictly AFTER the colon ':'.
       (e.g., 'Computer Networks : Dr.Sk.Zuber Basha' -> ['Dr.Sk.Zuber Basha']
        '1): Mobile Computing : Dr.S.V.N.Srinivasu' -> ['Dr.S.V.N.Srinivasu']
        'Data Warehousing and Data Mining : Y.Chandana' -> ['Y.Chandana'])
    2. Split multiple faculty names separated by commas.
    3. Trim whitespace around each name.
    4. Ignore empty values and placeholders.
    """
    if not text:
        return []
    s = str(text).strip()
    if not s or s.upper() in ["BREAK", "LUNCH", "FREE", "NONE", "N/A", "-"]:
        return []

    if ":" in s:
        parts = s.rsplit(":", 1)
        faculty_portion = parts[1].strip()
    else:
        faculty_portion = s

    # Remove enclosing parentheses if any like '(Dr. X)'
    faculty_portion = re.sub(r"^\((.+)\)$", r"\1", faculty_portion).strip()

    # Split by comma for multiple faculty members
    raw_names = [f.strip() for f in faculty_portion.split(",") if f.strip()]

    valid_names = []
    for name in raw_names:
        clean_name = re.sub(r"^\d+[\).:\s]+", "", name).strip()
        if clean_name and len(clean_name) > 1 and clean_name.upper() not in ["N/A", "NONE", "NULL", "-"]:
            valid_names.append(clean_name)

    return valid_names


def _parse_subject_and_faculty(raw_text: str) -> Tuple[str, List[str], Optional[str]]:
    """
    Parses a timetable cell or subject/faculty string.
    Rule:
    1. If room in parentheses e.g. '(B-204)' or '(Lab-1)', extract room.
    2. If ':' is present:
       - Subject name is before the colon ':'.
       - Faculty information starts strictly after ':'.
       - Faculty names separated by comma ',' are individual persons.
       - Whitespace around each name is trimmed.
    3. If no ':' is present:
       - Multi-line text: line 0 is subject, subsequent lines contain faculty.
    """
    if not raw_text:
        return "", [], None

    raw = str(raw_text).strip()
    room = None
    m_room = re.search(r"\(([^)]+)\)", raw)
    if m_room:
        potential_room = m_room.group(1).strip()
        if any(c.isdigit() for c in potential_room) or "LAB" in potential_room.upper() or "ROOM" in potential_room.upper():
            room = potential_room
            raw = re.sub(r"\(([^)]+)\)", "", raw).strip()

    if ":" in raw:
        parts = raw.rsplit(":", 1)
        subj = parts[0].strip()
        subj = re.sub(r"^\d+[\).:\s]+", "", subj).strip()
        fac_list = extract_faculty_names_from_str(parts[1])
        return subj, fac_list, room

    lines = [l.strip() for l in re.split(r"[\r\n]+", raw) if l.strip()]
    if len(lines) >= 2:
        subj = re.sub(r"^\d+[\).:\s]+", "", lines[0]).strip()
        rest = " ".join(lines[1:]).strip()
        fac_list = extract_faculty_names_from_str(rest)
        return subj, fac_list, room

    return raw, [], room


def _parse_matrix_timetable_excel(ws: openpyxl.worksheet.worksheet.Worksheet, sheet_name: str) -> List[Dict[str, Any]]:
    """Parse College Matrix Grid Timetable sheet (e.g. DAY | 1 | 2 | Break | 3 | 4 | Lunch | 5 | 6 | 7)."""
    # 1. Search top 12 rows for Section, Year, Semester
    detected_section = None
    detected_year = "2nd Year"

    for r in range(1, min(12, ws.max_row + 1)):
        row_str = " ".join(str(_get_cell_value(ws, r, c) or "") for c in range(1, ws.max_column + 1))
        sec_match = re.search(r"\[\s*([A-Za-z0-9]+\s*-\s*[A-Za-z0-9]+)\s*\]", row_str, re.IGNORECASE)
        if not sec_match:
            sec_match = re.search(r"\b([A-Z]{2,5}\s*-\s*[A-Z0-9]+)\b", row_str)
        if sec_match and not detected_section:
            detected_section = re.sub(r"\s+", "", sec_match.group(1)).upper()

        year_match = re.search(r"\b(I|II|III|IV)\s*B\.?Tech\b", row_str, re.IGNORECASE)
        if year_match:
            roman = year_match.group(1).upper()
            mapping = {"I": "1st Year", "II": "2nd Year", "III": "3rd Year", "IV": "4th Year"}
            detected_year = mapping.get(roman, f"{roman} Year")

    roman_prefix_map = {"1st Year": "I", "2nd Year": "II", "3rd Year": "III", "4th Year": "IV"}
    prefix = roman_prefix_map.get(detected_year, "II")

    if detected_section:
        clean_sec = re.sub(r"^(I|II|III|IV)-", "", detected_section)
        detected_section = f"{prefix}-{clean_sec}"
    else:
        detected_section = f"{prefix}-CSE-A"

    # 2. Locate header row with DAY and Period numbers
    header_row_idx = None
    time_row_idx = None

    for r in range(1, min(15, ws.max_row + 1)):
        for col_check in range(1, min(5, ws.max_column + 1)):
            cell_val = str(_get_cell_value(ws, r, col_check) or "").replace("\n", "").replace(" ", "").upper().strip()
            if "DAY" in cell_val or "PERIOD" in cell_val:
                header_row_idx = r
                time_row_idx = r + 1
                break
        if header_row_idx:
            break

    if not header_row_idx:
        for r in range(1, min(15, ws.max_row + 1)):
            cols_with_digits = 0
            for c in range(1, min(10, ws.max_column + 1)):
                c_val = str(_get_cell_value(ws, r, c) or "").strip()
                if re.search(r"^\d+$", c_val) or "09:" in c_val or "10:" in c_val:
                    cols_with_digits += 1
            if cols_with_digits >= 3:
                header_row_idx = r
                time_row_idx = r + 1
                break

    if not header_row_idx:
        return []

    # Map column indexes to period numbers & time slots
    period_col_map: Dict[int, Tuple[int, str, str]] = {}
    
    for c in range(2, ws.max_column + 1):
        p_val = str(_get_cell_value(ws, header_row_idx, c) or "").strip()
        time_val = str(_get_cell_value(ws, time_row_idx, c) or "").strip()

        if p_val.upper() in ["BREAK", "LUNCH"] or time_val.upper() in ["BREAK", "LUNCH"]:
            continue

        p_num_match = re.search(r"\b(\d+)\b", p_val)
        if not p_num_match:
            p_num_match = re.search(r"\b(\d+)\b", time_val)

        if p_num_match:
            p_num = int(p_num_match.group(1))
        else:
            p_num = len(period_col_map) + 1

        start_t, end_t = _parse_time_range(time_val, p_num)
        if not start_t:
            start_t, end_t = _parse_time_range(p_val, p_num)
        if not start_t:
            default_times = {
                1: ("09:10", "10:00"), 2: ("10:00", "10:50"), 3: ("11:00", "11:50"),
                4: ("11:50", "12:40"), 5: ("13:30", "14:20"), 6: ("14:20", "15:10"), 7: ("15:10", "16:00")
            }
            start_t, end_t = default_times.get(p_num, ("09:00", "10:00"))
        period_col_map[c] = (p_num, start_t, end_t)

    # 3. Parse Day rows (MON to SAT)
    day_mapping = {
        "MON": "Monday", "MONDAY": "Monday",
        "TUE": "Tuesday", "TUESDAY": "Tuesday",
        "WED": "Wednesday", "WEDNESDAY": "Wednesday",
        "THU": "Thursday", "THURSDAY": "Thursday",
        "FRI": "Friday", "FRIDAY": "Friday",
        "SAT": "Saturday", "SATURDAY": "Saturday"
    }

    records = []
    last_day_row_idx = time_row_idx

    for r in range(time_row_idx + 1, ws.max_row + 1):
        raw_day_cell = ""
        for day_c in range(1, min(3, ws.max_column + 1)):
            c_val = str(_get_cell_value(ws, r, day_c) or "").replace("\n", "").replace("\r", "").replace(" ", "").upper().strip()
            if any(c_val.startswith(k) for k in day_mapping):
                raw_day_cell = c_val
                break

        matched_day = None
        for k, d in day_mapping.items():
            if raw_day_cell.startswith(k):
                matched_day = d
                break

        if matched_day:
            last_day_row_idx = r
            for col_idx, (p_num, start_t, end_t) in period_col_map.items():
                cell_raw = str(_get_cell_value(ws, r, col_idx) or "").strip()
                if not cell_raw or cell_raw.upper() in ["BREAK", "LUNCH", "FREE", "NONE"]:
                    continue

                subj_parsed, fac_list_parsed, room_parsed = _parse_subject_and_faculty(cell_raw)

                records.append({
                    "year": detected_year,
                    "section": detected_section,
                    "day": matched_day,
                    "period": p_num,
                    "start_time": start_t,
                    "end_time": end_t,
                    "subject": subj_parsed,
                    "faculty": ", ".join(fac_list_parsed) if fac_list_parsed else None,
                    "faculty_names": fac_list_parsed,
                    "room": room_parsed,
                    "updated_at": datetime.now(timezone.utc),
                })

    # 4. Parse Faculty Legend Table below last day row (and adjacent cells)
    faculty_legend: Dict[str, List[str]] = {}
    for r in range(last_day_row_idx + 1, ws.max_row + 1):
        for c in range(1, ws.max_column + 1):
            cell_val = str(_get_cell_value(ws, r, c) or "").strip()
            if not cell_val:
                continue

            # Case A: Separator in single cell (e.g. "DMGT : Dr. Ramesh, Prof. Suresh", "1): Mobile Computing : Dr.S.V.N.Srinivasu")
            if ":" in cell_val or "-" in cell_val:
                m_sep = re.split(r"\s*[:\-\u2013\u2014]\s*", cell_val, maxsplit=1)
                if len(m_sep) == 2 and m_sep[0].strip() and m_sep[1].strip():
                    subj_code = re.sub(r"^\d+[\).:\s]+", "", m_sep[0]).replace("\n", " ").strip().upper()
                    fac_list = extract_faculty_names_from_str(m_sep[1])
                    if fac_list and subj_code not in faculty_legend:
                        faculty_legend[subj_code] = fac_list
                    continue

            # Case B: Two adjacent cells in a row (Column A = "CN", Column B = "Computer Networks : Dr.Sk.Zuber Basha" or "Data Warehousing and Data Mining : Y.Chandana")
            if c < ws.max_column:
                adj_val = str(_get_cell_value(ws, r, c + 1) or "").strip()
                if cell_val and adj_val:
                    code_norm = re.sub(r"^\d+[\).:\s]+", "", cell_val).replace("\n", " ").strip().upper()
                    fac_list = extract_faculty_names_from_str(adj_val)
                    if len(code_norm) <= 25 and fac_list and code_norm not in faculty_legend:
                        if code_norm not in ["SUBJECT", "COURSE", "SL.NO", "CODE", "PERIOD", "FACULTY", "STAFF"]:
                            faculty_legend[code_norm] = fac_list

    # Assign faculty names to matching subject records
    for rec in records:
        if rec.get("faculty_names"):
            rec["faculty"] = ", ".join(rec["faculty_names"])
            continue
        subj_upper = rec["subject"].upper()
        if subj_upper in faculty_legend:
            rec["faculty_names"] = faculty_legend[subj_upper]
            rec["faculty"] = ", ".join(faculty_legend[subj_upper])
        else:
            for k, v in faculty_legend.items():
                if k in subj_upper or subj_upper in k:
                    rec["faculty_names"] = v
                    rec["faculty"] = ", ".join(v)
                    break

    return records


async def parse_and_import_timetable_excel(
    file_bytes: bytes, filename: str, actor_id: str
) -> Dict[str, Any]:
    """Parse timetable workbook (supporting Matrix Grid or Tabular format) and store in MongoDB."""
    if not filename.lower().endswith(".xlsx"):
        raise ValueError("Invalid file format. Only .xlsx files are supported.")

    try:
        wb = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=True)
    except Exception as e:
        raise ValueError(f"Failed to read Excel workbook: {str(e)}")

    records_to_insert = []
    total_rows = 0
    failed_rows = 0
    errors = []

    # Process all sheets in workbook
    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        rows = list(ws.iter_rows(values_only=True))
        if not rows:
            continue

        first_row_non_empty = next((r for r in rows if any(r)), None)
        first_row_str = " ".join(str(c or "").lower() for c in first_row_non_empty) if first_row_non_empty else ""

        is_tabular = ("subject" in first_row_str and "period" in first_row_str) or ("start time" in first_row_str) or ("start_time" in first_row_str) or ("starttime" in first_row_str)

        # Check if sheet is a College Matrix Grid sheet (e.g. contains DAY in top rows)
        is_matrix_grid = False
        if not is_tabular:
            for r in range(1, min(15, ws.max_row + 1)):
                for c in range(1, min(6, ws.max_column + 1)):
                    val_upper = str(_get_cell_value(ws, r, c) or "").strip().upper()
                    if "DAY" in val_upper or "TIME TABLE" in val_upper or any(k in val_upper for k in ["MON", "TUE", "WED", "THU", "FRI", "SAT"]):
                        is_matrix_grid = True
                        break
                if is_matrix_grid:
                    break

        if is_matrix_grid:
            matrix_records = _parse_matrix_timetable_excel(ws, sheet_name)
            records_to_insert.extend(matrix_records)
            total_rows += len(matrix_records)
            continue

        # Standard Tabular parsing fallback

        header_row = [str(cell).strip() if cell is not None else "" for cell in rows[0]]
        header_lower = [h.lower() for h in header_row]

        col_map = {}
        for idx, h in enumerate(header_lower):
            col_map[h] = idx

        default_section = sheet_name.strip().upper() if "-" in sheet_name or len(sheet_name) <= 10 else None

        for row_idx, row_values in enumerate(rows[1:], start=2):
            if not any(row_values):
                continue

            total_rows += 1
            row_errors = []

            def get_cell(key: str) -> str:
                idx = col_map.get(key)
                if idx is not None and idx < len(row_values) and row_values[idx] is not None:
                    return str(row_values[idx]).strip()
                return ""

            year = get_cell("year") or "Standard"
            section = get_cell("section").upper() or default_section
            if section and not re.match(r"^(I|II|III|IV)-", section):
                section = f"II-{section}"
            day = get_cell("day").capitalize()
            period_raw = get_cell("period")
            start_time_raw = get_cell("start time") or get_cell("starttime") or get_cell("start_time")
            end_time_raw = get_cell("end time") or get_cell("endtime") or get_cell("end_time")
            subject = get_cell("subject")
            faculty = get_cell("faculty")
            room = get_cell("room")

            if not section:
                row_errors.append("Section name is required.")
            if day not in DAYS_OF_WEEK:
                row_errors.append(f"Invalid Day: '{day}'. Must be one of {DAYS_OF_WEEK}.")

            try:
                period_num = int(re.sub(r"\D", "", period_raw))
            except Exception:
                period_num = 1
                if not period_raw:
                    row_errors.append("Period number is required.")

            start_time = _format_time_str(start_time_raw)
            end_time = _format_time_str(end_time_raw)

            if not re.match(r"^\d{2}:\d{2}$", start_time):
                row_errors.append(f"Invalid Start Time format: '{start_time_raw}'. Expected HH:MM.")
            if not re.match(r"^\d{2}:\d{2}$", end_time):
                row_errors.append(f"Invalid End Time format: '{end_time_raw}'. Expected HH:MM.")
            if not subject:
                row_errors.append("Subject name is required.")

            if row_errors:
                failed_rows += 1
                errors.append({"sheet": sheet_name, "row": row_idx, "errors": row_errors})
                continue

            if ":" in subject:
                subj_clean, fac_from_subj, room_from_subj = _parse_subject_and_faculty(subject)
                subject = subj_clean
                if not room and room_from_subj:
                    room = room_from_subj
                if fac_from_subj:
                    faculty_names = fac_from_subj
                elif faculty:
                    faculty_names = [f.strip() for f in faculty.split(",") if f.strip() and len(f.strip()) > 1]
                else:
                    faculty_names = []
            elif faculty:
                if ":" in faculty:
                    _, faculty_names, _ = _parse_subject_and_faculty(faculty)
                else:
                    faculty_names = [f.strip() for f in faculty.split(",") if f.strip() and len(f.strip()) > 1]
            else:
                faculty_names = []

            faculty_display = ", ".join(faculty_names) if faculty_names else (faculty if faculty else None)

            records_to_insert.append(
                {
                    "year": year,
                    "section": section,
                    "day": day,
                    "period": period_num,
                    "start_time": start_time,
                    "end_time": end_time,
                    "subject": subject,
                    "faculty": faculty_display,
                    "faculty_names": faculty_names,
                    "room": room if room else None,
                    "updated_at": datetime.now(timezone.utc),
                }
            )

    if not records_to_insert and errors:
        return {
            "total_rows": total_rows,
            "inserted": 0,
            "failed": failed_rows,
            "errors": errors,
        }

    db = get_database()

    inserted_count = 0
    section_map = {}
    for rec in records_to_insert:
        await db.timetables.update_one(
            {
                "section": rec["section"],
                "day": rec["day"],
                "period": rec["period"],
            },
            {"$set": rec},
            upsert=True,
        )
        inserted_count += 1
        sec = rec["section"]
        yr = rec.get("year", "2nd Year")
        if sec not in section_map:
            section_map[sec] = yr

    # Auto-upsert sections into db.sections so sessions can be generated
    for sec, yr in section_map.items():
        await db.sections.update_one(
            {"section_name": sec},
            {
                "$set": {
                    "section_name": sec,
                    "year": yr,
                    "is_active": True,
                    "updated_at": datetime.now(timezone.utc),
                },
                "$setOnInsert": {
                    "created_at": datetime.now(timezone.utc),
                    "assigned_cr_id": None,
                    "assigned_lr_id": None,
                },
            },
            upsert=True,
        )

    # Persist all individual faculty members as distinct records in users collection
    all_fac_names = set()
    for rec in records_to_insert:
        for f_name in rec.get("faculty_names", []):
            if f_name and len(f_name) > 1:
                all_fac_names.add(f_name.strip())

    for f_name in all_fac_names:
        existing_u = await db.users.find_one({"name": f_name})
        if not existing_u:
            clean_email_prefix = re.sub(r'[^a-z0-9]', '', f_name.lower())
            fac_email = f"{clean_email_prefix}@nrtec.in" if clean_email_prefix else f"fac_{ObjectId()}@nrtec.in"
            await db.users.update_one(
                {"name": f_name},
                {
                    "$setOnInsert": {
                        "name": f_name,
                        "email": fac_email,
                        "role": "FACULTY",
                        "password_hash": hash_password("faculty1234"),
                        "is_active": True,
                        "created_at": datetime.now(timezone.utc),
                        "updated_at": datetime.now(timezone.utc),
                    }
                },
                upsert=True,
            )

    await db.audit_logs.insert_one(
        {
            "actor_id": actor_id,
            "action": "IMPORT_TIMETABLE_EXCEL",
            "metadata": {
                "total_rows": total_rows,
                "inserted": inserted_count,
                "failed": failed_rows,
            },
            "created_at": datetime.now(timezone.utc),
        }
    )

    return {
        "total_rows": total_rows,
        "inserted": inserted_count,
        "failed": failed_rows,
        "errors": errors,
    }


# ----------------------------------------------------
# MENTOR EXCEL PROCESSING
# ----------------------------------------------------

def generate_mentor_excel_template() -> bytes:
    """Generate a clean .xlsx template for Mentor bulk import matching standard college faculty attributes."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Mentor_Import_Template"

    headers = ["S.NO", "NAME", "ID/EMPLOYEE ID", "MAIL ID/ EMAIL", "DESIGN/DESIGNATION", "BRANCH/DEPARTMENT", "MOBILE NO"]
    ws.append(headers)

    header_fill = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")

    for col_num in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col_num)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")

    samples = [
        ["1", "SIVA NAGESWARA RAO SIVARATRI", "605101", "drssnr@nrtec.in", "PROFESSOR", "CSE", "8977987777"],
        ["2", "MOTURI SIREESHA", "905101", "moturisireesha@gmail.com", "ASSOCIATE PROFESSOR", "CSE", "9492468445"],
        ["3", "NAGA TIRUMALA RAO TIRUMALA RAO", "1105101", "csehod@nrtec.in", "PROFESSOR & HOD", "CSE", "8247394015"],
        ["4", "PRASAD MANCHIKANTI", "1310116", "mprasad@nrtec.in", "ASSISTANT PROFESSOR", "CSE", "9885466378"],
        ["5", "KHAJA MOHIDDIN BASHA SHAIK", "1605104", "sk.basha579@gmail.com", "ASSISTANT PROFESSOR", "CSE", "8096622595"],
    ]
    for row in samples:
        ws.append(row)

    for col in ws.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        col_letter = get_column_letter(col[0].column)
        ws.column_dimensions[col_letter].width = max(max_len + 4, 18)

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()


def extract_raw_rows_from_file(file_bytes: bytes, filename: str) -> List[List[str]]:
    """
    Extracts raw string rows from any uploaded workbook or text file (.xlsx, .xls, .csv, .tsv, or HTML tables formatted as .xls).
    Tries xlrd, openpyxl, pandas, html parsing, and csv readers across all sheets to ensure 100% compatibility.
    """
    raw_rows: List[List[str]] = []
    if not file_bytes:
        return raw_rows

    is_zip = file_bytes.startswith(b"PK")
    is_ole = file_bytes.startswith(b"\xd0\xcf\x11\xe0")
    fn_lower = filename.lower()

    # 1. Try xlrd for BIFF8 binary .xls files first if OLE header or .xls extension
    if is_ole or fn_lower.endswith(".xls"):
        try:
            import xlrd
            wb = xlrd.open_workbook(file_contents=file_bytes)
            all_sheets_rows = []
            for sheet in wb.sheets():
                for r in range(sheet.nrows):
                    row_vals = sheet.row_values(r)
                    clean_r = []
                    for c in row_vals:
                        if isinstance(c, float) and c.is_integer():
                            clean_r.append(str(int(c)))
                        elif c is not None:
                            s = str(c).strip()
                            if s.endswith(".0"):
                                s = s[:-2]
                            clean_r.append(s)
                        else:
                            clean_r.append("")
                    if any(clean_r):
                        all_sheets_rows.append(clean_r)
            if all_sheets_rows:
                return all_sheets_rows
        except Exception:
            pass

    # 2. Try openpyxl for OpenXML .xlsx files
    if is_zip or fn_lower.endswith(".xlsx"):
        try:
            wb = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=True)
            all_sheets_rows = []
            for ws_name in wb.sheetnames:
                ws = wb[ws_name]
                for row in ws.iter_rows(values_only=True):
                    clean_r = []
                    for cell in row:
                        if isinstance(cell, float) and cell.is_integer():
                            clean_r.append(str(int(cell)))
                        elif cell is not None:
                            s = str(cell).strip()
                            if s.endswith(".0"):
                                s = s[:-2]
                            clean_r.append(s)
                        else:
                            clean_r.append("")
                    if any(clean_r):
                        all_sheets_rows.append(clean_r)
            if all_sheets_rows:
                return all_sheets_rows
        except Exception:
            pass

    # 3. Try pandas with all available engines
    try:
        import pandas as pd
        excel_file = pd.ExcelFile(io.BytesIO(file_bytes))
        all_df_rows = []
        for sheet_name in excel_file.sheet_names:
            df = excel_file.parse(sheet_name, header=None)
            df = df.fillna("")
            rows = df.astype(str).values.tolist()
            for r in rows:
                clean_r = [c.strip()[:-2] if c.strip().endswith(".0") else c.strip() for c in r]
                if any(clean_r):
                    all_df_rows.append(clean_r)
        if all_df_rows:
            return all_df_rows
    except Exception:
        pass

    # 4. Check for HTML Table export files
    text = ""
    for encoding in ["utf-8-sig", "utf-8", "latin1", "cp1252", "utf-16", "iso-8859-1"]:
        try:
            text = file_bytes.decode(encoding)
            break
        except Exception:
            continue

    if text and ("<tr" in text.lower() or "<table" in text.lower()):
        try:
            import pandas as pd
            dfs = pd.read_html(io.StringIO(text), header=None)
            if dfs:
                all_html_rows = []
                for df in dfs:
                    df = df.fillna("")
                    rows = df.astype(str).values.tolist()
                    for r in rows:
                        clean_r = [c.strip()[:-2] if c.strip().endswith(".0") else c.strip() for c in r]
                        if any(clean_r):
                            all_html_rows.append(clean_r)
                if all_html_rows:
                    return all_html_rows
        except Exception:
            pass

        try:
            soup_rows = re.findall(r'<tr[^>]*>(.*?)</tr>', text, re.IGNORECASE | re.DOTALL)
            for tr in soup_rows:
                cells = re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', tr, re.IGNORECASE | re.DOTALL)
                clean_cells = [re.sub(r'<[^>]+>', '', c).strip() for c in cells]
                if any(clean_cells):
                    raw_rows.append(clean_cells)
            if raw_rows:
                return raw_rows
        except Exception:
            pass

    # 5. CSV / TSV / Delimited text parsing
    if text:
        text_clean = text.replace("\x00", "")
        lines = [l.strip() for l in text_clean.splitlines() if l.strip()]
        if lines:
            delimiter = ","
            if "\t" in lines[0] and lines[0].count("\t") > lines[0].count(","):
                delimiter = "\t"
            elif ";" in lines[0] and lines[0].count(";") > lines[0].count(","):
                delimiter = ";"

            try:
                reader = csv.reader(io.StringIO(text_clean), delimiter=delimiter)
                for r in reader:
                    clean_r = [str(c).strip() if c is not None else "" for c in r]
                    if any(clean_r):
                        raw_rows.append(clean_r)
                if raw_rows:
                    return raw_rows
            except Exception:
                pass

    return raw_rows


async def parse_and_import_mentor_excel(
    file_bytes: bytes, filename: str, actor_id: str
) -> Dict[str, Any]:
    """Parse Mentor Excel (.xlsx, .xls) or CSV (.csv) file and safely import mentors into users collection."""
    fn_lower = filename.lower()
    if not (fn_lower.endswith(".xlsx") or fn_lower.endswith(".xls") or fn_lower.endswith(".csv")):
        raise ValueError("Invalid file format. Only .xlsx, .xls, or .csv files are supported.")

    raw_rows = extract_raw_rows_from_file(file_bytes, filename)
    if not raw_rows:
        raise ValueError("File is empty or could not be read.")

    header_idx = -1
    col_map: Dict[str, int] = {}

    ID_ALIASES = {
        "id", "employeeid", "empid", "mentorid", "facid", "facultyid",
        "empcode", "code", "username", "empno", "idno", "idemployeeid",
        "userid", "empidno", "facultycode",
    }
    NAME_ALIASES = {
        "name", "fullname", "facultyname", "mentorname", "faculty",
        "mentor", "teacher", "employeename", "staffname",
    }
    EMAIL_ALIASES = {
        "email", "mailid", "mail", "emailid", "emailaddress",
        "mailidemail", "officialemail", "personalemail", "emailidmailid",
    }
    DESIG_ALIASES = {
        "designation", "design", "desig", "designdesignation",
        "post", "role", "roles", "position",
    }
    DEPT_ALIASES = {
        "department", "dept", "branch", "stream", "branchdepartment",
        "discipline", "deptbranch",
    }
    PHONE_ALIASES = {
        "mobileno", "mobile", "phone", "contact", "cell",
        "mobilenumber", "phonenumber", "contactnumber", "cellno",
        "contactno", "mobilephone",
    }
    PROFILE_ALIASES = {
        "profile", "profilerole", "userprofile", "userroles",
        "rolesassigned", "profileassigned",
    }

    # Extended Header Range: Search top 30 rows
    for idx, row in enumerate(raw_rows[:30]):
        row_cleaned = [re.sub(r'[^a-z0-9]', '', str(cell or "").lower()) for cell in row]

        has_id_header = any(
            c in ID_ALIASES
            or "employeeid" in c
            or "empid" in c
            or "mentorid" in c
            or "facultyid" in c
            or "idemployee" in c
            or c == "id"
            for c in row_cleaned
        )
        has_name_header = any(
            c in NAME_ALIASES
            or (("name" in c or "faculty" in c or "mentor" in c) and "father" not in c and "file" not in c and "user" not in c)
            for c in row_cleaned
        )

        if has_name_header or has_id_header:
            temp_map: Dict[str, int] = {}
            for c_idx, c_norm in enumerate(row_cleaned):
                if not c_norm or c_norm in ["sno", "slno", "serialno", "serialnumber"]:
                    continue

                # 1. Profile
                if c_norm in PROFILE_ALIASES or "profile" in c_norm:
                    if "profile" not in temp_map:
                        temp_map["profile"] = c_idx

                # 2. Mobile / Phone
                elif c_norm in PHONE_ALIASES or any(k in c_norm for k in ["mobile", "phone", "contact", "cell"]):
                    if "phone" not in temp_map:
                        temp_map["phone"] = c_idx

                # 3. Email / Mail ID
                elif c_norm in EMAIL_ALIASES or any(k in c_norm for k in ["email", "mail"]):
                    if "email" not in temp_map:
                        temp_map["email"] = c_idx

                # 4. Designation
                elif c_norm in DESIG_ALIASES or any(k in c_norm for k in ["designation", "design", "desig", "post"]):
                    if "designation" not in temp_map:
                        temp_map["designation"] = c_idx

                # 5. Department / Branch
                elif c_norm in DEPT_ALIASES or any(k in c_norm for k in ["department", "dept", "branch", "stream", "discipline"]):
                    if "department" not in temp_map:
                        temp_map["department"] = c_idx

                # 6. Mentor / Employee ID / User Name
                elif (
                    c_norm in ID_ALIASES
                    or any(k in c_norm for k in ["employeeid", "mentorid", "facid", "facultyid", "empid", "empcode", "username", "idemployee"])
                    or c_norm == "id"
                ):
                    if "mentor_id" not in temp_map or "employee" in c_norm or "mentor" in c_norm or "empid" in c_norm:
                        temp_map["mentor_id"] = c_idx

                # 7. Name
                elif (
                    c_norm in NAME_ALIASES
                    or (any(k in c_norm for k in ["name", "faculty", "mentor", "teacher"])
                        and "user" not in c_norm and "file" not in c_norm and "father" not in c_norm and "id" not in c_norm)
                ):
                    if "name" not in temp_map:
                        temp_map["name"] = c_idx

            if len(temp_map) >= 2 and ("name" in temp_map or "mentor_id" in temp_map):
                header_idx = idx
                col_map = temp_map
                break

    # Positional fallback if headers could not be matched
    if (header_idx == -1 or "name" not in col_map or "mentor_id" not in col_map) and len(raw_rows) >= 1:
        for f_idx in range(min(10, len(raw_rows))):
            row_str = [str(c or "").strip() for c in raw_rows[f_idx]]
            row_clean = [re.sub(r'[^a-z0-9]', '', c.lower()) for c in row_str]
            for c_i, c_val in enumerate(row_clean):
                if ("id" in c_val or "emp" in c_val or "code" in c_val) and "mentor_id" not in col_map:
                    col_map["mentor_id"] = c_i
                elif ("name" in c_val or "faculty" in c_val or "mentor" in c_val) and "name" not in col_map:
                    col_map["name"] = c_i

            if "name" in col_map or "mentor_id" in col_map:
                header_idx = f_idx
                break

        if "name" not in col_map and len(raw_rows[0]) > 1:
            col_map["name"] = 1 if len(raw_rows[0]) > 1 else 0
        if "mentor_id" not in col_map:
            col_map["mentor_id"] = 2 if len(raw_rows[0]) > 2 else (0 if col_map.get("name") != 0 else 1)
        if header_idx == -1:
            header_idx = 0

    db = get_database()
    existing_users = await db.users.find({"role": UserRole.MENTOR.value}).to_list(length=10000)
    existing_by_id = {str(u.get("mentor_id") or u.get("roll_number") or "").upper(): str(u["_id"]) for u in existing_users if u.get("mentor_id") or u.get("roll_number")}
    existing_by_email = {str(u["email"]).lower(): str(u["_id"]) for u in existing_users if u.get("email")}

    seen_ids_in_file: set = set()
    total_rows = 0
    created_count = 0
    updated_count = 0
    failed_count = 0
    errors = []

    def clean_val(val: Any) -> str:
        if val is None:
            return ""
        s = str(val).strip()
        if s.endswith(".0") and re.match(r"^\d+\.0$", s):
            s = s[:-2]
        # Strip special/corrupt unicode characters like â, Â, \xa0, \u200b, \ufeff
        s = re.sub(r"[Ââ\xa0\u200b\ufeff\r\n\t]+", " ", s)
        # Collapse multiple whitespace
        s = re.sub(r"\s+", " ", s).strip()
        return s

    for row_idx, row_values in enumerate(raw_rows[header_idx + 1:], start=header_idx + 2):
        if not any(row_values):
            continue

        def get_field(col_key: str) -> str:
            c_i = col_map.get(col_key)
            if c_i is not None and c_i < len(row_values):
                return clean_val(row_values[c_i])
            return ""

        raw_mentor_id = get_field("mentor_id")
        raw_name = get_field("name")
        raw_email = get_field("email")
        designation = get_field("designation")
        department = get_field("department")
        raw_phone = get_field("phone")
        profile = get_field("profile")
        password = get_field("password")

        # Sanitize specific fields
        mentor_id = re.sub(r'[^a-zA-Z0-9_\-/]', '', raw_mentor_id).upper().strip()
        name = raw_name.strip()
        email = re.sub(r'[^a-zA-Z0-9_.+@-]', '', raw_email).lower().strip()
        phone = re.sub(r'[^0-9+]', '', raw_phone).strip()

        name_upper = name.upper()
        mentor_id_upper = mentor_id.upper()

        # Skip repeated header rows or section banner rows
        if (
            (not mentor_id or mentor_id_upper in ["ID", "EMPLOYEEID", "USERNAME", "MENTORID", "IDEMPLOYEEID"])
            and (not name or name_upper in ["NAME", "FULL NAME", "FACULTY NAME", "MENTOR NAME", "TEACHING", "NON-TEACHING", "S.NO", "SL.NO"] or name_upper.startswith("S.N"))
        ):
            continue

        total_rows += 1
        row_errors = []

        if not name:
            row_errors.append("Mentor Name is required.")
        if not mentor_id and not email:
            row_errors.append("Mentor ID or Email is required.")

        if row_errors:
            failed_count += 1
            errors.append({"row": row_idx, "mentor_id": mentor_id or "N/A", "errors": row_errors})
            continue

        if not mentor_id and email:
            mentor_id = email.split("@")[0].upper()

        if not email:
            clean_id_email = re.sub(r'[^a-zA-Z0-9]', '', mentor_id.lower())
            email = f"{clean_id_email}@nrtec.in"

        now = datetime.now(timezone.utc)
        target_id = existing_by_id.get(mentor_id) or existing_by_email.get(email)

        # Default password is the mentor's ID number
        pwd_to_use = password.strip() if password and password.strip() else mentor_id

        update_fields: Dict[str, Any] = {
            "name": name,
            "email": email,
            "mentor_id": mentor_id,
            "roll_number": mentor_id,
            "updated_at": now,
        }
        if phone:
            update_fields["phone"] = phone
        if designation:
            update_fields["designation"] = designation
        if department:
            update_fields["department"] = department
        if profile:
            update_fields["profile"] = profile
        if password:
            update_fields["password_hash"] = hash_password(pwd_to_use)

        if mentor_id and mentor_id in seen_ids_in_file:
            if target_id:
                query = {"_id": ObjectId(target_id)} if ObjectId.is_valid(target_id) else {"_id": target_id}
                await db.users.update_one(query, {"$set": update_fields})
                updated_count += 1
            continue
        elif mentor_id:
            seen_ids_in_file.add(mentor_id)

        if target_id:
            query = {"_id": ObjectId(target_id)} if ObjectId.is_valid(target_id) else {"_id": target_id}
            await db.users.update_one(query, {"$set": update_fields})
            updated_count += 1
        else:
            new_doc = {
                "name": name,
                "email": email,
                "mentor_id": mentor_id,
                "roll_number": mentor_id,
                "password_hash": hash_password(pwd_to_use),
                "role": UserRole.MENTOR.value,
                "phone": phone if phone else None,
                "designation": designation if designation else None,
                "department": department if department else None,
                "profile": profile if profile else None,
                "is_active": True,
                "created_at": now,
                "updated_at": now,
            }
            res = await db.users.insert_one(new_doc)
            new_str_id = str(res.inserted_id)
            existing_by_id[mentor_id] = new_str_id
            existing_by_email[email] = new_str_id
            created_count += 1

    await db.audit_logs.insert_one({
        "actor_id": actor_id,
        "action": "IMPORT_MENTORS_EXCEL",
        "metadata": {"total_rows": total_rows, "created": created_count, "updated": updated_count, "failed": failed_count},
        "created_at": datetime.now(timezone.utc),
    })

    return {
        "total_rows": total_rows,
        "created": created_count,
        "updated": updated_count,
        "failed": failed_count,
        "errors": errors,
    }


# ----------------------------------------------------
# STUDENT EXCEL PROCESSING
# ----------------------------------------------------

def generate_student_excel_template() -> bytes:
    """Generate a clean .xlsx template for Student bulk import."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Student_Import_Template"

    headers = ["name", "rollNumber", "branch", "batch", "section", "parentPhone", "studentPhone"]
    ws.append(headers)

    header_fill = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")

    for col_num in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col_num)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")

    samples = [
        ["BODAPATI PALLAVI", "24471A0575", "CSE", 2029, "J", "9642648130", "9505371832"],
        ["RAHUL KUMAR", "24471A0501", "CSE", 2029, "A", "9876543210", "9876543299"],
        ["SNEHA SHARMA", "23471A0502", "CSE", 2028, "B", "9876543211", "9876543298"],
    ]
    for row in samples:
        ws.append(row)

    for col in ws.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        col_letter = get_column_letter(col[0].column)
        ws.column_dimensions[col_letter].width = max(max_len + 4, 18)

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()


async def parse_and_import_student_excel(
    file_bytes: bytes, filename: str, actor_id: str
) -> Dict[str, Any]:
    """Parse Student Excel workbook or CSV file and safely import students into students collection."""
    fn_lower = filename.lower()
    if not (fn_lower.endswith(".xlsx") or fn_lower.endswith(".xls") or fn_lower.endswith(".csv")):
        raise ValueError("Invalid file format. Only .xlsx, .xls, or .csv files are supported.")

    raw_rows = extract_raw_rows_from_file(file_bytes, filename)
    if not raw_rows:
        raise ValueError("File is empty or could not be read.")

    header_idx = -1
    col_map = {}

    NAME_ALIASES = {"name", "studentname", "fullname", "student"}
    ROLL_ALIASES = {"rollnumber", "rollno", "roll", "pin", "htno", "regno", "reg"}
    BRANCH_ALIASES = {"branch", "department", "dept", "stream"}
    BATCH_ALIASES = {"batch", "passoutyear", "graduationyear", "joiningyear"}
    SECTION_ALIASES = {"section", "sec"}
    PARENT_PHONE_ALIASES = {"parentphone", "parentmobile", "fatherphone", "fathermobile", "guardianphone", "parent"}
    STUDENT_PHONE_ALIASES = {"studentphone", "studentmobile", "phone", "mobile", "mobileno", "phoneno", "contact"}

    for idx, row in enumerate(raw_rows[:30]):
        row_cleaned = [re.sub(r'[^a-z0-9]', '', str(cell).lower()) for cell in row]
        has_roll = any(c in ROLL_ALIASES or "roll" in c or "htno" in c or "pin" in c for c in row_cleaned)
        has_name = any(c in NAME_ALIASES or ("name" in c and "father" not in c and "file" not in c) for c in row_cleaned)

        if has_name or has_roll:
            temp_map = {}
            for c_idx, c_norm in enumerate(row_cleaned):
                if not c_norm or c_norm in ["sno", "slno"]:
                    continue

                if c_norm in NAME_ALIASES or ("name" in c_norm and "father" not in c_norm and "file" not in c_norm and "roll" not in c_norm):
                    if "name" not in temp_map:
                        temp_map["name"] = c_idx
                elif c_norm in ROLL_ALIASES or "roll" in c_norm or "htno" in c_norm or "pin" in c_norm:
                    if "roll_number" not in temp_map:
                        temp_map["roll_number"] = c_idx
                elif c_norm in BRANCH_ALIASES or "branch" in c_norm or "dept" in c_norm or "stream" in c_norm:
                    if "branch" not in temp_map:
                        temp_map["branch"] = c_idx
                elif c_norm in BATCH_ALIASES or "batch" in c_norm:
                    if "batch" not in temp_map:
                        temp_map["batch"] = c_idx
                elif "year" in c_norm:
                    if "year" not in temp_map:
                        temp_map["year"] = c_idx
                elif c_norm in SECTION_ALIASES or "sec" in c_norm:
                    if "section" not in temp_map:
                        temp_map["section"] = c_idx
                elif c_norm in PARENT_PHONE_ALIASES or "parent" in c_norm or "father" in c_norm or "guardian" in c_norm:
                    if "parent_phone" not in temp_map:
                        temp_map["parent_phone"] = c_idx
                elif c_norm in STUDENT_PHONE_ALIASES or "phone" in c_norm or "mobile" in c_norm:
                    if "student_phone" not in temp_map:
                        temp_map["student_phone"] = c_idx

            if len(temp_map) >= 2 and ("name" in temp_map or "roll_number" in temp_map):
                header_idx = idx
                col_map = temp_map
                break

    if header_idx == -1:
        header_idx = 0
        col_map = {"name": 0, "roll_number": 1, "branch": 2, "batch": 3, "section": 4, "parent_phone": 5, "student_phone": 6}

    if "name" not in col_map and "roll_number" not in col_map:
        raise ValueError("Invalid Student Roster file format! The uploaded file does not contain required Student headers (Roll Number and Student Name). Please upload a valid Student Roster Excel/CSV file.")

    inferred_year = "2nd Year"
    inferred_batch = 2029
    if "3" in fn_lower or "iii" in fn_lower:
        inferred_year = "3rd Year"
        inferred_batch = 2028
    elif "4" in fn_lower or "iv" in fn_lower:
        inferred_year = "4th Year"
        inferred_batch = 2027
    elif "1" in fn_lower or "i" in fn_lower:
        inferred_year = "1st Year"
        inferred_batch = 2030

    inferred_section = "A"
    sec_match = re.search(r'([i|v|x]+-cse-[a-z]+|cse-[a-z]+|section-[a-z]+)', fn_lower)
    if sec_match:
        inferred_section = sec_match.group(1).upper()

    db = get_database()
    existing_students = await db.students.find({}, {"roll_number": 1}).to_list(length=10000)
    existing_rolls = {s["roll_number"].upper(): str(s["_id"]) for s in existing_students if s.get("roll_number")}

    seen_rolls_in_file = set()
    total_rows = 0
    created_count = 0
    updated_count = 0
    failed_count = 0
    errors = []

    def clean_val(val: Any) -> str:
        if val is None:
            return ""
        s = str(val).strip()
        if s.endswith(".0"):
            s = s[:-2]
        s = re.sub(r'^[âÂ\xa0\s]+', '', s).strip()
        return s

    for row_idx, row_values in enumerate(raw_rows[header_idx + 1:], start=header_idx + 2):
        if not any(row_values):
            continue

        def get_field(col_key: str) -> str:
            c_i = col_map.get(col_key)
            if c_i is not None and c_i < len(row_values):
                return clean_val(row_values[c_i])
            return ""

        name = get_field("name")
        roll = get_field("roll_number").upper()
        branch = get_field("branch") or "CSE"
        batch_raw = get_field("batch")
        year_raw = get_field("year")
        section = get_field("section").upper() or inferred_section
        student_phone = get_field("student_phone")
        parent_phone = get_field("parent_phone")

        if not roll and not name:
            continue
        if roll in ["ROLL NUMBER", "ROLL NO", "PIN", "HT NO", "S.NO", "ROLLNUMBER"]:
            continue

        # Calculate year and batch
        if batch_raw:
            batch = int(batch_raw) if str(batch_raw).strip().isdigit() else batch_raw
            year = compute_year_from_batch(batch)
        elif year_raw:
            year = year_raw
            inferred_from_roll = infer_batch_from_roll(roll)
            batch = inferred_from_roll if inferred_from_roll else inferred_batch
        else:
            inferred_from_roll = infer_batch_from_roll(roll)
            if inferred_from_roll:
                batch = inferred_from_roll
                year = compute_year_from_batch(batch)
            else:
                batch = inferred_batch
                year = compute_year_from_batch(batch)

        total_rows += 1
        row_errors = []

        if not name:
            row_errors.append("Student Name is required.")
        if not roll:
            row_errors.append("Roll Number is required.")

        if roll and roll in seen_rolls_in_file:
            row_errors.append(f"Duplicate roll number '{roll}' within file.")
        elif roll:
            seen_rolls_in_file.add(roll)

        if row_errors:
            failed_count += 1
            errors.append({"row": row_idx, "roll_number": roll or "N/A", "errors": row_errors})
            continue

        crlr_id, crlr_name = await find_crlr_for_student(db, year, section)

        now = datetime.now(timezone.utc)
        student_doc = {
            "batch": batch,
            "branch": branch,
            "year": year,
            "name": name,
            "roll_number": roll,
            "section": section,
            "student_phone": student_phone if student_phone else None,
            "parent_phone": parent_phone if parent_phone else None,
            "crlr_id": crlr_id,
            "crlr_name": crlr_name,
            "updated_at": now,
        }

        if roll in existing_rolls:
            s_id = existing_rolls[roll]
            await db.students.update_one({"_id": ObjectId(s_id)}, {"$set": student_doc})
            updated_count += 1
        else:
            student_doc["created_at"] = now
            res = await db.students.insert_one(student_doc)
            existing_rolls[roll] = str(res.inserted_id)
            created_count += 1

    await db.audit_logs.insert_one({
        "actor_id": actor_id,
        "action": "IMPORT_STUDENTS_EXCEL",
        "metadata": {"total_rows": total_rows, "created": created_count, "updated": updated_count, "failed": failed_count},
        "created_at": datetime.now(timezone.utc),
    })

    return {
        "total_rows": total_rows,
        "created": created_count,
        "updated": updated_count,
        "failed": failed_count,
        "errors": errors,
    }

