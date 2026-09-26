import logging
from pymongo import IndexModel, ASCENDING, DESCENDING
from app.db.mongodb import get_database, db_manager

logger = logging.getLogger("fams.indexes")


async def create_db_indexes():
    """Ensure required database indexes are created idempotently."""
    db = get_database()

    try:
        # users collection
        await db.users.create_index([("email", ASCENDING)], unique=True)

        # mongomock does not support partialFilterExpression and throws DuplicateKeyError when fields are missing/None
        if not getattr(db_manager, "is_mock_mode", False):
            await db.users.create_index(
                [("roll_number", ASCENDING)],
                unique=True,
                partialFilterExpression={"roll_number": {"$type": "string"}},
            )
            await db.users.create_index(
                [("mentor_id", ASCENDING)],
                unique=True,
                partialFilterExpression={"mentor_id": {"$type": "string"}},
            )
        else:
            try:
                await db.users.create_index([("roll_number", ASCENDING)], sparse=True)
            except Exception:
                pass
            try:
                await db.users.create_index([("mentor_id", ASCENDING)], sparse=True)
            except Exception:
                pass

        await db.users.create_index([("role", ASCENDING)])
        await db.users.create_index([("section", ASCENDING)])

        # students collection
        try:
            await db.students.create_index(
                [("roll_number", ASCENDING)],
                unique=True,
            )
        except Exception:
            pass
        await db.students.create_index([("year", ASCENDING), ("section", ASCENDING)])

        # student_attendance collection
        try:
            await db.student_attendance.create_index(
                [("year", ASCENDING), ("section", ASCENDING), ("date", ASCENDING), ("roll_number", ASCENDING)],
                unique=True,
            )
        except Exception:
            pass
        await db.student_attendance.create_index([("date", DESCENDING)])
        await db.student_attendance.create_index([("roll_number", ASCENDING)])

        # sections collection
        try:
            await db.sections.create_index([("section_name", ASCENDING)], unique=True)
        except Exception:
            pass
        await db.sections.create_index([("year", ASCENDING)])

        # timetables collection
        try:
            await db.timetables.create_index(
                [("section", ASCENDING), ("day", ASCENDING), ("period", ASCENDING)],
                unique=True,
            )
        except Exception:
            pass
        await db.timetables.create_index(
            [("section", ASCENDING), ("day", ASCENDING), ("start_time", ASCENDING)]
        )

        # sessions collection
        try:
            await db.sessions.create_index(
                [("section", ASCENDING), ("date", ASCENDING), ("start_time", ASCENDING)],
                unique=True,
            )
        except Exception:
            pass
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
        try:
            await db.push_subscriptions.create_index([("token", ASCENDING)], unique=True)
        except Exception:
            pass

        # audit_logs collection
        await db.audit_logs.create_index([("created_at", DESCENDING)])
        await db.audit_logs.create_index([("actor_id", ASCENDING)])

        logger.info("MongoDB database indexes successfully created.")
    except Exception as exc:
        logger.warning("Index creation notice: %s", exc)
