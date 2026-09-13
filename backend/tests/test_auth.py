import pytest
from httpx import AsyncClient
from app.core.security import hash_password
from app.db.mongodb import get_database
from app.schemas.user import UserRole


@pytest.mark.asyncio
async def test_valid_admin_and_crlr_login(client: AsyncClient):
    db = get_database()
    pass_hash = hash_password("secret123")

    # Create admin and CR user
    await db.users.insert_one({
        "name": "Admin Test",
        "email": "admin@test.com",
        "password_hash": pass_hash,
        "role": UserRole.ADMIN.value,
        "is_active": True,
    })
    await db.users.insert_one({
        "name": "CR Test",
        "email": "cr@test.com",
        "password_hash": pass_hash,
        "role": UserRole.CR.value,
        "section": "II-A",
        "year": "2nd Year",
        "is_active": True,
    })

    # Test Admin Login
    res = await client.post("/api/auth/login", json={"email": "admin@test.com", "password": "secret123", "portal": "ADMIN"})
    assert res.status_code == 200
    json_data = res.json()
    assert json_data["success"] is True
    assert json_data["data"]["user"]["role"] == "ADMIN"
    assert "access_token" in json_data["data"]

    # Test CR Login
    res2 = await client.post("/api/auth/login", json={"email": "cr@test.com", "password": "secret123", "portal": "CRLR"})
    assert res2.status_code == 200
    json2 = res2.json()
    assert json2["data"]["user"]["role"] == "CR"
    assert json2["data"]["user"]["section"] == "II-A"


@pytest.mark.asyncio
async def test_invalid_password_returns_401(client: AsyncClient):
    db = get_database()
    await db.users.insert_one({
        "name": "User Test",
        "email": "user@test.com",
        "password_hash": hash_password("secret123"),
        "role": UserRole.CR.value,
        "is_active": True,
    })

    res = await client.post("/api/auth/login", json={"email": "user@test.com", "password": "wrongpassword"})
    assert res.status_code == 401
    assert res.json()["success"] is False


@pytest.mark.asyncio
async def test_inactive_user_login_fails(client: AsyncClient):
    db = get_database()
    await db.users.insert_one({
        "name": "Disabled User",
        "email": "disabled@test.com",
        "password_hash": hash_password("secret123"),
        "role": UserRole.CR.value,
        "is_active": False,
    })

    res = await client.post("/api/auth/login", json={"email": "disabled@test.com", "password": "secret123"})
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_portal_mismatch_returns_403(client: AsyncClient):
    db = get_database()
    await db.users.insert_one({
        "name": "CR User",
        "email": "cruser@test.com",
        "password_hash": hash_password("secret123"),
        "role": UserRole.CR.value,
        "is_active": True,
    })

    # CR attempting to login via ADMIN portal
    res = await client.post("/api/auth/login", json={"email": "cruser@test.com", "password": "secret123", "portal": "ADMIN"})
    assert res.status_code == 403
