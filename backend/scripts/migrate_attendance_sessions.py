"""Apply additive attendance-session indexes after a verified database backup.

This migration never updates or deletes documents and never drops/replaces indexes.
Run with the intended environment selected: python scripts/migrate_attendance_sessions.py
"""
import asyncio

from pymongo import ASCENDING

from app.db.mongodb import close_mongo_connection, connect_to_mongo, get_database


async def apply_migration() -> None:
    await connect_to_mongo()
    try:
        db = get_database()
        # Check for conflicts before creating a unique partial index. Historical
        # markers without session_id remain outside this index and are untouched.
        duplicate = await db.student_attendance_submissions.aggregate([
            {"$match": {"session_id": {"$type": "string"}}},
            {"$group": {"_id": {"year": "$year", "section": "$section", "date": "$date", "session_id": "$session_id"}, "count": {"$sum": 1}}},
            {"$match": {"count": {"$gt": 1}}},
            {"$limit": 1},
        ]).to_list(length=1)
        if duplicate:
            raise RuntimeError("Duplicate session submissions found. No database changes were made.")

        await db.student_attendance_sessions.create_index(
            [("year", ASCENDING), ("section", ASCENDING), ("date", ASCENDING), ("roll_number", ASCENDING), ("session_id", ASCENDING)],
            unique=True,
            name="uniq_student_session_attendance",
        )
        await db.student_attendance_submissions.create_index(
            [("year", ASCENDING), ("section", ASCENDING), ("date", ASCENDING), ("session_id", ASCENDING)],
            unique=True,
            partialFilterExpression={"session_id": {"$type": "string"}},
            name="uniq_session_submission",
        )
        print("Attendance session indexes created. No documents were modified or deleted.")
    finally:
        await close_mongo_connection()


if __name__ == "__main__":
    asyncio.run(apply_migration())
