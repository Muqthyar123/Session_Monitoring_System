from datetime import datetime, timezone
import zoneinfo
from bson import ObjectId
from fastapi import HTTPException, status
from app.core.config import settings
from app.db.mongodb import get_database
from app.schemas.attendance import AttendanceStatus, AttendanceSubmitRequest
from app.schemas.session import ClassSessionResponse, FacultyResponseStatus
from app.services.notification_service import notify_immediate_faculty_absent
from app.services.session_service import calculate_session_dynamic_state

tz_kolkata = zoneinfo.ZoneInfo(settings.TIMEZONE)


async def submit_attendance(
    data: AttendanceSubmitRequest, current_user: dict
) -> ClassSessionResponse:
    if not ObjectId.is_valid(data.session_id):
        raise HTTPException(status_code=400, detail="Invalid Session ID.")

    db = get_database()
    session = await db.sessions.find_one({"_id": ObjectId(data.session_id)})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    user_role = current_user.get("role")
    user_sec = current_user.get("section")
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
