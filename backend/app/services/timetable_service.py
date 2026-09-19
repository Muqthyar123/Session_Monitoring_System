import re
from typing import List, Optional
from app.db.mongodb import get_database
from app.schemas.timetable import TimetablePeriodResponse


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
    results = [TimetablePeriodResponse(**{**doc, "_id": str(doc["_id"])}) async for doc in cursor]

    if not results and year:
        # Fallback: try without year filter in case year string format differs (e.g. '2nd Year' vs 'II B.Tech')
        cursor = db.timetables.find({"section": sec_clean}).sort([("day", 1), ("period", 1)])
        results = [TimetablePeriodResponse(**{**doc, "_id": str(doc["_id"])}) async for doc in cursor]

    if not results:
        # Fallback: try regex search for section (e.g. 'CSE-A' vs 'CSE A' or 'II-A')
        norm_regex = re.compile(rf"^{re.escape(sec_clean).replace('-', '[- ]?')}$", re.IGNORECASE)
        cursor = db.timetables.find({"section": {"$regex": norm_regex}}).sort([("day", 1), ("period", 1)])
        results = [TimetablePeriodResponse(**{**doc, "_id": str(doc["_id"])}) async for doc in cursor]

    if not results:
        # Final fallback: if only 1 section exists in DB, return that section's timetable
        distinct_secs = await db.timetables.distinct("section")
        if len(distinct_secs) == 1:
            cursor = db.timetables.find({"section": distinct_secs[0]}).sort([("day", 1), ("period", 1)])
            results = [TimetablePeriodResponse(**{**doc, "_id": str(doc["_id"])}) async for doc in cursor]

    return results


async def get_all_timetables() -> List[TimetablePeriodResponse]:
    db = get_database()
    cursor = db.timetables.find().sort([("section", 1), ("day", 1), ("period", 1)])
    results = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        results.append(TimetablePeriodResponse(**doc))
    return results


async def delete_timetable_by_section(section: str) -> int:
    db = get_database()
    result = await db.timetables.delete_many({"section": section.strip().upper()})
    return result.deleted_count


async def delete_all_timetables() -> int:
    db = get_database()
    result = await db.timetables.delete_many({})
    return result.deleted_count
