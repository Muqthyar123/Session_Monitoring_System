"""Opt-in real Atlas API CRUD test for a separately provisioned test database.

Set MONGODB_TEST_DATABASE_NAME to a database name distinct from DATABASE_NAME
to run this test. The test cleans up only the unique documents it creates and
never drops collections or databases.
"""

import os
from uuid import uuid4

import pytest

from app.core.config import settings
from app.db.indexes import create_db_indexes
from app.db.mongodb import close_mongo_connection, connect_to_mongo, get_database
from app.schemas.user import UserRole
from app.services.admin_provisioning import create_first_admin


@pytest.mark.asyncio
async def test_real_atlas_student_api_crud(client, monkeypatch):
    test_database_name = os.getenv("MONGODB_TEST_DATABASE_NAME", "").strip()
    if not test_database_name:
        pytest.skip("Set MONGODB_TEST_DATABASE_NAME to an isolated Atlas test database.")
    if test_database_name == settings.DATABASE_NAME:
        pytest.fail("MONGODB_TEST_DATABASE_NAME must not equal the configured application database.")

    monkeypatch.setattr(settings, "DATABASE_NAME", test_database_name)
    suffix = uuid4().hex
    admin_email = f"atlas-integration-{suffix}@example.invalid"
    admin_password = f"{suffix[:8]}A!"
    roll_number = f"IT{suffix[:16].upper()}"
    await connect_to_mongo()
    db = get_database()
    try:
        await create_db_indexes()
        await create_first_admin(
            db, admin_email, "Atlas Integration Test Administrator", admin_password
        )
        seeded_admin = await db.users.find_one({"email": admin_email})
        assert seeded_admin is not None
        assert seeded_admin["role"] == UserRole.ADMIN.value
        assert seeded_admin["password_hash"] != admin_password

        login = await client.post(
            "/api/auth/login",
            json={"email": admin_email, "password": admin_password, "portal": "ADMIN"},
        )
        assert login.status_code == 200, login.text
        assert login.json()["data"]["user"]["role"] == UserRole.ADMIN.value
        token = login.json()["data"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        protected = await client.get("/api/admin/students", headers=headers)
        assert protected.status_code == 200, protected.text

        created = await client.post(
            "/api/admin/students",
            headers=headers,
            json={
                "name": "Atlas CRUD Integration Student",
                "rollNumber": roll_number,
                "year": "2nd Year",
                "branch": "CSE",
                "section": "A",
            },
        )
        assert created.status_code == 201, created.text
        student_id = created.json()["data"]["id"]
        persisted = await db.students.find_one({"roll_number": roll_number})
        assert persisted is not None
        assert persisted["name"] == "Atlas CRUD Integration Student"

        fetched = await client.get(
            f"/api/admin/students?search={roll_number}", headers=headers
        )
        assert fetched.status_code == 200, fetched.text
        assert any(item["id"] == student_id for item in fetched.json()["data"])

        updated = await client.patch(
            f"/api/admin/students/{student_id}",
            headers=headers,
            json={"name": "Atlas CRUD Integration Student Updated"},
        )
        assert updated.status_code == 200, updated.text
        persisted = await db.students.find_one({"roll_number": roll_number})
        assert persisted is not None
        assert persisted["name"] == "Atlas CRUD Integration Student Updated"

        await close_mongo_connection()
        await connect_to_mongo()
        db = get_database()
        persisted_after_reconnect = await db.students.find_one({"roll_number": roll_number})
        assert persisted_after_reconnect is not None
        assert persisted_after_reconnect["name"] == "Atlas CRUD Integration Student Updated"

        deleted = await client.delete(
            f"/api/admin/students/{student_id}", headers=headers
        )
        assert deleted.status_code == 200, deleted.text
        assert await db.students.find_one({"roll_number": roll_number}) is None
    finally:
        await db.students.delete_one({"roll_number": roll_number})
        seeded_admin = await db.users.find_one({"email": admin_email})
        if seeded_admin:
            await db.audit_logs.delete_many({"actor_id": str(seeded_admin["_id"])})
            await db.users.delete_one({"_id": seeded_admin["_id"]})
        await close_mongo_connection()
