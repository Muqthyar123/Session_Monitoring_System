import asyncio
import re
from urllib.parse import unquote, urlsplit

import certifi
from app.core.config import settings
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ConfigurationError, OperationFailure, PyMongoError, ServerSelectionTimeoutError


def safe_failure_category(exc: Exception) -> str:
    """Return a useful category without printing the exception or URI."""
    if isinstance(exc, OperationFailure) and (
        exc.code == 18 or "auth" in str(exc).lower()
    ):
        return "Authentication rejected: verify the Atlas Database Access username and password."
    if isinstance(exc, ServerSelectionTimeoutError):
        return "Server selection timed out: check DNS, network access/IP allowlist, firewall, and cluster status."
    if isinstance(exc, ConfigurationError):
        return "Invalid MongoDB URI configuration: check scheme and percent-encoding."
    return "MongoDB connection failed: check the configured URI and Atlas availability."


async def main():
    uri = settings.MONGODB_URI
    parsed = urlsplit(uri)
    print("MongoDB host:", parsed.hostname or "missing")
    print("MongoDB username:", unquote(parsed.username or "missing"))
    print("MongoDB database:", settings.DATABASE_NAME)
    raw_userinfo = parsed.netloc.rsplit("@", 1)[0]
    raw_password = raw_userinfo.partition(":")[2]
    malformed_escape = bool(re.search(r"%(?![0-9A-Fa-f]{2})", raw_password))
    unescaped_reserved = any(char in raw_password for char in ":/?#[]@")
    print(
        "MongoDB password URI encoding:",
        "check required" if malformed_escape or unescaped_reserved else "no malformed escapes or raw reserved characters detected",
    )

    options = {"serverSelectionTimeoutMS": settings.MONGODB_SERVER_SELECTION_TIMEOUT_MS}
    if uri.lower().startswith("mongodb+srv://") or "tls=true" in uri.lower():
        options["tlsCAFile"] = certifi.where()
    client = None
    try:
        client = AsyncIOMotorClient(uri, **options)
        await client.admin.command("ping")
        print("MongoDB connection status: ping succeeded")
    except PyMongoError as exc:
        print("MongoDB connection status: failed")
        print("Diagnostic:", safe_failure_category(exc))
        raise SystemExit(1) from None
    finally:
        if client is not None:
            client.close()


if __name__ == "__main__":
    asyncio.run(main())
