import logging
from pymongo import ASCENDING, DESCENDING
from app.db.mongodb import get_database

logger = logging.getLogger("fams.indexes")


async def _ensure_index(collection, keys, **options):
    """Reuse compatible indexes; safely migrate legacy non-unique patterns."""
    expected_keys = [(field, direction) for field, direction in keys]
    expected_unique = bool(options.get("unique", False))
    expected_partial = options.get("partialFilterExpression")
    index_info = await collection.index_information()

    for name, info in index_info.items():
        actual_keys = [(field, direction) for field, direction in info.get("key", [])]
        if actual_keys != expected_keys:
            continue

        if not expected_unique:
            return name

        if info.get("unique", False) and info.get("partialFilterExpression") == expected_partial:
            return name

        pipeline = []
        if expected_partial:
            pipeline.append({"$match": expected_partial})
        pipeline.extend([
            {"$group": {
                "_id": {field: f"${field}" for field, _ in expected_keys},
                "count": {"$sum": 1},
            }},
            {"$match": {"count": {"$gt": 1}}},
            {"$limit": 1},
        ])
        duplicates = await collection.aggregate(pipeline).to_list(length=1)
        if duplicates:
            raise RuntimeError("Duplicate documents prevent required unique index creation.")

        logger.info("Replacing legacy index %s after confirming uniqueness.", name)
        await collection.drop_index(name)
        break

    return await collection.create_index(keys, **options)


async def create_db_indexes():
    """Ensure required database indexes are created idempotently."""
    db = get_database()

    try:
        # users collection
        await _ensure_index(db.users, [("email", ASCENDING)], unique=True)

        await _ensure_index(db.users,
            [("roll_number", ASCENDING)],
            unique=True,
            partialFilterExpression={"roll_number": {"$type": "string"}},
        )
        await _ensure_index(db.users,
            [("mentor_id", ASCENDING)],
            unique=True,
            partialFilterExpression={"mentor_id": {"$type": "string"}},
        )

        await _ensure_index(db.users, [("role", ASCENDING)])
        await _ensure_index(db.users, [("role", ASCENDING), ("created_at", DESCENDING)])
        await _ensure_index(db.users, [("section", ASCENDING)])

        # students collection
        await _ensure_index(db.students, [("roll_number", ASCENDING)], unique=True)
        await _ensure_index(db.students, [("year", ASCENDING), ("section", ASCENDING), ("roll_number", ASCENDING)])


        # student_attendance collection
        await _ensure_index(db.student_attendance,
            [("year", ASCENDING), ("section", ASCENDING), ("date", ASCENDING), ("roll_number", ASCENDING)],
            unique=True,
        )
        await _ensure_index(db.student_attendance, [("date", DESCENDING)])
        await _ensure_index(db.student_attendance, [("roll_number", ASCENDING)])

        # sections collection
        await _ensure_index(db.sections, [("section_name", ASCENDING)], unique=True)
        await _ensure_index(db.sections, [("year", ASCENDING)])

        # timetables collection
        await _ensure_index(db.timetables,
            [("section", ASCENDING), ("day", ASCENDING), ("period", ASCENDING)],
            unique=True,
        )
        await _ensure_index(db.timetables,
            [("section", ASCENDING), ("day", ASCENDING), ("start_time", ASCENDING)]
        )

        # sessions collection
        await _ensure_index(db.sessions,
            [("section", ASCENDING), ("date", ASCENDING), ("start_time", ASCENDING)],
            unique=True,
        )
        await _ensure_index(db.sessions, [("status", ASCENDING)])
        await _ensure_index(db.sessions, [("date", ASCENDING)])

        # attendance_records collection
        await _ensure_index(db.attendance_records, [("session_id", ASCENDING)])
        await _ensure_index(db.attendance_records, [("user_id", ASCENDING)])
        await _ensure_index(db.attendance_records, [("created_at", DESCENDING)])

        # notifications collection
        await _ensure_index(db.notifications, [("recipient_user_id", ASCENDING)])
        await _ensure_index(db.notifications, [("is_read", ASCENDING)])
        await _ensure_index(db.notifications, [("created_at", DESCENDING)])

        # push_subscriptions collection
        await _ensure_index(db.push_subscriptions, [("user_id", ASCENDING)])
        await _ensure_index(db.push_subscriptions, [("token", ASCENDING)], unique=True)

        # planned_absences collection
        await _ensure_index(db.planned_absences, [("student_id", ASCENDING), ("status", ASCENDING)])
        await _ensure_index(db.planned_absences, [("mentor_id", ASCENDING), ("status", ASCENDING)])
        await _ensure_index(db.planned_absences, [("roll_number", ASCENDING), ("status", ASCENDING)])
        await _ensure_index(db.planned_absences, [("start_date", ASCENDING), ("end_date", ASCENDING)])

        # mentor_student_mappings collection
        await _ensure_index(db.mentor_student_mappings, [("mentor_id", ASCENDING)])
        await _ensure_index(db.mentor_student_mappings, [("year", ASCENDING), ("section", ASCENDING)])
        await _ensure_index(db.mentor_student_mappings, [("student_ids", ASCENDING)])

        # audit_logs collection
        await _ensure_index(db.audit_logs, [("created_at", DESCENDING)])
        await _ensure_index(db.audit_logs, [("actor_id", ASCENDING)])

        logger.info("MongoDB database indexes successfully created.")
    except Exception as exc:
        logger.error("MongoDB index initialization failed (%s).", type(exc).__name__)
        raise RuntimeError(
            "MongoDB index initialization failed. Check for duplicate existing data or conflicting indexes."
        ) from None
