import logging
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.core.config import settings

logger = logging.getLogger("fams.db")


class MongoManager:
    client: AsyncIOMotorClient = None
    db: AsyncIOMotorDatabase = None


db_manager = MongoManager()


async def connect_to_mongo():
    db_name = settings.get_database_name()
    logger.info("Connecting to MongoDB at %s...", settings.MONGODB_URI)
    
    # Initialize Motor client with fast timeout
    db_manager.client = AsyncIOMotorClient(
        settings.MONGODB_URI,
        serverSelectionTimeoutMS=settings.MONGODB_SERVER_SELECTION_TIMEOUT_MS,
    )

    # Explicitly verify connection using lightweight ping command
    try:
        await db_manager.client.admin.command("ping")
        db_manager.db = db_manager.client[db_name]
        logger.info("MongoDB connection successful. Connected to database: %s", db_name)
    except Exception as e:
        logger.error("Unable to connect to MongoDB at %s: %s", settings.MONGODB_URI, str(e))
        raise RuntimeError(
            f"Unable to connect to MongoDB at {settings.MONGODB_URI}: {str(e)}"
        ) from e


async def close_mongo_connection():
    if db_manager.client:
        logger.info("Closing MongoDB connection.")
        db_manager.client.close()
        logger.info("MongoDB connection closed.")


def get_database() -> AsyncIOMotorDatabase:
    if db_manager.db is None:
        raise RuntimeError("Database connection has not been initialized.")
    return db_manager.db
