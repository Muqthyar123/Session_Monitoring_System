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

    # 2. CR & LR Users for each section (II-CSE-A to II-CSE-J)
    # Default password for each CR/LR is their roll number (e.g. 22CSA01).
    # Login can be done with email OR roll number.
    sections_list = ["II-CSE-A", "II-CSE-B", "II-CSE-C", "II-CSE-D", "II-CSE-E", "II-CSE-F", "II-CSE-G", "II-CSE-H", "II-CSE-I", "II-CSE-J"]

    for sec in sections_list:
        sec_letter = sec.split("-")[-1]
        slug = sec_letter.lower()

        cr_roll = f"22CS{sec_letter}01"
        lr_roll = f"22CS{sec_letter}02"
        cr_email = f"cr.{slug}@college.edu"
        lr_email = f"lr.{slug}@college.edu"

        # Password = roll number (unique per CR/LR)
        cr_pwd_hash = hash_password(cr_roll)
        lr_pwd_hash = hash_password(lr_roll)

        # CR User — insert if absent, migrate if stale
        cr_existing = await db.users.find_one(
            {"$or": [{"email": cr_email}, {"roll_number": cr_roll, "role": UserRole.CR.value}]}
        )
        if not cr_existing:
            cr_res = await db.users.insert_one(
                {
                    "name": f"{sec} CR",
                    "email": cr_email,
                    "password_hash": cr_pwd_hash,
                    "role": UserRole.CR.value,
                    "roll_number": cr_roll,
                    "phone": "9876543211",
                    "year": "2nd Year",
                    "section": sec,
                    "is_active": True,
                    "created_at": now,
                    "updated_at": now,
                }
            )
            cr_id = str(cr_res.inserted_id)
            logger.info("Created CR user: %s / %s", cr_email, cr_roll)
        else:
            cr_id = str(cr_existing["_id"])
            update_fields: dict = {"email": cr_email, "section": sec, "updated_at": now}
            if cr_existing.get("password_hash") == hash_password("demo1234"):
                update_fields["password_hash"] = cr_pwd_hash
                logger.info("Migrated CR %s password to roll number", cr_roll)
            await db.users.update_one({"_id": cr_existing["_id"]}, {"$set": update_fields})

        # LR User — insert if absent, migrate if stale
        lr_existing = await db.users.find_one(
            {"$or": [{"email": lr_email}, {"roll_number": lr_roll, "role": UserRole.LR.value}]}
        )
        if not lr_existing:
            lr_res = await db.users.insert_one(
                {
                    "name": f"{sec} LR",
                    "email": lr_email,
                    "password_hash": lr_pwd_hash,
                    "role": UserRole.LR.value,
                    "roll_number": lr_roll,
                    "phone": "9876543212",
                    "year": "2nd Year",
                    "section": sec,
                    "is_active": True,
                    "created_at": now,
                    "updated_at": now,
                }
            )
            lr_id = str(lr_res.inserted_id)
            logger.info("Created LR user: %s / %s", lr_email, lr_roll)
        else:
            lr_id = str(lr_existing["_id"])
            update_fields = {"email": lr_email, "section": sec, "updated_at": now}
            if lr_existing.get("password_hash") == hash_password("demo1234"):
                update_fields["password_hash"] = lr_pwd_hash
                logger.info("Migrated LR %s password to roll number", lr_roll)
            await db.users.update_one({"_id": lr_existing["_id"]}, {"$set": update_fields})

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
