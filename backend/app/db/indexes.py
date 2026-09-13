import logging
from pymongo import IndexModel, ASCENDING, DESCENDING
from app.db.mongodb import get_database

logger = logging.getLogger("fams.indexes")


async def create_db_indexes():
    """Ensure required database indexes are created idempotently."""
    db = get_database()

    # users collection
    await db.users.create_index([("email", ASCENDING)], unique=True)
    await db.users.create_index(
        [("roll_number", ASCENDING)],
        unique=True,
        partialFilterExpression={"roll_number": {"$type": "string"}},
    )
    await db.users.create_index([("role", ASCENDING)])
    await db.users.create_index([("section", ASCENDING)])

    # sections collection
    await db.sections.create_index([("section_name", ASCENDING)], unique=True)
    await db.sections.create_index([("year", ASCENDING)])

    # timetables collection
    await db.timetables.create_index(
        [("section", ASCENDING), ("day", ASCENDING), ("period", ASCENDING)],
        unique=True,
    )
    await db.timetables.create_index(
        [("section", ASCENDING), ("day", ASCENDING), ("start_time", ASCENDING)]
    )

    # sessions collection
    await db.sessions.create_index(
        [("section", ASCENDING), ("date", ASCENDING), ("start_time", ASCENDING)],
        unique=True,
    )
    await db.sessions.create_index([("status", ASCENDING)])
    await db.sessions.create_index([("date", ASCENDING)])

    # attendance_records collection
    await db.attendance_records.create_index([("session_id", ASCENDING)])
    await db.attendance_records.create_index([("user_id", ASCENDING)])
    await db.attendance_records.create_index([("created_at", DESCENDING)])

    # notifications collection
    await db.notifications.create_index([("recipient_user_id", ASCENDING)])
    await db.notifications.create_index([("is_read", ASCENDING)])
    await db.notifications.create_index([("created_at", DESCENDING)])

    # push_subscriptions collection
    await db.push_subscriptions.create_index([("user_id", ASCENDING)])
    await db.push_subscriptions.create_index([("token", ASCENDING)], unique=True)

    # audit_logs collection
    await db.audit_logs.create_index([("created_at", DESCENDING)])
    await db.audit_logs.create_index([("actor_id", ASCENDING)])

    logger.info("MongoDB database indexes successfully created.")
