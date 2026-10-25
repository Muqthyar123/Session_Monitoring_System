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

    # 1. Admin User — the only account seeded automatically.
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

    # 2. CR & LR — NOT auto-seeded.
    # The Admin must create real CR/LR credentials via the CR/LR Management page
    # or by uploading an Excel file. Any old placeholder/dummy accounts are purged
    # so the database starts clean and the admin sees an empty CR/LR list.
    purge_result = await db.users.delete_many(
        {
            "role": {"$in": [UserRole.CR.value, UserRole.LR.value]},
            "$or": [
                {"email": {"$regex": r"^(cr|lr)\.[a-j]@college\.edu$"}},
                {"email": {"$regex": r"^(cr|lr)(@|\.cs[a-j]@)example\.com$"}},
            ],
        }
    )
    if purge_result.deleted_count > 0:
        logger.info(
            "Purged %d dummy CR/LR seed accounts. Admin must add real credentials.",
            purge_result.deleted_count,
        )
    else:
        logger.info("No dummy CR/LR placeholder accounts found — CR/LR list is already clean.")

    await close_mongo_connection()
    logger.info("Database seeding successfully completed!")


if __name__ == "__main__":
    asyncio.run(seed())
