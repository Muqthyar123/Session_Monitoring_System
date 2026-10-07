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
        fac_names = p.get("faculty_names") or ([f.strip() for f in fac.split(",") if f.strip()] if fac else [])
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
                "faculty_names": fac_names,
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
                    "faculty_names": fac_names,
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


async def generate_and_sync_sessions_for_date(
    target_date: Optional[datetime] = None, section_filter: Optional[str] = None
) -> List[dict]:
    """Reads timetable for current day of week and creates/updates sessions in MongoDB idempotently in a single fast batch pass."""
    db = get_database()
    now_local = (target_date or datetime.now(tz_kolkata))
    date_str = now_local.strftime("%Y-%m-%d")
    day_name = now_local.strftime("%A")  # Monday..Sunday

    sec_clean = section_filter.strip().upper() if section_filter else None

    # Check if sessions for target date (and section if specified) already exist
    count_query = {"date": date_str}
    if sec_clean:
        count_query["$or"] = [
            {"section": section_filter},
            {"section": sec_clean},
            {"section": f"II-{sec_clean}"},
            {"section": {"$regex": f"^{sec_clean}$", "$options": "i"}},
        ]

    existing_count = await db.sessions.count_documents(count_query)
    if existing_count > 0:
        cursor = db.sessions.find(count_query).sort("start_time", 1)
        existing_docs = await cursor.to_list(length=1000)
        for d in existing_docs:
            d["_id"] = str(d["_id"])
        return existing_docs

    # If sessions do not exist for date/section yet, sync them in a fast batch pass
    sections_query = {}
    if sec_clean:
        sections_query["$or"] = [
            {"section_name": section_filter},
            {"section_name": sec_clean},
            {"section_name": f"II-{sec_clean}"},
            {"section_name": {"$regex": f"^{sec_clean}$", "$options": "i"}},
        ]

    all_sections = await db.sections.find(sections_query).to_list(length=1000)
    if not all_sections:
        # Fallback to distinct sections from timetables
        tt_distinct = await db.timetables.distinct("section")
        all_sections = [{"section_name": s, "year": "2nd Year"} for s in tt_distinct if s]

    tt_query = {"day": day_name}
    if sec_clean:
        tt_query["$or"] = [
            {"section": section_filter},
            {"section": sec_clean},
            {"section": f"II-{sec_clean}"},
            {"section": {"$regex": f"^{sec_clean}$", "$options": "i"}},
        ]

    tt_docs = await db.timetables.find(tt_query).to_list(length=5000)

    # Group timetables by section
    sec_tt_map = {}
    for tt in tt_docs:
        s_name = (tt.get("section") or "").strip()
        if not s_name:
            continue
        if s_name not in sec_tt_map:
            sec_tt_map[s_name] = []
        sec_tt_map[s_name].append(tt)

    # Batch fetch CR/LR users
    user_docs = await db.users.find({"role": {"$in": ["CR", "LR"]}}).to_list(length=1000)
    user_id_map = {str(u["_id"]): u for u in user_docs}

    generated_sessions = []
    sessions_to_insert = []

    for sec_doc in all_sections:
        sec_name = sec_doc.get("section_name", "")
        if not sec_name or sec_name not in sec_tt_map:
            continue

        cr_id = sec_doc.get("assigned_cr_id")
        lr_id = sec_doc.get("assigned_lr_id")

        cr_user = user_id_map.get(str(cr_id)) if cr_id else None
        lr_user = user_id_map.get(str(lr_id)) if lr_id else None

        crlr_name = cr_user.get("name") if cr_user else (lr_user.get("name") if lr_user else "Unassigned")
        crlr_role = "CR" if cr_user else ("LR" if lr_user else "CR")

        periods = sec_tt_map[sec_name]
        combined_sessions = combine_continuous_periods(periods)

        for cs in combined_sessions:
            fac_val = cs.get("faculty", "")
            subj_val = cs["subject"]

            session_doc = {
                "section": sec_name,
                "year": cs.get("year", sec_doc.get("year", "2nd Year")),
                "subject": subj_val,
                "faculty": fac_val,
                "faculty_names": cs.get("faculty_names", []),
                "period": cs["period_display"],
                "periods_included": cs["periods_included"],
                "start_time": cs["start_time"],
                "end_time": cs["end_time"],
                "date": date_str,
                "crlr_name": crlr_name,
                "crlr_role": crlr_role,
                "assigned_cr_id": str(cr_id) if cr_id else None,
                "assigned_lr_id": str(lr_id) if lr_id else None,
                "session_status": SessionStatus.UPCOMING.value,
                "faculty_response": FacultyResponseStatus.PENDING.value,
                "response_time": None,
                "substitute_name": None,
                "start_notification_sent": False,
                "escalation_alert_generated": False,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            }
            sessions_to_insert.append(session_doc)

    if sessions_to_insert:
        res = await db.sessions.insert_many(sessions_to_insert)
        for doc, inserted_id in zip(sessions_to_insert, res.inserted_ids):
            doc["_id"] = str(inserted_id)
            generated_sessions.append(doc)

    return generated_sessions


def calculate_session_dynamic_state(session: dict, now_local: datetime) -> dict:
    """Computes session status, remaining response window, and expired flags dynamically."""
    date_str = session["date"]
    start_time_str = session["start_time"]
    end_time_str = session["end_time"]

    # Parse full local datetime objects for start and end times
    def _parse_time_dt(t_str: str) -> datetime:
        dt = datetime.strptime(f"{date_str} {t_str}", "%Y-%m-%d %H:%M").replace(tzinfo=tz_kolkata)
        if dt.hour < 8:
            dt = dt.replace(hour=dt.hour + 12)
        return dt

    start_dt = _parse_time_dt(start_time_str)
    end_dt = _parse_time_dt(end_time_str)

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
        status = SessionStatus.COMPLETED.value
    else:
        # Pending response
        if now_ts < start_dt.timestamp():
            status = SessionStatus.UPCOMING.value
            remaining_seconds = int(window_end_dt - now_ts)
        elif now_ts < end_dt.timestamp():
            status = SessionStatus.ACTIVE.value
            remaining_seconds = max(0, int(window_end_dt - now_ts))
            response_window_expired = now_ts > window_end_dt
        else:
            # Class period ended without response
            remaining_seconds = 0
            response_window_expired = True
            status = SessionStatus.EXPIRED.value

    session_copy = dict(session)
    session_copy["session_status"] = status
    session_copy["response_window_seconds_remaining"] = remaining_seconds
    session_copy["response_window_expired"] = response_window_expired
    return session_copy


async def get_sessions(
    section: Optional[str] = None,
    year: Optional[str] = None,
    branch: Optional[str] = None,
    status_filter: Optional[str] = None,
    date_str: Optional[str] = None,
) -> List[ClassSessionResponse]:
    db = get_database()
    now_local = datetime.now(tz_kolkata)

    if not date_str:
        date_str = now_local.strftime("%Y-%m-%d")

    # Ensure sessions for date are synced
    await generate_and_sync_sessions_for_date(now_local, section_filter=section)

    query = {"date": date_str}
    and_clauses = [{"date": date_str}]

    if section and section.upper() != "ALL":
        sec_clean = section.strip().upper()
        sec_clause = {
            "$or": [
                {"section": section},
                {"section": sec_clean},
                {"section": f"II-{sec_clean}"},
                {"section": {"$regex": f"^{sec_clean}$", "$options": "i"}},
            ]
        }
        and_clauses.append(sec_clause)

    if year and year.upper() != "ALL":
        yr_clean = year.replace("Year", "").strip()
        and_clauses.append({
            "$or": [
                {"year": year},
                {"year": {"$regex": yr_clean, "$options": "i"}},
            ]
        })

    if branch and branch.upper() != "ALL":
        b_clean = branch.strip().upper()
        and_clauses.append({
            "$or": [
                {"branch": b_clean},
                {"department": b_clean},
                {"section": {"$regex": b_clean, "$options": "i"}},
            ]
        })

    query = {"$and": and_clauses} if len(and_clauses) > 1 else and_clauses[0]

    cursor = db.sessions.find(query).sort("start_time", 1)
    results = []
    async for s in cursor:
        s["_id"] = str(s["_id"])
        computed = calculate_session_dynamic_state(s, now_local)

        # Apply status filter if provided
        if status_filter and status_filter.upper() != "ALL":
            sf = status_filter.strip().upper()
            curr_status = str(computed.get("session_status", "")).upper()
            curr_resp = str(computed.get("faculty_response", "")).upper()

            if sf == "COMPLETED":
                is_completed = (
                    curr_status == "COMPLETED"
                    or curr_resp in ["PRESENT", "ABSENT", "NOT PRESENT", "NOT_PRESENT", "SUBSTITUTE", "SUBSTITUTE_FACULTY"]
                )
                if not is_completed:
                    continue
            elif sf == "ACTIVE" or sf == "LIVE":
                if curr_status != "ACTIVE":
                    continue
            elif sf == "UPCOMING":
                if curr_status != "UPCOMING":
                    continue
            elif sf == "EXPIRED":
                if curr_status != "EXPIRED":
                    continue
            elif sf == "PENDING":
                if curr_resp not in ["PENDING", ""] or curr_status == "COMPLETED":
                    continue

        results.append(ClassSessionResponse(**computed))

    results.sort(key=lambda s: min(s.periods_included) if s.periods_included else 99)
    return results


async def get_active_sessions_for_section(section: str) -> List[ClassSessionResponse]:
    all_sessions = await get_sessions(section=section)
    return all_sessions


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
