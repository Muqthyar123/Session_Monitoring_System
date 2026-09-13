import io
import re
from datetime import datetime, time, timezone
from typing import Any, Dict, List, Tuple
import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from pydantic import EmailStr, TypeAdapter
from app.core.security import hash_password
from app.db.mongodb import get_database
from app.schemas.user import UserRole

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
    # Match H:MM or HH:MM
    match = re.match(r"^(\d{1,2}):(\d{2})", val_str)
    if match:
        h, m = int(match.group(1)), int(match.group(2))
        return f"{h:02d}:{m:02d}"
    return val_str


async def parse_and_import_timetable_excel(
    file_bytes: bytes, filename: str, actor_id: str
) -> Dict[str, Any]:
    """Parse timetable workbook and store validated timetable records in MongoDB."""
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

        header_row = [str(cell).strip() if cell is not None else "" for cell in rows[0]]
        header_lower = [h.lower() for h in header_row]

        # Determine column positions
        col_map = {}
        for idx, h in enumerate(header_lower):
            col_map[h] = idx

        # If sheet name looks like a section (e.g. "II-A"), use it as default section if missing in columns
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

            # Validate period number
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

            records_to_insert.append(
                {
                    "year": year,
                    "section": section,
                    "day": day,
                    "period": period_num,
                    "start_time": start_time,
                    "end_time": end_time,
                    "subject": subject,
                    "faculty": faculty if faculty else None,
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
    # Store records using upsert to avoid duplicate key errors
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

    # Log audit entry
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
