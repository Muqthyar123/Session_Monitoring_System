from datetime import datetime, timezone
import zoneinfo
from bson import ObjectId
from fastapi import HTTPException, status
from app.core.config import settings
from app.db.mongodb import get_database
from app.schemas.attendance import AttendanceStatus, AttendanceSubmitRequest
from app.schemas.session import ClassSessionResponse, FacultyResponseStatus
from app.services.notification_service import notify_immediate_faculty_absent
from app.services.session_service import (
    calculate_session_dynamic_state,
    generate_and_sync_sessions_for_date,
)

tz_kolkata = zoneinfo.ZoneInfo(settings.TIMEZONE)


async def submit_attendance(
    data: AttendanceSubmitRequest, current_user: dict
) -> ClassSessionResponse:
    db = get_database()
    now_local = datetime.now(tz_kolkata)
    now_utc = datetime.now(timezone.utc)
    user_sec = (current_user.get("section") or "II-CSE-B").strip().upper()

    session = None
    if ObjectId.is_valid(data.session_id):
        session = await db.sessions.find_one({"_id": ObjectId(data.session_id)})

    if not session:
        # Ensure sessions for today are synced in database
        await generate_and_sync_sessions_for_date(now_local)

        if ObjectId.is_valid(data.session_id):
            session = await db.sessions.find_one({"_id": ObjectId(data.session_id)})

        if not session:
            date_str = now_local.strftime("%Y-%m-%d")
            session = await db.sessions.find_one({"section": user_sec, "date": date_str})

        if not session:
            date_str = now_local.strftime("%Y-%m-%d")
            new_doc = {
                "section": user_sec,
                "year": current_user.get("year", "2nd Year"),
                "subject": "DMGT",
                "faculty": "Ch.Revathi",
                "period": "Period 1",
                "periods_included": [1],
                "start_time": "09:10",
                "end_time": "10:00",
                "date": date_str,
                "crlr_name": current_user.get("name", "Student Rep"),
                "crlr_role": current_user.get("role", "CR"),
                "session_status": "Active",
                "faculty_response": "Pending",
                "response_time": None,
                "substitute_name": None,
                "start_notification_sent": True,
                "escalation_alert_generated": False,
                "created_at": now_utc,
                "updated_at": now_utc,
            }
            res = await db.sessions.insert_one(new_doc)
            session = await db.sessions.find_one({"_id": res.inserted_id})

    user_role = current_user.get("role")
    user_id = str(current_user["_id"])
    user_name = current_user.get("name", "Student Rep")

    # Access control: CR/LR can only submit attendance for their assigned section
    if user_role in ["CR", "LR"] and session["section"] != user_sec:
        raise HTTPException(
            status_code=403,
            detail="Access forbidden: You can only submit attendance for your assigned section.",
        )

    # Validation: substitute_name rules
    if data.status == AttendanceStatus.PRESENT and data.substitute_name:
        raise HTTPException(
            status_code=400,
            detail="Substitute name cannot be provided when faculty status is PRESENT.",
        )

    if data.status == AttendanceStatus.SUBSTITUTE and not (data.substitute_name and data.substitute_name.strip()):
        raise HTTPException(
            status_code=400,
            detail="Substitute faculty name is required when status is SUBSTITUTE.",
        )

    now_local = datetime.now(tz_kolkata)
    now_utc = datetime.now(timezone.utc)
    response_time_str = now_local.strftime("%H:%M")

    # Record audit entry in attendance_records collection
    rec_doc = {
        "session_id": str(session["_id"]),
        "user_id": user_id,
        "user_name": user_name,
        "user_role": user_role,
        "section": session["section"],
        "status": data.status.value,
        "substitute_name": data.substitute_name.strip() if data.substitute_name else None,
        "created_at": now_utc,
    }
    await db.attendance_records.insert_one(rec_doc)

    # Determine faculty response string for session
    if data.status == AttendanceStatus.PRESENT:
        fac_resp = FacultyResponseStatus.PRESENT.value
    elif data.status == AttendanceStatus.ABSENT:
        fac_resp = FacultyResponseStatus.ABSENT.value
    else:
        fac_resp = FacultyResponseStatus.SUBSTITUTE.value

    sub_name = data.substitute_name.strip() if data.substitute_name else None

    # Update session document
    update_data = {
        "faculty_response": fac_resp,
        "substitute_name": sub_name,
        "response_time": response_time_str,
        "updated_at": now_utc,
    }
    await db.sessions.update_one({"_id": session["_id"]}, {"$set": update_data})

    # Trigger immediate admin alert if absent or substitute
    if data.status in [AttendanceStatus.ABSENT, AttendanceStatus.SUBSTITUTE]:
        await notify_immediate_faculty_absent(
            session_doc=session, reporter_name=user_name, reporter_role=user_role
        )

    # Log audit entry
    await db.audit_logs.insert_one(
        {
            "actor_id": user_id,
            "action": "SUBMIT_ATTENDANCE",
            "session_id": str(session["_id"]),
            "metadata": {"status": data.status.value, "substitute": sub_name},
            "created_at": now_utc,
        }
    )

    updated_doc = await db.sessions.find_one({"_id": session["_id"]})
    updated_doc["_id"] = str(updated_doc["_id"])
    computed = calculate_session_dynamic_state(updated_doc, now_local)
    return ClassSessionResponse(**computed)
