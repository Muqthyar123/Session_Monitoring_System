import pytest
from datetime import datetime, timezone
import zoneinfo
from app.core.config import settings
from app.db.mongodb import get_database
from app.schemas.session import FacultyResponseStatus, SessionStatus
from app.schemas.user import UserRole
from app.scheduler.jobs import process_scheduled_sessions_job

tz_kolkata = zoneinfo.ZoneInfo(settings.TIMEZONE)


@pytest.mark.asyncio
async def test_process_scheduled_sessions_job_escalation():
    db = get_database()
    now_local = datetime.now(tz_kolkata)
    date_str = now_local.strftime("%Y-%m-%d")

    # Insert section
    await db.sections.insert_one({"section_name": "II-A", "is_active": True})

    # Insert session starting 15 minutes ago (09:00 if current time is 09:15)
    past_start_time = "00:01"  # Midnight start time is guaranteed to be > 10 mins ago during testing

    session_res = await db.sessions.insert_one({
        "section": "II-A",
        "subject": "Algorithms",
        "period": "Period 1",
        "periods_included": [1],
        "start_time": past_start_time,
        "end_time": "23:59",
        "date": date_str,
        "session_status": SessionStatus.ACTIVE.value,
        "faculty_response": FacultyResponseStatus.PENDING.value,
        "start_notification_sent": True,
        "escalation_alert_generated": False,
        "created_at": datetime.now(timezone.utc),
    })
    session_id = str(session_res.inserted_id)

    # Run scheduled job
    await process_scheduled_sessions_job()

    # Verify escalation alert created
    alert = await db.admin_alerts.find_one({"session_id": session_id})
    assert alert is not None
    assert alert["reason"] == "No response within 10 minutes"

    # Verify session marked escalation_alert_generated = True
    session_doc = await db.sessions.find_one({"_id": session_res.inserted_id})
    assert session_doc["escalation_alert_generated"] is True

    # Run job again to verify IDEMPOTENCY (no duplicate alerts)
    await process_scheduled_sessions_job()
    alert_count = await db.admin_alerts.count_documents({"session_id": session_id})
    assert alert_count == 1, "Duplicate alert created during job rerun!"
