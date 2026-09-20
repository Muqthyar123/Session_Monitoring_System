import unittest
import unittest.mock
import pytest
from datetime import datetime, timedelta, timezone
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

    # Insert session starting at 09:00
    start_time_str = "09:00"

    session_res = await db.sessions.insert_one({
        "section": "II-A",
        "subject": "Algorithms",
        "period": "Period 1",
        "periods_included": [1],
        "start_time": start_time_str,
        "end_time": "10:00",
        "date": date_str,
        "session_status": SessionStatus.ACTIVE.value,
        "faculty_response": FacultyResponseStatus.PENDING.value,
        "start_notification_sent": True,
        "escalation_alert_generated": False,
        "created_at": datetime.now(timezone.utc),
    })
    session_id = str(session_res.inserted_id)

    # Run scheduled job with mock time set to 09:15 (15 mins after start_time)
    mock_now = datetime.strptime(f"{date_str} 09:15", "%Y-%m-%d %H:%M").replace(tzinfo=tz_kolkata)
    with unittest.mock.patch("app.scheduler.jobs.datetime") as mock_datetime:
        mock_datetime.now.side_effect = lambda tz=None: mock_now if tz else mock_now.astimezone(timezone.utc)
        mock_datetime.strptime = datetime.strptime
        await process_scheduled_sessions_job()

    # Verify escalation alert created
    alert = await db.admin_alerts.find_one({"session_id": session_id})
    assert alert is not None
    assert alert["reason"] == "No response within 10 minutes"

    # Verify session marked escalation_alert_generated = True
    session_doc = await db.sessions.find_one({"_id": session_res.inserted_id})
    assert session_doc["escalation_alert_generated"] is True

    # Run job again to verify IDEMPOTENCY (no duplicate alerts)
    with unittest.mock.patch("app.scheduler.jobs.datetime") as mock_datetime:
        mock_datetime.now.side_effect = lambda tz=None: mock_now if tz else mock_now.astimezone(timezone.utc)
        mock_datetime.strptime = datetime.strptime
        await process_scheduled_sessions_job()
    alert_count = await db.admin_alerts.count_documents({"session_id": session_id})
    assert alert_count == 1, "Duplicate alert created during job rerun!"
