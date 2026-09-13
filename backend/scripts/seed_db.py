import asyncio
import logging
from datetime import datetime, timezone
import sys
import os

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.security import hash_password
from app.db.indexes import create_db_indexes
from app.db.mongodb import close_mongo_connection, connect_to_mongo, get_database
from app.schemas.user import UserRole

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seed_db")


async def seed():
    logger.info("Starting database seeding process...")
    await connect_to_mongo()
    await create_db_indexes()
    db = get_database()

    now = datetime.now(timezone.utc)
    demo_pass_hash = hash_password("demo1234")

    # 1. Admin User
    admin = await db.users.find_one({"email": "admin@example.com"})
    if not admin:
        res = await db.users.insert_one(
            {
                "name": "System Administrator",
                "email": "admin@example.com",
                "password_hash": demo_pass_hash,
                "role": UserRole.ADMIN.value,
                "roll_number": None,
                "phone": "9876543210",
                "year": None,
                "section": None,
                "is_active": True,
                "created_at": now,
                "updated_at": now,
            }
        )
        admin_id = str(res.inserted_id)
        logger.info("Created Admin User: admin@example.com / demo1234 (ID: %s)", admin_id)
    else:
        logger.info("Admin user already exists.")

    # 2. CR User
    cr_user = await db.users.find_one({"email": "cr@example.com"})
    if not cr_user:
        res = await db.users.insert_one(
            {
                "name": "Rahul Kumar (CR)",
                "email": "cr@example.com",
                "password_hash": demo_pass_hash,
                "role": UserRole.CR.value,
                "roll_number": "22CS2A01",
                "phone": "9876543211",
                "year": "2nd Year",
                "section": "II-A",
                "is_active": True,
                "created_at": now,
                "updated_at": now,
            }
        )
        cr_id = str(res.inserted_id)
        logger.info("Created CR User: cr@example.com / demo1234 (ID: %s)", cr_id)
    else:
        cr_id = str(cr_user["_id"])
        logger.info("CR user already exists.")

    # 3. LR User
    lr_user = await db.users.find_one({"email": "lr@example.com"})
    if not lr_user:
        res = await db.users.insert_one(
            {
                "name": "Sneha Sharma (LR)",
                "email": "lr@example.com",
                "password_hash": demo_pass_hash,
                "role": UserRole.LR.value,
                "roll_number": "22CS2A02",
                "phone": "9876543212",
                "year": "2nd Year",
                "section": "II-A",
                "is_active": True,
                "created_at": now,
                "updated_at": now,
            }
        )
        lr_id = str(res.inserted_id)
        logger.info("Created LR User: lr@example.com / demo1234 (ID: %s)", lr_id)
    else:
        lr_id = str(lr_user["_id"])
        logger.info("LR user already exists.")

    # 4. Sections
    sections = [
        {"year": "2nd Year", "section_name": "II-A", "assigned_cr_id": cr_id, "assigned_lr_id": lr_id},
        {"year": "2nd Year", "section_name": "II-B", "assigned_cr_id": None, "assigned_lr_id": None},
        {"year": "2nd Year", "section_name": "II-C", "assigned_cr_id": None, "assigned_lr_id": None},
        {"year": "3rd Year", "section_name": "III-A", "assigned_cr_id": None, "assigned_lr_id": None},
        {"year": "3rd Year", "section_name": "III-B", "assigned_cr_id": None, "assigned_lr_id": None},
    ]

    for sec in sections:
        await db.sections.update_one(
            {"section_name": sec["section_name"]},
            {
                "$set": {
                    "year": sec["year"],
                    "section_name": sec["section_name"],
                    "assigned_cr_id": sec["assigned_cr_id"],
                    "assigned_lr_id": sec["assigned_lr_id"],
                    "is_active": True,
                    "updated_at": now,
                },
                "$setOnInsert": {"created_at": now},
            },
            upsert=True,
        )
    logger.info("Seeded %d sample sections.", len(sections))

    # 5. Timetable Data (Monday to Saturday for II-A with continuous DBMS session)
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    sample_timetable = []

    for d in days:
        # Period 1, 2, 3 DBMS continuous session (09:10 to 11:40)
        sample_timetable.extend([
            {"year": "2nd Year", "section": "II-A", "day": d, "period": 1, "start_time": "09:10", "end_time": "10:00", "subject": "Database Management Systems", "faculty": "Dr. A. Sharma", "room": "B-204"},
            {"year": "2nd Year", "section": "II-A", "day": d, "period": 2, "start_time": "10:00", "end_time": "10:50", "subject": "Database Management Systems", "faculty": "Dr. A. Sharma", "room": "B-204"},
            {"year": "2nd Year", "section": "II-A", "day": d, "period": 3, "start_time": "10:50", "end_time": "11:40", "subject": "Database Management Systems", "faculty": "Dr. A. Sharma", "room": "B-204"},
            {"year": "2nd Year", "section": "II-A", "day": d, "period": 4, "start_time": "11:40", "end_time": "12:30", "subject": "Operating Systems", "faculty": "Prof. R. Verma", "room": "B-205"},
            {"year": "2nd Year", "section": "II-A", "day": d, "period": 5, "start_time": "13:20", "end_time": "14:10", "subject": "Computer Networks", "faculty": "Dr. K. Patel", "room": "C-101"},
        ])

    for t in sample_timetable:
        await db.timetables.update_one(
            {"section": t["section"], "day": t["day"], "period": t["period"]},
            {"$set": {**t, "updated_at": now}},
            upsert=True,
        )

    logger.info("Seeded sample timetable for section II-A.")
    await close_mongo_connection()
    logger.info("Database seeding successfully completed!")


if __name__ == "__main__":
    asyncio.run(seed())
