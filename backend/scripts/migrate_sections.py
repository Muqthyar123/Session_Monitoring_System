import asyncio
import logging
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.db.mongodb import close_mongo_connection, connect_to_mongo, get_database

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("migrate_sections")


async def migrate():
    logger.info("Starting section migration...")
    await connect_to_mongo()
    db = get_database()

    sections_map = {
        "CSE-A": "II-CSE-A",
        "CSE-B": "II-CSE-B",
        "CSE-C": "II-CSE-C",
        "CSE-D": "II-CSE-D",
        "CSE-E": "II-CSE-E",
        "CSE-F": "II-CSE-F",
        "CSE-G": "II-CSE-G",
        "CSE-H": "II-CSE-H",
        "CSE-I": "II-CSE-I",
        "CSE-J": "II-CSE-J",
        "II-A": "II-CSE-A",
        "II-B": "II-CSE-B",
        "II-C": "II-CSE-C",
    }

    # Remove old II-A records completely
    await db.sections.delete_many({"section_name": {"$in": ["II-A", "II-B", "II-C", "III-A", "III-B"]}})
    await db.timetables.delete_many({"section": {"$in": ["II-A", "II-B", "II-C", "III-A", "III-B"]}})
    await db.sessions.delete_many({"section": {"$in": ["II-A", "II-B", "II-C", "III-A", "III-B"]}})

    for old_sec, new_sec in sections_map.items():
        # Update users
        res_u = await db.users.update_many({"section": old_sec}, {"$set": {"section": new_sec}})
        if res_u.modified_count > 0:
            logger.info("Updated %d users from %s to %s", res_u.modified_count, old_sec, new_sec)

        # Update sections
        res_s = await db.sections.update_many({"section_name": old_sec}, {"$set": {"section_name": new_sec}})
        if res_s.modified_count > 0:
            logger.info("Updated %d sections from %s to %s", res_s.modified_count, old_sec, new_sec)

        # Update timetables
        res_t = await db.timetables.update_many({"section": old_sec}, {"$set": {"section": new_sec}})
        if res_t.modified_count > 0:
            logger.info("Updated %d timetable records from %s to %s", res_t.modified_count, old_sec, new_sec)

        # Update sessions
        res_sess = await db.sessions.update_many({"section": old_sec}, {"$set": {"section": new_sec}})
        if res_sess.modified_count > 0:
            logger.info("Updated %d session records from %s to %s", res_sess.modified_count, old_sec, new_sec)

    logger.info("Section migration completed.")
    await close_mongo_connection()


if __name__ == "__main__":
    asyncio.run(migrate())
