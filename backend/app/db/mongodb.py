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
    """Seed initial demo users, sections, and timetables into in-memory mock database."""
    now = datetime.now(timezone.utc)
    demo_pwd_hash = hash_password("demo1234")

    # 1. Admin
    admin_res = await db.users.insert_one(
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
    admin_id = str(admin_res.inserted_id)

    # 2. CR User
    cr_res = await db.users.insert_one(
        {
            "name": "Rahul Kumar (CR)",
            "email": "cr@example.com",
            "password_hash": demo_pwd_hash,
            "role": "CR",
            "roll_number": "22CS2A01",
            "phone": "9876543211",
            "year": "2nd Year",
            "section": "II-A",
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )
    cr_id = str(cr_res.inserted_id)

    # 3. LR User
    lr_res = await db.users.insert_one(
        {
            "name": "Sneha Sharma (LR)",
            "email": "lr@example.com",
            "password_hash": demo_pwd_hash,
            "role": "LR",
            "roll_number": "22CS2A02",
            "phone": "9876543212",
            "year": "2nd Year",
            "section": "II-A",
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )
    lr_id = str(lr_res.inserted_id)

    # 4. Sections
    sections = [
        {"year": "2nd Year", "section_name": "II-A", "assigned_cr_id": cr_id, "assigned_lr_id": lr_id},
        {"year": "2nd Year", "section_name": "II-B", "assigned_cr_id": None, "assigned_lr_id": None},
        {"year": "2nd Year", "section_name": "II-C", "assigned_cr_id": None, "assigned_lr_id": None},
        {"year": "3rd Year", "section_name": "III-A", "assigned_cr_id": None, "assigned_lr_id": None},
        {"year": "3rd Year", "section_name": "III-B", "assigned_cr_id": None, "assigned_lr_id": None},
    ]
    for s in sections:
        await db.sections.insert_one({**s, "is_active": True, "created_at": now, "updated_at": now})

    # 5. Timetables
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    for d in days:
        sample_periods = [
            {"year": "2nd Year", "section": "II-A", "day": d, "period": 1, "start_time": "09:10", "end_time": "10:00", "subject": "Database Management Systems", "faculty": "Dr. A. Sharma", "room": "B-204"},
            {"year": "2nd Year", "section": "II-A", "day": d, "period": 2, "start_time": "10:00", "end_time": "10:50", "subject": "Database Management Systems", "faculty": "Dr. A. Sharma", "room": "B-204"},
            {"year": "2nd Year", "section": "II-A", "day": d, "period": 3, "start_time": "10:50", "end_time": "11:40", "subject": "Database Management Systems", "faculty": "Dr. A. Sharma", "room": "B-204"},
            {"year": "2nd Year", "section": "II-A", "day": d, "period": 4, "start_time": "11:40", "end_time": "12:30", "subject": "Operating Systems", "faculty": "Prof. R. Verma", "room": "B-205"},
            {"year": "2nd Year", "section": "II-A", "day": d, "period": 5, "start_time": "13:20", "end_time": "14:10", "subject": "Computer Networks", "faculty": "Dr. K. Patel", "room": "C-101"},
        ]
        for p in sample_periods:
            await db.timetables.insert_one({**p, "updated_at": now})


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
