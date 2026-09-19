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

    # 2. CR & LR Users for each section (CSE-A to CSE-J)
    sections_list = ["CSE-A", "CSE-B", "CSE-C", "CSE-D", "CSE-E", "CSE-F", "CSE-G", "CSE-H", "CSE-I", "CSE-J"]

    for sec in sections_list:
        slug = sec.replace("-", "").lower()
        cr_email = "cr@example.com" if sec == "CSE-A" else f"cr.{slug}@example.com"
        lr_email = "lr@example.com" if sec == "CSE-A" else f"lr.{slug}@example.com"
        sec_letter = sec.split("-")[-1]

        # CR User
        cr_existing = await db.users.find_one({"email": cr_email})
        if not cr_existing:
            cr_res = await db.users.insert_one(
                {
                    "name": f"{sec} CR",
                    "email": cr_email,
                    "password_hash": demo_pass_hash,
                    "role": UserRole.CR.value,
                    "roll_number": f"22CS{sec_letter}01",
                    "phone": "9876543211",
                    "year": "2nd Year",
                    "section": sec,
                    "is_active": True,
                    "created_at": now,
                    "updated_at": now,
                }
            )
            cr_id = str(cr_res.inserted_id)
        else:
            cr_id = str(cr_existing["_id"])

        # LR User
        lr_existing = await db.users.find_one({"email": lr_email})
        if not lr_existing:
            lr_res = await db.users.insert_one(
                {
                    "name": f"{sec} LR",
                    "email": lr_email,
                    "password_hash": demo_pass_hash,
                    "role": UserRole.LR.value,
                    "roll_number": f"22CS{sec_letter}02",
                    "phone": "9876543212",
                    "year": "2nd Year",
                    "section": sec,
                    "is_active": True,
                    "created_at": now,
                    "updated_at": now,
                }
            )
            lr_id = str(lr_res.inserted_id)
        else:
            lr_id = str(lr_existing["_id"])

        # Section record
        await db.sections.update_one(
            {"section_name": sec},
            {
                "$set": {
                    "year": "2nd Year",
                    "section_name": sec,
                    "assigned_cr_id": cr_id,
                    "assigned_lr_id": lr_id,
                    "is_active": True,
                    "updated_at": now,
                },
                "$setOnInsert": {"created_at": now},
            },
            upsert=True,
        )
    logger.info("Seeded CR & LR accounts and section records for %d sections.", len(sections_list))

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
