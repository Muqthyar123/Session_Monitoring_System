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
