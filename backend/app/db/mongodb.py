import logging
import certifi
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from mongomock_motor import AsyncMongoMockClient
from app.core.config import settings
from app.core.security import hash_password

logger = logging.getLogger("fams.db")


class MongoManager:
    client = None
    db: AsyncIOMotorDatabase = None
    is_mock_mode: bool = False


db_manager = MongoManager()


async def seed_in_memory_db(db):
    """Seed initial Root Admin user into database, keeping all section, timetable, and CR/LR collections fresh."""
    now = datetime.now(timezone.utc)
    demo_pwd_hash = hash_password("demo1234")
    # Root System Administrator
    existing_admin = await db.users.find_one({"role": "ADMIN"})
    if not existing_admin:
        await db.users.insert_one(
            {
                "name": "System Administrator",
                "email": "admin@example.com",
                "password_hash": demo_pwd_hash,
                "role": "ADMIN",
                "roll_number": None,
                "phone": "9876543210",
                "year": None,
                "section": None,
                "is_active": True,
                "created_at": now,
                "updated_at": now,
            }
        )

    # Seed CR and LR dummy accounts for each section (CSE-A to CSE-J)
    sections = ["CSE-A", "CSE-B", "CSE-C", "CSE-D", "CSE-E", "CSE-F", "CSE-G", "CSE-H", "CSE-I", "CSE-J"]

    for sec in sections:
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
                    "password_hash": demo_pwd_hash,
                    "role": "CR",
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
                    "password_hash": demo_pwd_hash,
                    "role": "LR",
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

        # Upsert Section document
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


async def connect_to_mongo():
    db_name = settings.get_database_name()
    logger.info("Connecting to MongoDB at %s...", settings.MONGODB_URI)

    client_kwargs = {
        "serverSelectionTimeoutMS": settings.MONGODB_SERVER_SELECTION_TIMEOUT_MS,
    }

    if "mongodb+srv" in settings.MONGODB_URI or "tls=true" in settings.MONGODB_URI.lower():
        client_kwargs["tlsCAFile"] = certifi.where()

    # Attempt connecting to external MongoDB
    try:
        real_client = AsyncIOMotorClient(settings.MONGODB_URI, **client_kwargs)
        await real_client.admin.command("ping")
        db_manager.client = real_client
        db_manager.db = real_client[db_name]
        db_manager.is_mock_mode = False
        logger.info("MongoDB connection successful. Connected to real database: %s", db_name)
        return
    except Exception as e:
        logger.warning(
            "Primary MongoDB connection attempt failed (%s). Attempting TLS fallback...",
            str(e),
        )
        try:
            client_kwargs["tlsAllowInvalidCertificates"] = True
            real_client = AsyncIOMotorClient(settings.MONGODB_URI, **client_kwargs)
            await real_client.admin.command("ping")
            db_manager.client = real_client
            db_manager.db = real_client[db_name]
            db_manager.is_mock_mode = False
            logger.info("MongoDB connection successful with TLS options. Connected to database: %s", db_name)
            return
        except Exception as retry_err:
            logger.warning(
                "Unable to reach external MongoDB Atlas (%s). Switching to In-Memory Mock Database Mode...",
                str(retry_err),
            )

    # In-Memory Fallback Mock Database
    mock_client = AsyncMongoMockClient()
    db_manager.client = mock_client
    db_manager.db = mock_client[db_name]
    db_manager.is_mock_mode = True

    await seed_in_memory_db(db_manager.db)
    logger.info(
        "Activated In-Memory Mock Database Mode. Database '%s' seeded with admin/CR/LR accounts.",
        db_name,
    )


async def close_mongo_connection():
    if db_manager.client:
        logger.info("Closing MongoDB connection.")
        db_manager.client.close()
        logger.info("MongoDB connection closed.")


def get_database() -> AsyncIOMotorDatabase:
    if db_manager.db is None:
        raise RuntimeError("Database connection has not been initialized.")
    return db_manager.db
