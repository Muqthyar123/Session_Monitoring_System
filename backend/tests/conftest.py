from typing import AsyncGenerator
import pytest
from httpx import ASGITransport, AsyncClient
from mongomock_motor import AsyncMongoMockClient
from app.db.mongodb import db_manager

TEST_DB_NAME = "test_college_session_monitoring"


@pytest.fixture(autouse=True)
async def setup_test_database():
    """Use in-memory mongomock_motor client for ultra-fast, isolated tests."""
    db_manager.client = AsyncMongoMockClient()
    db_manager.db = db_manager.client[TEST_DB_NAME]
    yield


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app_instance)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


from app.main import app as app_instance
