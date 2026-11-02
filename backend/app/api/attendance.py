from typing import List, Optional
from datetime import datetime, time, timedelta, timezone
import csv, io
from zoneinfo import ZoneInfo
from fastapi import APIRouter, Depends, Query, status, HTTPException
from fastapi.responses import StreamingResponse
from app.core.dependencies import get_current_user, require_roles
from app.schemas.attendance import (
    AdminAlertResponse,
    AttendanceRecordResponse,
    AttendanceSubmitRequest,
)
from app.schemas.common import ApiResponse
from app.schemas.session import ClassSessionResponse
from app.schemas.user import UserRole
from app.services.attendance_service import submit_attendance
from app.db.mongodb import get_database

router = APIRouter(prefix="/attendance", tags=["Attendance Management"])
tz = ZoneInfo("Asia/Kolkata")

def _alert_date_query(query: dict, from_date: Optional[str], to_date: Optional[str]):
    try:
        lower = datetime.combine(datetime.strptime(from_date, "%Y-%m-%d").date(), time.min, tzinfo=tz).astimezone(timezone.utc) if from_date else None
        upper = datetime.combine(datetime.strptime(to_date, "%Y-%m-%d").date() + timedelta(days=1), time.min, tzinfo=tz).astimezone(timezone.utc) if to_date else None
    except ValueError:
        raise HTTPException(422, "Dates must use YYYY-MM-DD format.") from None
    if from_date and to_date and from_date > to_date:
        raise HTTPException(422, "From date cannot be later than To date.")
    if lower or upper:
        query["created_at"] = {**({"$gte": lower} if lower else {}), **({"$lt": upper} if upper else {})}
    return query


@router.post("", response_model=ApiResponse[ClassSessionResponse])
async def submit_attendance_api(
    data: AttendanceSubmitRequest,
    current_user: dict = Depends(get_current_user),
):
    session_res = await submit_attendance(data, current_user)
    return ApiResponse(
        success=True, data=session_res, message="Faculty attendance recorded successfully."
    )


@router.get("/my", response_model=ApiResponse[List[AttendanceRecordResponse]])
async def get_my_attendance_records_api(
    current_user: dict = Depends(get_current_user),
):
    db = get_database()
    cursor = db.attendance_records.find({"user_id": current_user["id"]}).sort("created_at", -1)
    results = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        results.append(AttendanceRecordResponse(**doc))
    return ApiResponse(success=True, data=results)


@router.get("/alerts", response_model=dict)
async def get_admin_alerts_api(
    category: Optional[str] = Query(None, description="Filter: ALL, NO_RESPONSE_10MIN, FACULTY_ABSENT, FACULTY_STATUS_UPDATED"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter: ALL, New, Acknowledged"),
    from_date: Optional[str] = Query(None, alias="fromDate"),
    to_date: Optional[str] = Query(None, alias="toDate"),
    search: Optional[str] = Query(None, max_length=100),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    admin: dict = Depends(require_roles([UserRole.ADMIN, UserRole.DEPARTMENT_COORDINATOR, UserRole.COORDINATOR])),
):
    db = get_database()
    query = _alert_date_query({}, from_date, to_date)

    if status_filter and status_filter.upper() != "ALL":
        query["status"] = {"$regex": f"^{status_filter}$", "$options": "i"}
    if search and search.strip():
        token = {"$regex": search.strip(), "$options": "i"}
        query["$and"] = query.get("$and", []) + [{"$or": [{field: token} for field in ("reason", "section", "subject", "session", "reported_by", "title")] }]

    if category and category.upper() != "ALL":
        cat_upper = category.strip().upper()
        if cat_upper in ["NO_RESPONSE_10MIN", "TIMEOUT", "CR_LR_TIMEOUT", "NO_RESPONSE"]:
            query["$or"] = [
                {"reason": {"$regex": "10 min", "$options": "i"}},
                {"reason": {"$regex": "no response", "$options": "i"}},
                {"type": "NO_RESPONSE_ALERT"},
            ]
        elif cat_upper in ["FACULTY_ABSENT", "ABSENT", "NOT_PRESENT"]:
            query["$or"] = [
                {"reason": {"$regex": "not available", "$options": "i"}},
                {"reason": {"$regex": "absent", "$options": "i"}},
                {"reason": {"$regex": "substitute", "$options": "i"}},
                {"type": "FACULTY_ABSENT_ALERT"},
            ]
        elif cat_upper in ["FACULTY_STATUS_UPDATED", "UPDATED", "STATUS_UPDATED"]:
            query["$or"] = [
                {"reason": {"$regex": "updated", "$options": "i"}},
                {"reason": {"$regex": "status", "$options": "i"}},
                {"reason": {"$regex": "changed", "$options": "i"}},
            ]

    total = await db.admin_alerts.count_documents(query)
    cursor = db.admin_alerts.find(query, {"section": 1, "subject": 1, "session": 1, "time": 1, "reported_by": 1, "reason": 1, "status": 1, "created_at": 1, "type": 1, "year": 1, "branch": 1}).sort("created_at", -1).skip((page - 1) * limit).limit(limit)
    results = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        results.append(AdminAlertResponse(**doc))
    return {"success": True, "data": {"items": results, "total": total, "page": page, "limit": limit}}


@router.get("/alerts/export")
async def export_admin_alerts_api(
    format: str = Query(..., pattern="^(csv|xlsx|pdf)$"),
    from_date: Optional[str] = Query(None, alias="fromDate"),
    to_date: Optional[str] = Query(None, alias="toDate"),
    category: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    search: Optional[str] = Query(None, max_length=100),
    admin: dict = Depends(require_roles([UserRole.ADMIN])),
):
    db = get_database()
    query = _alert_date_query({}, from_date, to_date)
    if status_filter and status_filter.upper() != "ALL":
        query["status"] = {"$regex": f"^{status_filter}$", "$options": "i"}
    if search and search.strip():
        token = {"$regex": search.strip(), "$options": "i"}
        query["$and"] = [{"$or": [{field: token} for field in ("reason", "section", "subject", "session", "reported_by", "title")]}]
    if category and category.upper() != "ALL":
        cat_upper = category.strip().upper()
        terms = {
            "NO_RESPONSE_10MIN": ["10 min", "no response"],
            "FACULTY_ABSENT": ["not available", "absent", "substitute"],
            "FACULTY_STATUS_UPDATED": ["updated", "status", "changed"],
        }.get(cat_upper)
        if terms:
            query["$or"] = [{"reason": {"$regex": term, "$options": "i"}} for term in terms]
    cursor = db.admin_alerts.find(query).sort("created_at", -1)
    docs = await cursor.to_list(length=None)
    columns = ["Notification ID", "Title", "Message", "Type", "Section", "Subject", "Session", "Reported By", "Status", "Created At"]
    rows = [[str(d.get("_id", "")), d.get("title", "Attendance alert"), d.get("reason", ""), d.get("type", ""), d.get("section", ""), d.get("subject", ""), d.get("session", ""), d.get("reported_by", ""), d.get("status", "New"), d.get("created_at", "")] for d in docs]
    if format == "csv":
        output = io.StringIO(newline="")
        writer = csv.writer(output); writer.writerow(columns); writer.writerows(rows)
        payload, mime, ext = output.getvalue().encode("utf-8-sig"), "text/csv; charset=utf-8", "csv"
    elif format == "xlsx":
        import openpyxl
        book = openpyxl.Workbook(); sheet = book.active; sheet.title = "Notifications"
        sheet.append(columns)
        for row in rows: sheet.append(row)
        sheet.freeze_panes = "A2"; sheet.auto_filter.ref = sheet.dimensions
        for col in sheet.columns:
            sheet.column_dimensions[col[0].column_letter].width = min(48, max(14, max(len(str(c.value or "")) for c in col) + 2))
        buf = io.BytesIO(); book.save(buf); payload, mime, ext = buf.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "xlsx"
    else:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import landscape, letter
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet
        buf = io.BytesIO(); doc = SimpleDocTemplate(buf, pagesize=landscape(letter))
        table_rows = [[Paragraph(str(v).replace("&", "&amp;").replace("<", "&lt;"), getSampleStyleSheet()["BodyText"]) for v in row] for row in [columns] + [[str(v) for v in r] for r in rows]]
        table = Table(table_rows, repeatRows=1); table.setStyle(TableStyle([("BACKGROUND", (0,0),(-1,0),colors.HexColor("#1f4e79")),("TEXTCOLOR",(0,0),(-1,0),colors.white),("GRID",(0,0),(-1,-1),.25,colors.grey),("VALIGN",(0,0),(-1,-1),"TOP")]))
        doc.build([Paragraph("Notification History", getSampleStyleSheet()["Title"]), Paragraph(f"Generated {datetime.now(tz).strftime('%Y-%m-%d %H:%M %Z')} · {len(rows)} records", getSampleStyleSheet()["Normal"]), Spacer(1, 12), table])
        payload, mime, ext = buf.getvalue(), "application/pdf", "pdf"
    return StreamingResponse(io.BytesIO(payload), media_type=mime, headers={"Content-Disposition": f'attachment; filename="notification_history.{ext}"'})


@router.patch("/alerts/{alert_id}/acknowledge", response_model=ApiResponse[dict])
async def acknowledge_alert_api(
    alert_id: str,
    admin: dict = Depends(require_roles([UserRole.ADMIN, UserRole.DEPARTMENT_COORDINATOR, UserRole.COORDINATOR])),
):
    from bson import ObjectId
    if not ObjectId.is_valid(alert_id):
        return ApiResponse(success=False, message="Invalid Alert ID.")
    db = get_database()
    await db.admin_alerts.update_one({"_id": ObjectId(alert_id)}, {"$set": {"status": "Acknowledged"}})
    return ApiResponse(success=True, message="Alert acknowledged successfully.")

