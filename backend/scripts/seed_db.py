import asyncio
import getpass
import logging
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.security import hash_password
from app.db.indexes import create_db_indexes
from app.db.mongodb import close_mongo_connection, connect_to_mongo, get_database
from app.schemas.user import UserRole

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seed_admin")


def prompt_admin_credentials():
    email = input("Initial administrator email: ").strip().lower()
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
        raise ValueError("Enter a valid administrator email address.")
    password = getpass.getpass("Initial administrator password (12+ characters): ")
    confirm = getpass.getpass("Confirm password: ")
    if len(password) < 12:
        raise ValueError("Administrator password must be at least 12 characters.")
    if password != confirm:
        raise ValueError("Passwords do not match.")
    return email, password


async def seed():
    await connect_to_mongo()
    try:
        await create_db_indexes()
        db = get_database()
        existing_admin = await db.users.find_one({"role": UserRole.ADMIN.value})
        if existing_admin:
            logger.info("An administrator already exists; no records were changed.")
            return

        email, password = prompt_admin_credentials()
        now = datetime.now(timezone.utc)
        await db.users.insert_one({
            "name": input("Administrator name: ").strip() or "System Administrator",
            "email": email,
            "password_hash": hash_password(password),
            "role": UserRole.ADMIN.value,
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        })
        logger.info("Initial administrator created. No password was logged or returned.")
    finally:
        await close_mongo_connection()


if __name__ == "__main__":
    asyncio.run(seed())
