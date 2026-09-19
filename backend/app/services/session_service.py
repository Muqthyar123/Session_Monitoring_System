import logging
from datetime import datetime, timezone
from typing import List, Optional
import zoneinfo
from bson import ObjectId
from app.core.config import settings
from app.db.mongodb import get_database
from app.schemas.session import ClassSessionResponse, FacultyResponseStatus, SessionStatus

logger = logging.getLogger("fams.session")

tz_kolkata = zoneinfo.ZoneInfo(settings.TIMEZONE)


def combine_continuous_periods(periods: List[dict]) -> List[dict]:
    """Combines consecutive periods with identical subject and faculty into continuous sessions."""
    if not periods:
        return []

    # Sort periods by period number / start time
    sorted_periods = sorted(periods, key=lambda p: (p.get("period", 0), p.get("start_time", "")))

    combined = []
    current_session = None

    for p in sorted_periods:
        subj = p.get("subject", "").strip()
        fac = (p.get("faculty") or "").strip()
        s_time = p.get("start_time", "").strip()
        e_time = p.get("end_time", "").strip()
        p_num = p.get("period", 1)

        if current_session is None:
            current_session = {
                "year": p.get("year", ""),
                "section": p.get("section", ""),
                "day": p.get("day", ""),
                "subject": subj,
                "faculty": fac,
                "room": p.get("room"),
                "start_time": s_time,
                "end_time": e_time,
                "periods_included": [p_num],
            }
        else:
            # Check if continuous: matching subject & faculty, and start_time equals previous end_time
            same_subj = current_session["subject"].lower() == subj.lower()
            same_fac = current_session["faculty"].lower() == fac.lower()
            is_adjacent = current_session["end_time"] == s_time

            if same_subj and same_fac and is_adjacent:
                # Merge into continuous session
                current_session["end_time"] = e_time
                current_session["periods_included"].append(p_num)
            else:
                combined.append(current_session)
                current_session = {
                    "year": p.get("year", ""),
                    "section": p.get("section", ""),
                    "day": p.get("day", ""),
                    "subject": subj,
                    "faculty": fac,
                    "room": p.get("room"),
                    "start_time": s_time,
                    "end_time": e_time,
                    "periods_included": [p_num],
                }

    if current_session:
        combined.append(current_session)

    # Format period representation (e.g. "Period 1" or "Period 1 - Period 3")
    for s in combined:
        p_list = s["periods_included"]
        if len(p_list) == 1:
            s["period_display"] = f"Period {p_list[0]}"
        else:
            s["period_display"] = f"Period {min(p_list)} - Period {max(p_list)}"

    return combined


async def generate_and_sync_sessions_for_date(target_date: Optional[datetime] = None) -> List[dict]:
    """Reads timetable for current day of week and creates/updates sessions in MongoDB idempotently."""
    db = get_database()
    now_local = (target_date or datetime.now(tz_kolkata))
    date_str = now_local.strftime("%Y-%m-%d")
    day_name = now_local.strftime("%A")  # Monday..Sunday

    sections_cursor = db.sections.find({"is_active": True})
    active_sections = await sections_cursor.to_list(length=1000)
    existing_sec_names = {s["section_name"] for s in active_sections if "section_name" in s}

    # Also collect distinct sections from db.timetables if not already in active_sections
    distinct_tt_sections = await db.timetables.distinct("section")
    for tt_sec in distinct_tt_sections:
        if tt_sec and tt_sec not in existing_sec_names:
            sample = await db.timetables.find_one({"section": tt_sec})
            yr = sample.get("year", "2nd Year") if sample else "2nd Year"
            active_sections.append({"section_name": tt_sec, "year": yr, "is_active": True})
            existing_sec_names.add(tt_sec)

    generated_sessions = []

    for sec in active_sections:
        sec_name = sec["section_name"]
        cr_id = sec.get("assigned_cr_id")
        lr_id = sec.get("assigned_lr_id")

        # Resolve CR / LR details
        cr_user = await db.users.find_one({"_id": ObjectId(cr_id)}) if cr_id and ObjectId.is_valid(cr_id) else None
        lr_user = await db.users.find_one({"_id": ObjectId(lr_id)}) if lr_id and ObjectId.is_valid(lr_id) else None

        crlr_name = cr_user.get("name") if cr_user else (lr_user.get("name") if lr_user else "Unassigned")
        crlr_role = "CR" if cr_user else ("LR" if lr_user else "CR")

        timetable_cursor = db.timetables.find({"section": sec_name, "day": day_name})
        periods = await timetable_cursor.to_list(length=100)

        combined_sessions = combine_continuous_periods(periods)

        for cs in combined_sessions:
            # Check if session already exists for section, date, and start_time
            existing = await db.sessions.find_one(
                {
                    "section": sec_name,
                    "date": date_str,
                    "start_time": cs["start_time"],
                }
            )

            if not existing:
                session_doc = {
                    "section": sec_name,
                    "year": cs.get("year", sec.get("year", "")),
                    "subject": cs["subject"],
                    "period": cs["period_display"],
                    "periods_included": cs["periods_included"],
                    "start_time": cs["start_time"],
                    "end_time": cs["end_time"],
                    "date": date_str,
                    "crlr_name": crlr_name,
                    "crlr_role": crlr_role,
                    "assigned_cr_id": cr_id,
                    "assigned_lr_id": lr_id,
                    "session_status": SessionStatus.UPCOMING.value,
                    "faculty_response": FacultyResponseStatus.PENDING.value,
                    "response_time": None,
                    "substitute_name": None,
                    "start_notification_sent": False,
                    "escalation_alert_generated": False,
                    "created_at": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc),
                }
                res = await db.sessions.insert_one(session_doc)
                session_doc["_id"] = str(res.inserted_id)
                generated_sessions.append(session_doc)
            else:
                existing["_id"] = str(existing["_id"])
                generated_sessions.append(existing)

    return generated_sessions


def calculate_session_dynamic_state(session: dict, now_local: datetime) -> dict:
    """Computes session status, remaining response window, and expired flags dynamically."""
    date_str = session["date"]
    start_time_str = session["start_time"]
    end_time_str = session["end_time"]

    # Parse full local datetime objects for start and end times
    start_dt = datetime.strptime(f"{date_str} {start_time_str}", "%Y-%m-%d %H:%M").replace(tzinfo=tz_kolkata)
    end_dt = datetime.strptime(f"{date_str} {end_time_str}", "%Y-%m-%d %H:%M").replace(tzinfo=tz_kolkata)

    status = session.get("session_status", SessionStatus.UPCOMING.value)
    faculty_resp = session.get("faculty_response", FacultyResponseStatus.PENDING.value)

    # 10 minute escalation window = 600 seconds from start_dt
    window_end_dt = start_dt.timestamp() + 600  # 10 minutes
    now_ts = now_local.timestamp()

    response_window_expired = False
    remaining_seconds = None

    if faculty_resp != FacultyResponseStatus.PENDING.value:
        # Already responded
        response_window_expired = False
        remaining_seconds = None
        if now_ts >= end_dt.timestamp():
            status = SessionStatus.COMPLETED.value
        else:
            status = SessionStatus.ACTIVE.value
    else:
        # Pending response
        if now_ts < start_dt.timestamp():
            status = SessionStatus.UPCOMING.value
            remaining_seconds = int(window_end_dt - now_ts)
        elif now_ts <= window_end_dt:
            status = SessionStatus.ACTIVE.value
            remaining_seconds = max(0, int(window_end_dt - now_ts))
            response_window_expired = False
        else:
            # 10 minutes passed without response
            remaining_seconds = 0
            response_window_expired = True
            if now_ts >= end_dt.timestamp():
                status = SessionStatus.COMPLETED.value
            else:
                status = SessionStatus.EXPIRED.value

    session_copy = dict(session)
    session_copy["session_status"] = status
    session_copy["response_window_seconds_remaining"] = remaining_seconds
    session_copy["response_window_expired"] = response_window_expired
    return session_copy


async def get_sessions(
    section: Optional[str] = None, date_str: Optional[str] = None
) -> List[ClassSessionResponse]:
    db = get_database()
    now_local = datetime.now(tz_kolkata)

    if not date_str:
        date_str = now_local.strftime("%Y-%m-%d")

    # Ensure sessions for date are synced
    await generate_and_sync_sessions_for_date(now_local)

    query = {"date": date_str}
    if section:
        query["section"] = section.strip().upper()

    cursor = db.sessions.find(query).sort("start_time", 1)
    results = []
    async for s in cursor:
        s["_id"] = str(s["_id"])
        computed = calculate_session_dynamic_state(s, now_local)
        results.append(ClassSessionResponse(**computed))
    return results


async def get_active_sessions_for_section(section: str) -> List[ClassSessionResponse]:
    all_sessions = await get_sessions(section=section)
    return [s for s in all_sessions if s.session_status in [SessionStatus.UPCOMING, SessionStatus.ACTIVE, SessionStatus.EXPIRED]]


async def get_session_by_id(session_id: str) -> Optional[ClassSessionResponse]:
    if not ObjectId.is_valid(session_id):
        return None
    db = get_database()
    s = await db.sessions.find_one({"_id": ObjectId(session_id)})
    if not s:
        return None
    s["_id"] = str(s["_id"])
    now_local = datetime.now(tz_kolkata)
    computed = calculate_session_dynamic_state(s, now_local)
    return ClassSessionResponse(**computed)
