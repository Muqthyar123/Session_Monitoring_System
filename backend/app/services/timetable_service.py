import re
from typing import Any, List, Optional
from app.db.mongodb import get_database
from app.schemas.timetable import TimetablePeriodResponse


def format_12h(t_str: str) -> str:
    if not t_str:
        return ""
    m = re.match(r"^(\d{1,2}):(\d{2})", str(t_str).strip())
    if not m:
        return str(t_str)
    h, m_val = int(m.group(1)), int(m.group(2))
    if h > 12:
        h -= 12
    return f"{h:02d}:{m_val:02d}"


def clean_faculty_display(fac: Any) -> Optional[str]:
    """Ensure faculty display string contains only faculty names starting strictly after ':' colon."""
    if not fac:
        return None
    s = str(fac).strip()
    if ":" in s:
        parts = s.rsplit(":", 1)
        s = parts[1].strip()
    # Remove leading numbering like '1) Dr. X'
    s = re.sub(r"^\d+[\).:\s]+", "", s).strip()
    return s if s else None


def _format_doc(doc: dict) -> dict:
    d = dict(doc)
    d["_id"] = str(d["_id"])
    if "start_time" in d:
        d["start_time"] = format_12h(d["start_time"])
    if "end_time" in d:
        d["end_time"] = format_12h(d["end_time"])

    # Clean faculty string if present
    if "faculty" in d and d["faculty"]:
        d["faculty"] = clean_faculty_display(d["faculty"])

    # Clean faculty_names list if present
    if "faculty_names" in d and isinstance(d["faculty_names"], list):
        cleaned_fac_names = []
        for fn in d["faculty_names"]:
            cfn = clean_faculty_display(fn)
            if cfn and cfn not in cleaned_fac_names:
                cleaned_fac_names.append(cfn)
        d["faculty_names"] = cleaned_fac_names
        if not d.get("faculty") and cleaned_fac_names:
            d["faculty"] = ", ".join(cleaned_fac_names)

    return d


async def get_timetable_by_section(
    section: str, year: Optional[str] = None
) -> List[TimetablePeriodResponse]:
    db = get_database()
    sec_clean = section.strip().upper()

    # Try exact section query with year first
    query = {"section": sec_clean}
    if year:
        query["year"] = year.strip()

    cursor = db.timetables.find(query).sort([("day", 1), ("period", 1)])
    results = [TimetablePeriodResponse(**_format_doc(doc)) async for doc in cursor]

    if not results and year:
        # Fallback: try without year filter in case year string format differs (e.g. '2nd Year' vs 'II B.Tech')
        cursor = db.timetables.find({"section": sec_clean}).sort([("day", 1), ("period", 1)])
        results = [TimetablePeriodResponse(**_format_doc(doc)) async for doc in cursor]

    if not results:
        # Fallback: try regex search for section (e.g. 'CSE-A' vs 'CSE A' or 'II-A')
        norm_regex = re.compile(rf"^{re.escape(sec_clean).replace('-', '[- ]?')}$", re.IGNORECASE)
        cursor = db.timetables.find({"section": {"$regex": norm_regex}}).sort([("day", 1), ("period", 1)])
        results = [TimetablePeriodResponse(**_format_doc(doc)) async for doc in cursor]

    return results


async def get_all_timetables() -> List[TimetablePeriodResponse]:
    db = get_database()
    cursor = db.timetables.find().sort([("section", 1), ("day", 1), ("period", 1)])
    results = []
    async for doc in cursor:
        results.append(TimetablePeriodResponse(**_format_doc(doc)))
    return results


async def delete_timetable_by_section(section: str) -> int:
    db = get_database()
    sec_clean = section.strip().upper()
    result = await db.timetables.delete_many({"section": sec_clean})
    await db.sessions.delete_many({"section": sec_clean})
    await db.attendance_records.delete_many({"section": sec_clean})
    return result.deleted_count


async def delete_all_timetables() -> int:
    db = get_database()
    result = await db.timetables.delete_many({})
    await db.sessions.delete_many({})
    await db.attendance_records.delete_many({})
    return result.deleted_count
