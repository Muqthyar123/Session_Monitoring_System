"""Authorized absentee exports and parent/student call history."""
import csv
import io
import re
from datetime import datetime, timezone
from typing import Literal, Optional
import zoneinfo

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.dependencies import enforce_assigned_department, enforce_assigned_year, get_assigned_years, is_legacy_unscoped_admin, require_roles
from app.db.mongodb import get_database
from app.schemas.user import UserRole
from app.services.mentor_mapping_service import get_mentor_assigned_student_ids
from app.services.student_service import build_year_filter_clause

router = APIRouter(tags=["Absentee History Exports and Calls"])
local_tz = zoneinfo.ZoneInfo(settings.TIMEZONE)


def _parse_day(value: Optional[str]) -> Optional[str]:
    if value is None or value == "":
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date().isoformat()
    except ValueError:
        raise HTTPException(422, "Dates must use YYYY-MM-DD format.") from None


async def _scoped_absences(db, user: dict, year: Optional[str], section: Optional[str], roll_number: Optional[str], branch: Optional[str], from_date: Optional[str], to_date: Optional[str]):
    query_parts: list[dict] = [{"status": "Absent"}]
    if year: query_parts.append(build_year_filter_clause(year))
    if section:
        sec = section.strip().upper(); tail = sec.split("-")[-1]
        query_parts.append({"$or": [{"section": sec}, {"section": tail}, {"section": f"CSE-{tail}"}, {"section": {"$regex": f"(^|-){re.escape(tail)}$", "$options": "i"}}]})
    if branch: query_parts.append({"branch": branch.strip().upper()})
    if roll_number: query_parts.append({"roll_number": roll_number.strip().upper()})
    date_clause: dict = {}
    if from_date: date_clause["$gte"] = from_date
    if to_date: date_clause["$lte"] = to_date
    if date_clause: query_parts.append({"date": date_clause})
    if user.get("role") == UserRole.MENTOR.value:
        assigned_ids = await get_mentor_assigned_student_ids(user)
        if assigned_ids is None:
            # Only privileged roles may receive an unrestricted assignment set.
            raise HTTPException(403, "Mentor assignments could not be resolved; ask an administrator to review Mentor Mapping.")
        if not assigned_ids:
            raise HTTPException(403, "No mentor-to-student assignments are configured for this account. Ask an administrator to create or review a mapping.")
        oids = [ObjectId(item) for item in assigned_ids if ObjectId.is_valid(item)]
        assigned_students = await db.students.find({"_id": {"$in": oids}}, {"roll_number": 1}).to_list(length=10000)
        rolls = {str(s.get("roll_number", "")).strip().upper() for s in assigned_students if s.get("roll_number")}
        rolls.update(item.strip().upper() for item in assigned_ids if item and not ObjectId.is_valid(item))
        if roll_number and roll_number.strip().upper() not in rolls and roll_number.strip() not in assigned_ids:
            raise HTTPException(403, "This student is outside your mentor assignments.")
        query_parts.append({"$or": [{"student_id": {"$in": assigned_ids}}, {"roll_number": {"$in": sorted(rolls)}}]})
    elif user.get("role") == UserRole.ADMIN.value:
        if is_legacy_unscoped_admin(user):
            query = {"$and": query_parts}
            rows = []
            # The legacy first Admin remains global until explicitly assigned.
            for collection, default_session in ((db.student_attendance, "SESSION_1"), (db.student_attendance_sessions, None)):
                cursor = collection.find(query).sort([("date", -1), ("created_at", -1)])
                for doc in await cursor.to_list(length=10000):
                    doc["_id"] = str(doc["_id"])
                    doc.setdefault("session", default_session)
                    rows.append(doc)
            return sorted(rows, key=lambda row: (row.get("date", ""), row.get("created_at", "")), reverse=True)
        if year:
            enforce_assigned_year(user, year)
        years = get_assigned_years(user) or []
        department = enforce_assigned_department(user, None)
        if not years or not department:
            raise HTTPException(403, "HOD account has no configured department/year scope.")
        if section and department.casefold() not in section.casefold():
            raise HTTPException(403, "Access denied for this department's section.")
        query_parts.append({"year": {"$in": years}})
        query_parts.append({"$or": [{"branch": department}, {"department": department},
                                     {"section": {"$regex": f"(^|-)({re.escape(department)})(-|$)", "$options": "i"}}]})
    query = {"$and": query_parts}
    rows = []
    for collection, default_session in ((db.student_attendance, "SESSION_1"), (db.student_attendance_sessions, None)):
        data = await collection.find(query).sort([("date", 1), ("roll_number", 1)]).to_list(length=50001)
        for row in data:
            if default_session: row.setdefault("session_id", default_session)
            rows.append(row)
    return rows


def _cell(value):
    if value is None: return ""
    if isinstance(value, datetime):
        stamp = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        return stamp.astimezone(local_tz).strftime("%Y-%m-%d %H:%M:%S %Z")
    return str(value)


def _timestamp_in_range(value, start: Optional[str], end: Optional[str]) -> bool:
    if not isinstance(value, datetime):
        return True  # Legacy comments have no separate creation timestamp.
    stamp = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    day = stamp.astimezone(local_tz).date().isoformat()
    return (not start or day >= start) and (not end or day <= end)


@router.get("/history/absentee-export")
async def export_absentee_history(
    format: Literal["csv", "xlsx", "pdf"] = Query(...), year: Optional[str] = None,
    branch: Optional[str] = None, section: Optional[str] = None,
    roll_number: Optional[str] = Query(None, alias="rollNumber"),
    from_date: Optional[str] = Query(None, alias="fromDate"), to_date: Optional[str] = Query(None, alias="toDate"),
    user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.MENTOR])),
):
    start, end = _parse_day(from_date), _parse_day(to_date)
    if start and end and start > end: raise HTTPException(422, "From Date cannot be later than To Date.")
    if user.get("role") == UserRole.MENTOR.value and not (year or section or roll_number):
        raise HTTPException(422, "Mentor exports must select an assigned academic year, section, or student.")
    db = get_database()
    records = await _scoped_absences(db, user, year, section, roll_number, branch, start, end)
    if len(records) > 50000:
        raise HTTPException(413, "Export exceeds the 50,000 absentee record limit. Narrow the date range or section.")
    attendance_ids = [row["_id"] for row in records]
    id_strings = [str(item) for item in attendance_ids]
    students = {}
    student_ids = {str(row.get("student_id")) for row in records if row.get("student_id")}
    oids = [ObjectId(item) for item in student_ids if ObjectId.is_valid(item)]
    if oids:
        for student in await db.students.find({"_id": {"$in": oids}}).to_list(length=10000):
            students[str(student["_id"])] = student
    calls = await db.absentee_call_history.find({"attendance_record_id": {"$in": id_strings}, **({"initiated_date": {k: v for k, v in (("$gte", start), ("$lte", end)) if v}} if start or end else {})}).sort("initiated_at", 1).to_list(length=50000)
    call_map: dict[str, list] = {}
    for call in calls:
        call_map.setdefault(call.get("attendance_record_id", ""), []).append(call)
    table_rows = []
    for row in records:
        student = students.get(str(row.get("student_id")), {})
        item = {
            "Student Name": row.get("student_name") or student.get("name"), "Roll Number": row.get("roll_number"),
            "Registration Number": student.get("registration_number") or student.get("registrationNumber"),
            "Academic Year": row.get("year"), "Branch": row.get("branch") or student.get("branch"), "Section": row.get("section"),
            "Parent/Guardian Name": student.get("parent_name") or student.get("parentName"),
            "Parent Contact": row.get("parent_phone") or student.get("parent_phone"), "Student Contact": row.get("student_phone") or student.get("student_phone"),
            "Attendance Date": row.get("date"), "Attendance Session": row.get("session_id") or row.get("session"),
            "Subject": row.get("subject"), "Faculty": row.get("faculty"), "Absence Status": row.get("status"),
            "Mentor Comment": row.get("reason") if _timestamp_in_range(row.get("reason_updated_at"), start, end) else None,
            "Comment Created At": row.get("reason_updated_at") if row.get("reason") and _timestamp_in_range(row.get("reason_updated_at"), start, end) else None,
            "Mentor Name": row.get("reason_updated_by"), "CR/LR Submitter": row.get("submitted_by"),
            "Contacted Person": "", "Call Phone": "", "Call Staff": "", "Call Staff Role": "", "Call Initiation Status": "", "Call Initiated At": "", "Call Outcome": "", "Call Notes": "", "Call Outcome Updated By": "", "Call Updated At": "",
        }
        related_calls = call_map.get(str(row["_id"]), [])
        if not related_calls: table_rows.append(item)
        else:
            for call in related_calls:
                table_rows.append({**item, "Contacted Person": call.get("contact_type"), "Call Phone": call.get("phone_number"), "Call Staff": call.get("staff_name"), "Call Staff Role": call.get("staff_role"), "Call Initiation Status": call.get("initiation_status"), "Call Initiated At": _cell(call.get("initiated_at")), "Call Outcome": call.get("outcome") or "Pending Outcome", "Call Notes": call.get("follow_up_notes"), "Call Outcome Updated By": call.get("outcome_updated_by"), "Call Updated At": _cell(call.get("outcome_updated_at"))})
    columns = list(table_rows[0].keys()) if table_rows else ["Student Name", "Roll Number", "Academic Year", "Branch", "Section", "Attendance Date", "Attendance Session", "Absence Status", "Mentor Comment", "Comment Created At", "CR/LR Submitter", "Contacted Person", "Call Phone", "Call Initiated At", "Call Outcome", "Call Notes"]
    stem = f"Absentee_History_{(year or 'All_Years').replace(' ', '_')}"
    if format == "csv":
        output = io.StringIO(newline="")
        writer = csv.DictWriter(output, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows([{key: _cell(value) for key, value in row.items()} for row in table_rows])
        body, media, suffix = output.getvalue().encode("utf-8-sig"), "text/csv; charset=utf-8", "csv"
    elif format == "xlsx":
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill
        output = io.BytesIO(); workbook = Workbook(); workbook.remove(workbook.active)
        student_columns = ["Student Name", "Roll Number", "Registration Number", "Academic Year", "Branch", "Section", "Parent/Guardian Name", "Parent Contact", "Student Contact"]
        attendance_columns = ["Roll Number", "Student Name", "Academic Year", "Branch", "Section", "Attendance Date", "Attendance Session", "Subject", "Faculty", "Absence Status", "CR/LR Submitter"]
        comment_columns = ["Roll Number", "Student Name", "Attendance Date", "Attendance Session", "Mentor Comment", "Mentor Name", "Comment Created At"]
        call_columns = ["Roll Number", "Student Name", "Attendance Date", "Contacted Person", "Call Phone", "Call Staff", "Call Staff Role", "Call Initiation Status", "Call Initiated At", "Call Outcome", "Call Notes", "Call Outcome Updated By", "Call Updated At"]
        datasets = {
            "Student Details": (student_columns, list({tuple(_cell(r.get(c)) for c in student_columns): r for r in table_rows}.values())),
            "Absentee Records": (attendance_columns, table_rows),
            "Mentor Comments": (comment_columns, [r for r in table_rows if r.get("Mentor Comment")]),
            "Parent Student Calls": (call_columns, [r for r in table_rows if r.get("Call Initiated At")]),
        }
        for title, (sheet_columns, dataset) in datasets.items():
            sheet = workbook.create_sheet(title); sheet.append(sheet_columns)
            for cell in sheet[1]: cell.font = Font(bold=True, color="FFFFFF"); cell.fill = PatternFill("solid", fgColor="24476B")
            for row in dataset: sheet.append([_cell(row.get(column)) for column in sheet_columns])
            sheet.freeze_panes = "A2"
            if dataset: sheet.auto_filter.ref = sheet.dimensions
            for cells in sheet.columns:
                letter = cells[0].column_letter
                sheet.column_dimensions[letter].width = min(48, max(14, max((len(str(c.value or "")) for c in cells[:100]), default=10) + 2))
        workbook.save(output); body, media, suffix = output.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "xlsx"
    else:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import landscape, A3
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_LEFT
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        output = io.BytesIO(); doc = SimpleDocTemplate(output, pagesize=landscape(A3), title="Absentee History Report", leftMargin=22, rightMargin=22, topMargin=24, bottomMargin=28)
        styles = getSampleStyleSheet(); small = ParagraphStyle("Small", parent=styles["BodyText"], fontName="Helvetica", fontSize=6.5, leading=8, alignment=TA_LEFT, wordWrap="CJK")
        matrix = [[Paragraph(str(column), small) for column in columns]]
        matrix.extend([[Paragraph(_cell(row.get(column)).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br/>"), small) for column in columns] for row in table_rows])
        story = [Paragraph("College Session Monitoring System — Absentee History", styles["Title"]), Paragraph(f"Year: {year or 'All'} | Branch: {branch or 'All'} | Section: {section or 'All'} | Attendance date range: {start or 'All'} to {end or 'All'} | Generated: {datetime.now(local_tz).strftime('%Y-%m-%d %H:%M %Z')}", styles["Normal"]), Spacer(1, 10)]
        widths = [max(36, 780 / max(1, len(columns)))] * len(columns)
        table = Table(matrix, colWidths=widths, repeatRows=1, splitByRow=1)
        table.setStyle(TableStyle([("BACKGROUND", (0,0), (-1,0), colors.HexColor("#24476b")), ("TEXTCOLOR", (0,0), (-1,0), colors.white), ("GRID", (0,0), (-1,-1), .25, colors.grey), ("VALIGN", (0,0), (-1,-1), "TOP"), ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#f1f5f9")]), ("LEFTPADDING", (0,0), (-1,-1), 3), ("RIGHTPADDING", (0,0), (-1,-1), 3)]))
        story.append(table)
        def footer(canvas, _doc): canvas.saveState(); canvas.setFont("Helvetica", 8); canvas.drawRightString(landscape(A3)[0]-24, 14, f"Page {_doc.page}"); canvas.restoreState()
        doc.build(story, onFirstPage=footer, onLaterPages=footer); body, media, suffix = output.getvalue(), "application/pdf", "pdf"
    return Response(body, media_type=media, headers={"Content-Disposition": f'attachment; filename="{stem}.{suffix}"', "Cache-Control": "no-store"})


class CallInitiate(BaseModel):
    attendance_id: str = Field(alias="attendanceId")
    phone_number: str = Field(alias="phoneNumber", min_length=3, max_length=32)
    contact_type: Literal["PARENT", "STUDENT"] = Field(alias="contactType")
    client_call_id: str = Field(alias="clientCallId", min_length=8, max_length=80)
    model_config = {"populate_by_name": True}


class CallOutcome(BaseModel):
    outcome: Literal["CONNECTED", "NOT_ANSWERED", "BUSY", "SWITCHED_OFF", "WRONG_NUMBER", "CALL_BACK_LATER", "OTHER"]
    follow_up_notes: Optional[str] = Field(None, alias="followUpNotes", max_length=2000)
    model_config = {"populate_by_name": True}


async def _authorized_attendance(db, record_id: str, user: dict):
    record = None
    for collection in (db.student_attendance, db.student_attendance_sessions):
        query = {"_id": ObjectId(record_id)} if ObjectId.is_valid(record_id) else {"_id": record_id}
        record = await collection.find_one(query)
        if record: break
    if not record: raise HTTPException(404, "Absence record was not found.")
    if user.get("role") == UserRole.MENTOR.value:
        assigned = await get_mentor_assigned_student_ids(user)
        if assigned is None:
            raise HTTPException(403, "Mentor student assignments are not configured; access is denied.")
        assigned_rolls = []
        oids = [ObjectId(item) for item in assigned if ObjectId.is_valid(item)]
        if oids:
            for student in await db.students.find({"_id": {"$in": oids}}, {"roll_number": 1}).to_list(length=10000):
                if student.get("roll_number"): assigned_rolls.append(str(student["roll_number"]).upper())
        if str(record.get("student_id")) not in assigned and str(record.get("roll_number", "")).upper() not in assigned_rolls:
            raise HTTPException(403, "This student is outside your mentor assignments.")
    return record


@router.post("/history/calls/initiate")
async def initiate_absentee_call(payload: CallInitiate, user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.MENTOR]))):
    db = get_database(); record = await _authorized_attendance(db, payload.attendance_id, user)
    expected_phone = record.get("parent_phone") if payload.contact_type == "PARENT" else record.get("student_phone")
    if not expected_phone or re.sub(r"\D", "", str(expected_phone)) != re.sub(r"\D", "", payload.phone_number):
        raise HTTPException(422, "Phone number does not match the selected student contact.")
    stamp = datetime.now(timezone.utc)
    doc = {"_id": payload.client_call_id, "attendance_record_id": str(record["_id"]), "student_id": str(record.get("student_id") or ""), "student_name": record.get("student_name"), "roll_number": record.get("roll_number"), "year": record.get("year"), "section": record.get("section"), "attendance_date": record.get("date"), "phone_number": payload.phone_number, "contact_type": payload.contact_type, "staff_id": str(user.get("_id")), "staff_name": user.get("name"), "staff_role": user.get("role"), "initiated_at": stamp, "initiated_date": stamp.astimezone(local_tz).date().isoformat(), "initiation_status": "INITIATED", "outcome": None, "created_at": stamp}
    await db.absentee_call_history.update_one({"_id": payload.client_call_id}, {"$setOnInsert": doc}, upsert=True)
    saved = await db.absentee_call_history.find_one({"_id": payload.client_call_id})
    saved["id"] = str(saved.pop("_id"))
    return {"success": True, "data": saved}


@router.patch("/history/calls/{call_id}/outcome")
async def update_absentee_call_outcome(call_id: str, payload: CallOutcome, user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.MENTOR]))):
    db = get_database(); call = await db.absentee_call_history.find_one({"_id": call_id})
    if not call: raise HTTPException(404, "Call history record was not found.")
    await _authorized_attendance(db, call["attendance_record_id"], user)
    stamp = datetime.now(timezone.utc)
    await db.absentee_call_history.update_one({"_id": call_id}, {"$set": {"outcome": payload.outcome, "follow_up_notes": payload.follow_up_notes, "outcome_updated_by_id": str(user.get("_id")), "outcome_updated_by": user.get("name"), "outcome_updated_at": stamp}})
    return {"success": True, "data": {"id": call_id, "outcome": payload.outcome, "followUpNotes": payload.follow_up_notes, "updatedAt": stamp}}


@router.get("/history/calls")
async def get_absentee_call_history(attendance_id: str = Query(..., alias="attendanceId"), user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.MENTOR]))):
    db = get_database(); await _authorized_attendance(db, attendance_id, user)
    rows = await db.absentee_call_history.find({"attendance_record_id": attendance_id}).sort("initiated_at", -1).to_list(length=500)
    for row in rows: row["id"] = str(row.pop("_id"))
    return {"success": True, "data": rows}
