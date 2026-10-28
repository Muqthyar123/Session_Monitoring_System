import logging
from urllib.parse import urlsplit

import certifi
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.errors import ConfigurationError, OperationFailure, ServerSelectionTimeoutError

from app.core.config import settings

logger = logging.getLogger("fams.db")


class MongoManager:
    client = None
    db: AsyncIOMotorDatabase | None = None


db_manager = MongoManager()


def _safe_connection_error(exc: Exception) -> str:
    if isinstance(exc, OperationFailure) and (
        exc.code == 18 or "auth" in str(exc).lower()
    ):
        return (
            "MongoDB authentication failed. Verify the Atlas Database Access "
            "username and password in MONGODB_URI."
        )
    if isinstance(exc, ServerSelectionTimeoutError):
        return (
            "MongoDB server selection timed out. Check Atlas cluster status, "
            "network access allowlist, DNS, firewall, and server availability."
        )
    if isinstance(exc, ConfigurationError):
        if "dns" in str(exc).lower() or "srv" in str(exc).lower():
            return (
                "MongoDB DNS/SRV lookup failed. Check network DNS, cluster hostname, "
                "and Atlas cluster availability."
            )
        return "MongoDB configuration is invalid. Check the URI scheme and percent-encoding."
    return "MongoDB connection failed. Check MONGODB_URI and Atlas availability."


async def connect_to_mongo():
    """Connect once to the configured MongoDB database and verify it with ping."""
    previous_client = db_manager.client
    db_manager.client = None
    db_manager.db = None
    if previous_client is not None:
        previous_client.close()

    uri = settings.MONGODB_URI
    db_name = settings.DATABASE_NAME
    mongo_host = urlsplit(uri).hostname or "configured MongoDB host"
    logger.info("Connecting to MongoDB host %s, database %s...", mongo_host, db_name)

    client_kwargs = {
        "serverSelectionTimeoutMS": settings.MONGODB_SERVER_SELECTION_TIMEOUT_MS,
    }
    # Atlas SRV connections require TLS. Keep certificate verification enabled.
    if uri.lower().startswith("mongodb+srv://") or "tls=true" in uri.lower():
        client_kwargs["tlsCAFile"] = certifi.where()

    client = None
    try:
        client = AsyncIOMotorClient(uri, **client_kwargs)
        await client.admin.command("ping")
    except Exception as exc:
        if client is not None:
            client.close()
        logger.error("MongoDB connection failed (%s).", type(exc).__name__)
        raise RuntimeError(_safe_connection_error(exc)) from None

    db_manager.client = client
    db_manager.db = client[db_name]
    logger.info("MongoDB ping succeeded. Connected to configured database %s.", db_name)


async def close_mongo_connection():
    client = db_manager.client
    db_manager.client = None
    db_manager.db = None
    if client:
        logger.info("Closing MongoDB connection.")
        client.close()
        logger.info("MongoDB connection closed.")


def get_database() -> AsyncIOMotorDatabase:
    if db_manager.db is None:
        raise RuntimeError("Database connection has not been initialized.")
    return db_manager.db
