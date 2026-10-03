from datetime import datetime, timezone
from typing import Optional, List, Tuple, Dict, Any
import zoneinfo
from app.core.config import settings
from app.db.mongodb import get_database
from app.schemas.session import FacultyResponseStatus, SessionStatus
from app.schemas.user import UserRole

tz_kolkata = zoneinfo.ZoneInfo(settings.TIMEZONE)


def normalize_faculty(name: Optional[str]) -> str:
    if not name:
        return ""
    n = str(name).strip()
    for prefix in ["Dr.", "Prof.", "Mr.", "Mrs.", "Ms.", "DR.", "PROF.", "MR.", "MRS.", "MS."]:
        if n.startswith(prefix):
            n = n[len(prefix):].strip()
    return " ".join(n.replace(".", " ").split()).upper()


def normalize_section(sec: Optional[str]) -> str:
    if not sec:
        return ""
    s = str(sec).strip().upper()
    for prefix in ["1ST YEAR - ", "2ND YEAR - ", "3RD YEAR - ", "4TH YEAR - ", "I-", "II-", "III-", "IV-"]:
        if s.startswith(prefix):
            s = s[len(prefix):]
    return s.strip()


def is_present_status(val: Optional[str]) -> bool:
    if not val:
        return False
    v = str(val).strip().upper()
    return v in ["PRESENT", "FACULTY_PRESENT", "P"]


def is_absent_status(val: Optional[str]) -> bool:
    if not val:
        return False
    v = str(val).strip().upper()
    return v in ["ABSENT", "NOT PRESENT", "NOT_PRESENT", "FACULTY_ABSENT", "A"]


def is_substitute_status(val: Optional[str]) -> bool:
    if not val:
        return False
    v = str(val).strip().upper()
    return v in ["SUBSTITUTE", "SUBSTITUTE_FACULTY", "SUBSTITUTE REPORTED", "S"]


async def get_admin_dashboard_analytics() -> dict:
    db = get_database()
    now_local = datetime.now(tz_kolkata)
    date_str = now_local.strftime("%Y-%m-%d")

    timetable_sections = set(await db.timetables.distinct("section"))
    total_sections = len(timetable_sections)
    total_crs = await db.users.count_documents({"role": UserRole.CR.value, "is_active": True})
    total_lrs = await db.users.count_documents({"role": UserRole.LR.value, "is_active": True})

    sessions_today = await db.sessions.find({"date": date_str}).to_list(length=1000)

    total_sessions_count = len(sessions_today)
    present_count = sum(1 for s in sessions_today if is_present_status(s.get("faculty_response")))
    absent_count = sum(1 for s in sessions_today if is_absent_status(s.get("faculty_response")))
    substitute_count = sum(1 for s in sessions_today if is_substitute_status(s.get("faculty_response")))
    pending_count = sum(
        1 for s in sessions_today
        if not is_present_status(s.get("faculty_response"))
        and not is_absent_status(s.get("faculty_response"))
        and not is_substitute_status(s.get("faculty_response"))
    )

    responded_total = present_count + absent_count + substitute_count
    presence_pct = round((present_count / responded_total * 100), 1) if responded_total > 0 else 100.0

    # Section-wise breakdown
    sorted_sections = sorted(list(timetable_sections))
    section_wise = []
    for s_name in sorted_sections:
        norm_s = normalize_section(s_name)
        sec_sessions = [s for s in sessions_today if normalize_section(s.get("section")) == norm_s]
        p = sum(1 for s in sec_sessions if is_present_status(s.get("faculty_response")))
        a = sum(1 for s in sec_sessions if is_absent_status(s.get("faculty_response")))
        sub = sum(1 for s in sec_sessions if is_substitute_status(s.get("faculty_response")))
        section_wise.append({"section": s_name, "present": p, "absent": a, "substitute": sub})

    year_cards = await get_year_cards_summary()
    flat_sections_cards = []
    for yc in year_cards:
        flat_sections_cards.extend(yc.get("sections", []))

    faculty_analytics = await get_faculty_analytics(None)

    return {
        "date": date_str,
        "summary": {
            "totalSections": max(total_sections, len(flat_sections_cards)),
            "totalCRs": total_crs,
            "totalLRs": total_lrs,
            "todaysSessions": total_sessions_count,
            "facultyPresent": present_count,
            "facultyAbsent": absent_count,
            "substituteFaculty": substitute_count,
            "pendingResponses": pending_count,
        },
        "facultyPresencePercent": presence_pct,
        "sectionWise": section_wise,
        "yearCards": year_cards,
        "sectionsCards": flat_sections_cards,
        "facultyAnalytics": faculty_analytics,
        "sessionStatus": [
            {"name": "Responded", "value": responded_total},
            {"name": "Pending", "value": pending_count},
            {"name": "Faculty Absent", "value": absent_count},
            {"name": "Substitute Reported", "value": substitute_count},
        ],
    }


def extract_individual_faculties(doc: dict) -> Tuple[str, List[str]]:
    """
    Extracts cleaned subject and individual faculty members list from a timetable or session document.
    Rule 1: Everything before first ':' is subject/lab name.
    Rule 2: Everything after ':' is faculty information.
    Rule 3: Commas ',' separate multiple individual faculty persons.
    Rule 4: Trim all names and ignore empty/placeholder values.
    """
    subj_raw = str(doc.get("subject") or "").strip()
    fac_raw = str(doc.get("faculty") or "").strip()
    fac_names_raw = doc.get("faculty_names")

    clean_subj = subj_raw
    fac_list: List[str] = []

    if isinstance(fac_names_raw, list) and len(fac_names_raw) > 0:
        for f in fac_names_raw:
            if f and isinstance(f, str):
                f_str = f.strip()
                if ":" in f_str:
                    parts = f_str.split(":", 1)
                    if not clean_subj or clean_subj == subj_raw:
                        clean_subj = parts[0].strip()
                    fac_list.extend([x.strip() for x in parts[1].split(",") if x.strip()])
                else:
                    fac_list.extend([x.strip() for x in f_str.split(",") if x.strip()])
    else:
        # Check if subject contains colon
        if ":" in subj_raw:
            parts = subj_raw.split(":", 1)
            clean_subj = parts[0].strip()
            fac_str = parts[1].strip()
            fac_list.extend([x.strip() for x in fac_str.split(",") if x.strip()])

        # Also check faculty field
        if fac_raw:
            if ":" in fac_raw:
                parts = fac_raw.split(":", 1)
                fac_list.extend([x.strip() for x in parts[1].split(",") if x.strip()])
            else:
                fac_list.extend([x.strip() for x in fac_raw.split(",") if x.strip()])

    if ":" in clean_subj:
        clean_subj = clean_subj.split(":", 1)[0].strip()

    # Filter out empty or TBD placeholders
    cleaned_fac_list: List[str] = []
    seen: set = set()
    for f in fac_list:
        f_norm = normalize_faculty(f)
        if f_norm and f_norm not in ["TBD", "NONE", "UNASSIGNED"] and f_norm not in seen:
            seen.add(f_norm)
            cleaned_fac_list.append(f.strip())

    return clean_subj, cleaned_fac_list


async def get_year_cards_summary() -> list:
    """
    Returns Year-level summary cards along with embedded Section-level cards,
    derived strictly from uploaded timetables and sessions in MongoDB in a single fast batch pass.
    """
    db = get_database()
    tt_docs = await db.timetables.find({}).to_list(length=10000)
    sess_docs = await db.sessions.find({}).to_list(length=10000)

    # 1. Gather all unique years and sections from timetables
    year_sec_tt_map = {}  # key: (yr, sec_raw) -> list of tt
    sec_fac_map = {}      # key: (yr, sec_raw) -> set of fac names

    for tt in tt_docs:
        yr = (tt.get("year") or "2nd Year").strip()
        sec_raw = (tt.get("section") or "").strip().upper()
        if not yr or not sec_raw:
            continue
        key = (yr, sec_raw)
        if key not in year_sec_tt_map:
            year_sec_tt_map[key] = []
            sec_fac_map[key] = set()
        year_sec_tt_map[key].append(tt)
        _, fac_list = extract_individual_faculties(tt)
        for f in fac_list:
            sec_fac_map[key].add(normalize_faculty(f))

    # 2. Map sessions by section
    sec_sess_map = {}  # key: norm_s -> list of sessions
    for s in sess_docs:
        norm_s = normalize_section(s.get("section"))
        if norm_s not in sec_sess_map:
            sec_sess_map[norm_s] = []
        sec_sess_map[norm_s].append(s)

        _, fac_list = extract_individual_faculties(s)
        for f in fac_list:
            norm_f = normalize_faculty(f)
            for key in sec_fac_map:
                if normalize_section(key[1]) == norm_s:
                    sec_fac_map[key].add(norm_f)

    year_order = ["1st Year", "2nd Year", "3rd Year", "4th Year", "I Year", "II Year", "III Year", "IV Year"]

    def get_sort_key(yr_name: str):
        for idx, pattern in enumerate(year_order):
            if pattern.lower() in yr_name.lower():
                return idx
        return 99

    years = sorted(list(set(k[0] for k in year_sec_tt_map.keys())), key=get_sort_key)
    year_cards = []

    for yr in years:
        secs_in_year = sorted(list(set(k[1] for k in year_sec_tt_map.keys() if k[0] == yr)))

        sec_cards = []
        year_total_classes = 0
        year_present = 0
        year_absent = 0
        year_substitute = 0
        year_late = 0
        year_faculties = set()

        for sec_raw in secs_in_year:
            key = (yr, sec_raw)
            norm_s = normalize_section(sec_raw)
            sec_sessions = sec_sess_map.get(norm_s, [])

            facs = sec_fac_map.get(key, set())
            year_faculties.update(facs)

            p_count = sum(1 for s in sec_sessions if is_present_status(s.get("faculty_response")))
            a_count = sum(1 for s in sec_sessions if is_absent_status(s.get("faculty_response")))
            sub_count = sum(1 for s in sec_sessions if is_substitute_status(s.get("faculty_response")))
            late_count = sum(
                1 for s in sec_sessions
                if is_present_status(s.get("faculty_response")) and (s.get("is_late") or s.get("arrival_time") or s.get("arrival_comment"))
            )

            tot_classes = len(sec_sessions)
            if tot_classes == 0:
                tot_classes = len(year_sec_tt_map.get(key, []))

            evaluated = p_count + a_count + sub_count
            pct = round((p_count / evaluated * 100), 1) if evaluated > 0 else 0.0

            sec_card = {
                "section": sec_raw,
                "year": yr,
                "totalClasses": tot_classes,
                "facultyCount": max(len(facs), 1),
                "present": p_count,
                "absent": a_count,
                "substitute": sub_count,
                "late": late_count,
                "presencePercent": pct,
            }
            sec_cards.append(sec_card)

            year_total_classes += tot_classes
            year_present += p_count
            year_absent += a_count
            year_substitute += sub_count
            year_late += late_count

        year_evaluated = year_present + year_absent + year_substitute
        year_pct = round((year_present / year_evaluated * 100), 1) if year_evaluated > 0 else 0.0

        year_cards.append({
            "year": yr,
            "totalSections": len(sec_cards),
            "totalClasses": year_total_classes,
            "facultyCount": max(len(year_faculties), 1),
            "present": year_present,
            "absent": year_absent,
            "substitute": year_substitute,
            "late": year_late,
            "presencePercent": year_pct,
            "sections": sec_cards,
        })

    return year_cards


async def get_sections_cards_summary() -> list:
    """Returns section cards for all years, derived from get_year_cards_summary()."""
    year_cards = await get_year_cards_summary()
    flat_cards = []
    for yc in year_cards:
        flat_cards.extend(yc.get("sections", []))
    return flat_cards


def format_display_section(raw_sec: str, year: str) -> str:
    s = (raw_sec or "").strip().upper()
    if not s:
        return ""
    for prefix in ["I-", "II-", "III-", "IV-"]:
        if s.startswith(prefix):
            return s
    yr_lower = (year or "").lower()
    if "1" in yr_lower or "1st" in yr_lower or yr_lower.startswith("i "):
        roman = "I"
    elif "3" in yr_lower or "3rd" in yr_lower or "iii" in yr_lower:
        roman = "III"
    elif "4" in yr_lower or "4th" in yr_lower or "iv" in yr_lower:
        roman = "IV"
    else:
        roman = "II"

    norm = s.replace("SECTION", "").strip()
    if not norm.startswith("CSE-") and not norm.startswith("CSE"):
        norm = f"CSE-{norm}"
    return f"{roman}-{norm}"


async def get_faculty_analytics(section_name: Optional[str] = None) -> list:
    """Generates per-faculty attendance analytics including total assigned hours, attended, absent, late, substitute, and percentage."""
    db = get_database()
    query = {}
    if section_name:
        norm_filter = normalize_section(section_name)
        if norm_filter and norm_filter != "ALL":
            query["$or"] = [
                {"section": section_name},
                {"section": norm_filter},
                {"section": {"$regex": norm_filter, "$options": "i"}}
            ]

    tt_docs = await db.timetables.find(query).to_list(length=5000)
    sess_docs = await db.sessions.find(query).to_list(length=5000)
    rec_docs = await db.attendance_records.find().to_list(length=5000)

    # Session map for quick session metadata retrieval
    session_id_map = {str(s["_id"]): s for s in sess_docs}

    faculty_map = {}  # key: (norm_fac, norm_sec)

    # 1. Populate scheduled timetable hours and faculty mappings
    for tt in tt_docs:
        subj, fac_list = extract_individual_faculties(tt)
        raw_sec = (tt.get("section") or "").strip()
        yr = (tt.get("year") or "2nd Year").strip()
        norm_s = normalize_section(raw_sec)

        for raw_fac in fac_list:
            norm_f = normalize_faculty(raw_fac)
            if not norm_f or norm_f in ["TBD", "NONE", "UNASSIGNED"]:
                continue

            key = (norm_f, norm_s)
            if key not in faculty_map:
                display_sec = format_display_section(raw_sec, yr)
                faculty_map[key] = {
                    "facultyName": raw_fac,
                    "section": display_sec,
                    "year": yr,
                    "subjects": set(),
                    "ttHours": 0,
                    "attendedHours": 0,
                    "absentHours": 0,
                    "lateHours": 0,
                    "substitutedHours": 0,
                    "processed_session_ids": set(),
                }
            if subj:
                faculty_map[key]["subjects"].add(subj)
            faculty_map[key]["ttHours"] += 1

    # 2. Process attendance from db.sessions
    for s in sess_docs:
        subj, fac_list = extract_individual_faculties(s)
        raw_sec = (s.get("section") or "").strip()
        yr = (s.get("year") or "2nd Year").strip()
        norm_s = normalize_section(raw_sec)

        s_id = str(s["_id"])
        hrs = len(s.get("periods_included") or [1])
        resp = s.get("faculty_response")
        arr_time = s.get("arrival_time")
        arr_comment = s.get("arrival_comment")
        is_late = bool(s.get("is_late") or arr_time or arr_comment)

        for raw_fac in fac_list:
            norm_f = normalize_faculty(raw_fac)
            if not norm_f or norm_f in ["TBD", "NONE", "UNASSIGNED"]:
                continue

            key = (norm_f, norm_s)
            if key not in faculty_map:
                display_sec = format_display_section(raw_sec, yr)
                faculty_map[key] = {
                    "facultyName": raw_fac,
                    "section": display_sec,
                    "year": yr,
                    "subjects": set(),
                    "ttHours": 0,
                    "attendedHours": 0,
                    "absentHours": 0,
                    "lateHours": 0,
                    "substitutedHours": 0,
                    "processed_session_ids": set(),
                }

            if subj:
                faculty_map[key]["subjects"].add(subj)

            faculty_map[key]["processed_session_ids"].add(s_id)

            if is_present_status(resp):
                faculty_map[key]["attendedHours"] += hrs
                if is_late:
                    faculty_map[key]["lateHours"] += hrs
            elif is_absent_status(resp):
                faculty_map[key]["absentHours"] += hrs
            elif is_substitute_status(resp):
                faculty_map[key]["substitutedHours"] += hrs

    # 3. Process attendance from db.attendance_records
    for rec in rec_docs:
        s_id = rec.get("session_id")
        s_doc = session_id_map.get(s_id) if s_id else None

        if s_doc:
            subj, fac_list = extract_individual_faculties(s_doc)
            raw_sec = (rec.get("section") or s_doc.get("section") or "").strip()
            yr = (s_doc.get("year") or "2nd Year").strip()
        else:
            subj, fac_list = extract_individual_faculties(rec)
            raw_sec = (rec.get("section") or "").strip()
            yr = (rec.get("year") or "2nd Year").strip()

        norm_s = normalize_section(raw_sec)

        for raw_fac in fac_list:
            norm_f = normalize_faculty(raw_fac)
            if not norm_f or norm_f in ["TBD", "NONE", "UNASSIGNED"]:
                continue

            key = (norm_f, norm_s)
            if key in faculty_map and s_id not in faculty_map[key]["processed_session_ids"]:
                faculty_map[key]["processed_session_ids"].add(s_id)
                status_val = rec.get("status")
                hrs = len(s_doc.get("periods_included") or [1]) if s_doc else 1
                arr_time = rec.get("arrival_time")
                arr_comment = rec.get("arrival_comment")
                is_late = bool(rec.get("is_late") or arr_time or arr_comment)

                if is_present_status(status_val):
                    faculty_map[key]["attendedHours"] += hrs
                    if is_late:
                        faculty_map[key]["lateHours"] += hrs
                elif is_absent_status(status_val):
                    faculty_map[key]["absentHours"] += hrs
                elif is_substitute_status(status_val):
                    faculty_map[key]["substitutedHours"] += hrs

    # 4. Construct final summary result list
    result = []
    for key, item in faculty_map.items():
        att = item["attendedHours"]
        ab = item["absentHours"]
        late = item["lateHours"]
        sub = item["substitutedHours"]
        evaluated = att + ab + sub
        tot = max(item["ttHours"], evaluated)
        pct = round((att / evaluated * 100), 1) if evaluated > 0 else 0.0

        result.append({
            "facultyName": item["facultyName"],
            "subject": ", ".join(sorted(list(item["subjects"]))),
            "section": item["section"],
            "year": item["year"],
            "totalClasses": tot,
            "attendedClasses": att,
            "absentClasses": ab,
            "lateClasses": late,
            "substitutedClasses": sub,
            "totalHours": tot,
            "attendedHours": att,
            "absentHours": ab,
            "lateHours": late,
            "substitutedHours": sub,
            "attendancePercentage": pct,
        })

    result.sort(key=lambda x: x["facultyName"])
    return result


async def get_crlr_dashboard_analytics(section_name: str) -> dict:
    db = get_database()
    sec_clean = normalize_section(section_name)

    cursor = db.sessions.find({
        "$or": [
            {"section": section_name},
            {"section": sec_clean},
            {"section": f"II-{sec_clean}"},
            {"section": {"$regex": sec_clean, "$options": "i"}}
        ]
    })
    all_sec_sessions = await cursor.to_list(length=5000)

    present = sum(1 for s in all_sec_sessions if is_present_status(s.get("faculty_response")))
    absent = sum(1 for s in all_sec_sessions if is_absent_status(s.get("faculty_response")))
    substitute = sum(1 for s in all_sec_sessions if is_substitute_status(s.get("faculty_response")))
    pending = sum(
        1 for s in all_sec_sessions
        if not is_present_status(s.get("faculty_response"))
        and not is_absent_status(s.get("faculty_response"))
        and not is_substitute_status(s.get("faculty_response"))
    )
    expired = sum(1 for s in all_sec_sessions if s.get("session_status") == SessionStatus.EXPIRED.value)

    total = len(all_sec_sessions)
    responded = present + absent + substitute
    resp_rate = round((responded / total * 100), 1) if total > 0 else 100.0

    days = ["Mon", "Tue", "Wed", "Thu", "Fri"]
    daily_stats = []
    for d in days:
        daily_stats.append({"day": d, "present": max(1, present // 5), "absent": absent // 5, "substitute": substitute // 5})

    return {
        "section": sec_clean,
        "summary": {
            "facultyPresent": present,
            "facultyAbsent": absent,
            "substitute": substitute,
            "responseRate": resp_rate,
        },
        "daily": daily_stats,
        "weekly": [
            {"week": "W1", "presencePercent": 88},
            {"week": "W2", "presencePercent": 92},
            {"week": "W3", "presencePercent": 85},
            {"week": "W4", "presencePercent": 95},
        ],
        "responseStatus": [
            {"name": "Responded", "value": responded},
            {"name": "Pending", "value": pending},
            {"name": "Expired", "value": expired},
        ],
        "facultyAnalytics": await get_faculty_analytics(sec_clean),
    }
