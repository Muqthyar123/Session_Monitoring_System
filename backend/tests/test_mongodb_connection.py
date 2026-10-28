import pytest
from pydantic import ValidationError
from pymongo.errors import ConfigurationError, OperationFailure, ServerSelectionTimeoutError

from app.core.config import BASE_DIR, Settings, settings
from app.db import mongodb
from app.db import indexes
from app.db.mongodb import db_manager


def test_settings_use_repository_root_env_and_explicit_database():
    assert settings.model_config["env_file"] == str(BASE_DIR.parent / ".env")
    assert settings.get_database_name() == settings.DATABASE_NAME


def test_process_environment_overrides_the_env_file(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "MONGODB_URI=mongodb://file-user:file-pass@file.example/filedb\n"
        "DATABASE_NAME=file_db\n"
        f"JWT_SECRET_KEY={'f' * 40}\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("MONGODB_URI", "mongodb://env-user:env-pass@env.example/envdb")
    monkeypatch.setenv("DATABASE_NAME", "env_db")
    monkeypatch.setenv("JWT_SECRET_KEY", "e" * 40)

    loaded = Settings(_env_file=env_file)
    assert loaded.MONGODB_URI.endswith("envdb")
    assert loaded.DATABASE_NAME == "env_db"


def test_settings_reject_missing_mongodb_uri_and_weak_jwt_secret():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, DATABASE_NAME="isolated", JWT_SECRET_KEY="x" * 32)
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            MONGODB_URI="https://example.invalid",
            DATABASE_NAME="isolated",
            JWT_SECRET_KEY="x" * 32,
        )
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            MONGODB_URI="mongodb://localhost",
            DATABASE_NAME="isolated",
            JWT_SECRET_KEY="short",
        )
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            MONGODB_URI="mongodb://test-user:raw@password@localhost/test",
            DATABASE_NAME="isolated",
            JWT_SECRET_KEY="x" * 32,
        )
    encoded = Settings(
        _env_file=None,
        MONGODB_URI="mongodb://test-user:encoded%40password@localhost/test",
        DATABASE_NAME="isolated",
        JWT_SECRET_KEY="x" * 32,
    )
    assert encoded.MONGODB_URI.endswith("/test")


class FakeClient:
    def __init__(self, uri, *, error=None, **kwargs):
        self.uri = uri
        self.error = error
        self.kwargs = kwargs
        self.closed = False
        self.admin = self

    async def command(self, name):
        assert name == "ping"
        if self.error:
            raise self.error
        return {"ok": 1}

    def __getitem__(self, name):
        return {"name": name}

    def close(self):
        self.closed = True


@pytest.mark.asyncio
async def test_connect_uses_one_configured_client_and_database(monkeypatch):
    created = []

    def client_factory(uri, **kwargs):
        client = FakeClient(uri, **kwargs)
        created.append(client)
        return client

    monkeypatch.setattr(mongodb, "AsyncIOMotorClient", client_factory)
    monkeypatch.setattr(settings, "MONGODB_URI", "mongodb://user:secret@db.example/test")
    monkeypatch.setattr(settings, "DATABASE_NAME", "configured_test_db")

    await mongodb.connect_to_mongo()
    assert len(created) == 1
    assert created[0].uri == settings.MONGODB_URI
    assert db_manager.db == {"name": "configured_test_db"}
    assert db_manager.client is created[0]

    await mongodb.close_mongo_connection()
    assert created[0].closed is True
    assert db_manager.client is None
    assert db_manager.db is None


@pytest.mark.asyncio
async def test_authentication_failure_is_safe_and_does_not_fallback(monkeypatch):
    client = FakeClient("mongodb://user:secret@db.example/test", error=OperationFailure("bad auth", code=8000))
    monkeypatch.setattr(mongodb, "AsyncIOMotorClient", lambda *args, **kwargs: client)
    monkeypatch.setattr(settings, "MONGODB_URI", "mongodb://user:secret@db.example/test")

    with pytest.raises(RuntimeError, match="authentication failed") as error:
        await mongodb.connect_to_mongo()

    assert "secret" not in str(error.value)
    assert client.closed is True
    assert db_manager.db is None
    assert db_manager.client is None


def test_connection_errors_have_safe_categories():
    auth = mongodb._safe_connection_error(OperationFailure("bad auth", code=8000))
    timeout = mongodb._safe_connection_error(ServerSelectionTimeoutError("timed out"))
    dns = mongodb._safe_connection_error(ConfigurationError("DNS query failed"))
    assert "authentication failed" in auth.lower()
    assert "secret" not in auth
    assert "timed out" in timeout.lower()
    assert "dns/srv" in dns.lower()


class FakeCursor:
    def __init__(self, rows):
        self.rows = rows

    async def to_list(self, length):
        return self.rows[:length]


class FakeIndexCollection:
    def __init__(self, duplicate_rows=None):
        self.info = {"legacy_1": {"key": [("roll_number", 1)]}}
        self.duplicate_rows = duplicate_rows or []
        self.dropped = []
        self.created = []

    async def index_information(self):
        return self.info

    def aggregate(self, pipeline):
        return FakeCursor(self.duplicate_rows)

    async def drop_index(self, name):
        self.dropped.append(name)
        self.info.pop(name)

    async def create_index(self, keys, **options):
        self.created.append((keys, options))
        return "roll_number_1"


@pytest.mark.asyncio
async def test_unique_index_migration_preserves_data_and_replaces_legacy_index():
    collection = FakeIndexCollection()
    await indexes._ensure_index(collection, [("roll_number", 1)], unique=True)
    assert collection.dropped == ["legacy_1"]
    assert collection.created == [([( "roll_number", 1)], {"unique": True})]


@pytest.mark.asyncio
async def test_unique_index_migration_stops_when_existing_duplicates_are_found():
    collection = FakeIndexCollection(duplicate_rows=[{"_id": "duplicate-key", "count": 2}])
    with pytest.raises(RuntimeError, match="Duplicate documents"):
        await indexes._ensure_index(collection, [("roll_number", 1)], unique=True)
    assert collection.dropped == []
    assert collection.created == []
