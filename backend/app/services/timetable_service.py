from typing import List, Optional
from app.db.mongodb import get_database
from app.schemas.timetable import TimetablePeriodResponse


async def get_timetable_by_section(
    section: str, year: Optional[str] = None
) -> List[TimetablePeriodResponse]:
    db = get_database()
    query = {"section": section.strip().upper()}
    if year:
        query["year"] = year.strip()

    cursor = db.timetables.find(query).sort([("day", 1), ("period", 1)])
    results = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        results.append(TimetablePeriodResponse(**doc))
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
