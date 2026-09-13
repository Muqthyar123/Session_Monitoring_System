import pytest
from httpx import AsyncClient
from app.core.security import create_access_token, hash_password
from app.db.mongodb import get_database
from app.schemas.user import UserRole
from app.services.excel_service import generate_crlr_excel_template


@pytest.mark.asyncio
async def test_create_and_update_user_admin(client: AsyncClient):
    db = get_database()
    admin_res = await db.users.insert_one({
        "name": "Admin",
        "email": "admin@test.com",
        "password_hash": hash_password("pass"),
        "role": UserRole.ADMIN.value,
        "is_active": True,
    })
    token = create_access_token({"sub": str(admin_res.inserted_id), "role": "ADMIN"})
    headers = {"Authorization": f"Bearer {token}"}

    # Create CR
    create_res = await client.post(
        "/api/admin/users",
        json={
            "name": "New CR",
            "email": "newcr@test.com",
            "password": "password123",
            "role": "CR",
            "roll_number": "22A99",
            "year": "2nd Year",
            "section": "II-A",
        },
        headers=headers,
    )
    assert create_res.status_code == 201
    cr_id = create_res.json()["data"]["_id"]

    # Update CR
    update_res = await client.patch(
        f"/api/admin/users/{cr_id}",
        json={"name": "Updated CR Name"},
        headers=headers,
    )
    assert update_res.status_code == 200
    assert update_res.json()["data"]["name"] == "Updated CR Name"


@pytest.mark.asyncio
async def test_duplicate_email_or_roll_number_error(client: AsyncClient):
    db = get_database()
    admin_res = await db.users.insert_one({
        "name": "Admin",
        "email": "admin@test.com",
        "role": UserRole.ADMIN.value,
        "is_active": True,
    })
    token = create_access_token({"sub": str(admin_res.inserted_id), "role": "ADMIN"})
    headers = {"Authorization": f"Bearer {token}"}

    await db.users.insert_one({
        "name": "Existing User",
        "email": "existing@test.com",
        "roll_number": "22CS01",
        "role": UserRole.CR.value,
        "is_active": True,
    })

    # Duplicate email
    res = await client.post(
        "/api/admin/users",
        json={
            "name": "Another User",
            "email": "existing@test.com",
            "password": "password123",
            "role": "CR",
        },
        headers=headers,
    )
    assert res.status_code == 400

    # Duplicate roll number
    res2 = await client.post(
        "/api/admin/users",
        json={
            "name": "Another User",
            "email": "different@test.com",
            "roll_number": "22CS01",
            "password": "password123",
            "role": "CR",
        },
        headers=headers,
    )
    assert res2.status_code == 400


@pytest.mark.asyncio
async def test_crlr_excel_import(client: AsyncClient):
    db = get_database()
    admin_res = await db.users.insert_one({
        "name": "Admin",
        "email": "admin@test.com",
        "role": UserRole.ADMIN.value,
        "is_active": True,
    })
    token = create_access_token({"sub": str(admin_res.inserted_id), "role": "ADMIN"})
    headers = {"Authorization": f"Bearer {token}"}

    template_bytes = generate_crlr_excel_template()

    files = {
        "file": ("CR_LR_Import_Template.xlsx", template_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    }
    res = await client.post("/api/admin/users/import", files=files, headers=headers)
    assert res.status_code == 200
    summary = res.json()["data"]
    assert summary["created"] >= 1
