import logging
from datetime import datetime, timezone
from typing import List, Optional
from bson import ObjectId
from app.db.mongodb import get_database
from app.schemas.notification import NotificationResponse, NotificationType
from app.schemas.user import UserRole
from app.services.push_service import send_push_notification_to_users

logger = logging.getLogger("fams.notification")


async def create_in_app_notification(
    recipient_user_id: str,
    notification_type: NotificationType,
    title: str,
    message: str,
    section: Optional[str] = None,
    subject: Optional[str] = None,
    time_str: Optional[str] = None,
    session_id: Optional[str] = None,
) -> dict:
    db = get_database()
    now = datetime.now(timezone.utc)
    doc = {
        "recipient_user_id": recipient_user_id,
        "type": notification_type.value,
        "title": title,
        "message": message,
        "section": section,
        "subject": subject,
        "time": time_str,
        "session_id": session_id,
        "is_read": False,
        "created_at": now,
    }
    res = await db.notifications.insert_one(doc)
    doc["_id"] = str(res.inserted_id)
    return doc


async def get_user_notifications(user_id: str, limit: int = 50) -> List[NotificationResponse]:
    db = get_database()
    cursor = db.notifications.find({"recipient_user_id": user_id}).sort("created_at", -1).limit(limit)
    results = []
    async for n in cursor:
        n["_id"] = str(n["_id"])
        results.append(NotificationResponse(**n))
    return results


async def get_unread_count(user_id: str) -> int:
    db = get_database()
    return await db.notifications.count_documents({"recipient_user_id": user_id, "is_read": False})


async def mark_notification_read(notification_id: str, user_id: str):
    if not ObjectId.is_valid(notification_id):
        return
    db = get_database()
    await db.notifications.update_one(
        {"_id": ObjectId(notification_id), "recipient_user_id": user_id},
        {"$set": {"is_read": True}},
    )


async def mark_all_notifications_read(user_id: str):
    db = get_database()
    await db.notifications.update_many(
        {"recipient_user_id": user_id, "is_read": False},
        {"$set": {"is_read": True}},
    )


async def notify_session_start(session_doc: dict):
    """Sends start notification to CR and LR of the section."""
    db = get_database()
    sec_name = session_doc["section"]
    subj = session_doc["subject"]
    time_str = f"{session_doc['start_time']} - {session_doc['end_time']}"
    s_id = str(session_doc["_id"])

    # Find CR and LR for section
    cr_lr_cursor = db.users.find(
        {
            "section": sec_name,
            "role": {"$in": [UserRole.CR.value, UserRole.LR.value]},
            "is_active": True,
        }
    )
    crlr_users = await cr_lr_cursor.to_list(length=10)
    user_ids = [str(u["_id"]) for u in crlr_users]

    title = "Faculty Attendance Required"
    msg = f"Class session for '{subj}' ({time_str}) has started. Please submit faculty attendance."

    for u_id in user_ids:
        await create_in_app_notification(
            recipient_user_id=u_id,
            notification_type=NotificationType.FACULTY_ATTENDANCE_REQUIRED,
            title=title,
            message=msg,
            section=sec_name,
            subject=subj,
            time_str=time_str,
            session_id=s_id,
        )

    # Send push notification
    await send_push_notification_to_users(
        user_ids=user_ids,
        title=title,
        body=msg,
        data={"session_id": s_id, "section": sec_name},
    )


async def notify_immediate_faculty_absent(
    session_doc: dict,
    reporter_name: str,
    reporter_role: str,
    status: str = "ABSENT",
    substitute_name: Optional[str] = None,
):
    """Creates immediate admin alert when faculty is reported absent or substitute."""
    db = get_database()
    sec_name = session_doc.get("section", "")
    subj = session_doc.get("subject", "")
    assigned_fac = session_doc.get("faculty") or "Assigned Faculty"
    time_str = f"{session_doc.get('start_time', '')} - {session_doc.get('end_time', '')}"
    period_str = session_doc.get("period", "Class Session")

    now = datetime.now(timezone.utc)

    if status == "SUBSTITUTE":
        sub_title = f"Alert: Substitute Faculty ({sec_name})"
        sub_name_str = substitute_name or "Substitute"
        msg = f"Substitute faculty '{sub_name_str}' assigned in place of '{assigned_fac}' for {subj} ({period_str}, {sec_name}, {time_str}) reported by {reporter_role} {reporter_name}."
        reason_str = f"Faculty not available — Substitute: {sub_name_str} (Replaced {assigned_fac})"
    else:
        sub_title = f"Alert: Faculty Absent ({sec_name})"
        msg = f"Faculty '{assigned_fac}' reported ABSENT for {subj} ({period_str}, {sec_name}, {time_str}) by {reporter_role} {reporter_name}."
        reason_str = f"Faculty not available ({assigned_fac})"

    # Insert Admin Alert record
    alert_doc = {
        "section": sec_name,
        "subject": subj,
        "session": time_str,
        "session_id": str(session_doc["_id"]),
        "time": now.strftime("%H:%M"),
        "reported_by": reporter_role,
        "reason": reason_str,
        "status": "New",
        "created_at": now,
    }
    await db.admin_alerts.insert_one(alert_doc)

    # Notify all admin users
    admins = await db.users.find({"role": UserRole.ADMIN.value, "is_active": True}).to_list(length=100)
    admin_ids = [str(a["_id"]) for a in admins]

    for a_id in admin_ids:
        await create_in_app_notification(
            recipient_user_id=a_id,
            notification_type=NotificationType.FACULTY_ABSENT_ALERT,
            title=sub_title,
            message=msg,
            section=sec_name,
            subject=subj,
            time_str=time_str,
            session_id=str(session_doc["_id"]),
        )

    await send_push_notification_to_users(
        user_ids=admin_ids,
        title=sub_title,
        body=msg,
        data={"session_id": str(session_doc["_id"]), "type": status},
    )


async def notify_10min_no_response(session_doc: dict):
    """Creates admin alert when no response received after 10 minutes from start."""
    db = get_database()
    sec_name = session_doc["section"]
    subj = session_doc["subject"]
    time_str = f"{session_doc['start_time']} - {session_doc['end_time']}"

    now = datetime.now(timezone.utc)
    alert_doc = {
        "section": sec_name,
        "subject": subj,
        "session": time_str,
        "session_id": str(session_doc["_id"]),
        "time": now.strftime("%H:%M"),
        "reported_by": session_doc.get("crlr_role", "CR"),
        "reason": "No response within 10 minutes",
        "status": "New",
        "created_at": now,
    }
    await db.admin_alerts.insert_one(alert_doc)

    admins = await db.users.find({"role": UserRole.ADMIN.value, "is_active": True}).to_list(length=100)
    admin_ids = [str(a["_id"]) for a in admins]

    title = f"Alert: No Response ({sec_name})"
    msg = f"No attendance response submitted within 10 minutes for {subj} ({sec_name}, {time_str})."

    for a_id in admin_ids:
        await create_in_app_notification(
            recipient_user_id=a_id,
            notification_type=NotificationType.NO_RESPONSE_ALERT,
            title=title,
            message=msg,
            section=sec_name,
            subject=subj,
            time_str=time_str,
            session_id=str(session_doc["_id"]),
        )

    await send_push_notification_to_users(
        user_ids=admin_ids,
        title=title,
        body=msg,
        data={"session_id": str(session_doc["_id"]), "type": "NO_RESPONSE_ALERT"},
    )
