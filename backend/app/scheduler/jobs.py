import logging
from datetime import datetime, timezone
import zoneinfo
from app.core.config import settings
from app.db.mongodb import get_database
from app.schemas.session import FacultyResponseStatus, SessionStatus
from app.services.notification_service import (
    notify_10min_no_response,
    notify_session_start,
)
from app.services.session_service import generate_and_sync_sessions_for_date

logger = logging.getLogger("fams.scheduler")
tz_kolkata = zoneinfo.ZoneInfo(settings.TIMEZONE)


async def process_scheduled_sessions_job():
    """Idempotent job executed periodically by APScheduler to process session starts and 10-min escalations."""
    try:
        db = get_database()
        now_local = datetime.now(tz_kolkata)
        now_utc = datetime.now(timezone.utc)
        date_str = now_local.strftime("%Y-%m-%d")

        # 1. Sync session records from timetable for today
        await generate_and_sync_sessions_for_date(now_local)

        # 2. Fetch today's sessions from MongoDB
        cursor = db.sessions.find({"date": date_str})
        todays_sessions = await cursor.to_list(length=1000)

        for session in todays_sessions:
            s_id = session["_id"]
            start_time_str = session["start_time"]

            # Parse start time in Kolkata timezone
            start_dt = datetime.strptime(f"{date_str} {start_time_str}", "%Y-%m-%d %H:%M").replace(tzinfo=tz_kolkata)
            now_ts = now_local.timestamp()
            start_ts = start_dt.timestamp()
            escalation_ts = start_ts + 600  # 10 minutes (600 seconds)

            # Check 1: Trigger Session Start Notification
            if now_ts >= start_ts and not session.get("start_notification_sent", False):
                # Atomic update to avoid race conditions
                result = await db.sessions.update_one(
                    {
                        "_id": s_id,
                        "start_notification_sent": False,
                    },
                    {
                        "$set": {
                            "start_notification_sent": True,
                            "session_status": SessionStatus.ACTIVE.value,
                            "updated_at": now_utc,
                        }
                    },
                )
                if result.modified_count > 0:
                    logger.info("Triggered start notification for session %s (%s)", s_id, session["subject"])
                    session["_id"] = str(session["_id"])
                    await notify_session_start(session)

            # Check 2: Trigger 10-Minute Escalation Alert if no response received
            if (
                now_ts >= escalation_ts
                and session.get("faculty_response") == FacultyResponseStatus.PENDING.value
                and not session.get("escalation_alert_generated", False)
            ):
                result = await db.sessions.update_one(
                    {
                        "_id": s_id,
                        "escalation_alert_generated": False,
                        "faculty_response": FacultyResponseStatus.PENDING.value,
                    },
                    {
                        "$set": {
                            "escalation_alert_generated": True,
                            "session_status": SessionStatus.EXPIRED.value,
                            "updated_at": now_utc,
                        }
                    },
                )
                if result.modified_count > 0:
                    logger.info("Triggered 10-min escalation alert for session %s (%s)", s_id, session["subject"])
                    session["_id"] = str(session["_id"])
                    await notify_10min_no_response(session)

    except Exception as e:
        logger.error("Error running process_scheduled_sessions_job: %s", str(e), exc_info=True)
