import pytest
from httpx import AsyncClient
from app.core.security import create_access_token, hash_password
from app.db.mongodb import get_database
from app.schemas.user import UserRole


@pytest.mark.asyncio
async def test_create_update_delete_student(client: AsyncClient):
    db = get_database()
    admin_res = await db.users.insert_one({
        "name": "Admin",
        "email": "admin@test.com",
        "role": UserRole.ADMIN.value,
        "is_active": True,
    })
    token = create_access_token({"sub": str(admin_res.inserted_id), "role": "ADMIN"})
    headers = {"Authorization": f"Bearer {token}"}

    # Create Student
    create_res = await client.post(
        "/api/admin/students",
        json={
            "name": "John Doe",
            "rollNumber": "21001A0501",
            "year": "2nd Year",
            "section": "CSE-A",
            "studentPhone": "9876543210",
        },
        headers=headers,
    )
    assert create_res.status_code == 201
    student_id = create_res.json()["data"]["_id"]
    assert student_id is not None

    # Update Student by ID
    update_res = await client.patch(
        f"/api/admin/students/{student_id}",
        json={"name": "John Doe Updated"},
        headers=headers,
    )
    assert update_res.status_code == 200
    assert update_res.json()["data"]["name"] == "John Doe Updated"

    # Update Student by Roll Number
    update_roll_res = await client.patch(
        "/api/admin/students/21001A0501",
        json={"name": "John Doe Final"},
        headers=headers,
    )
    assert update_roll_res.status_code == 200
    assert update_roll_res.json()["data"]["name"] == "John Doe Final"

    # Delete Student by Roll Number or ID
    delete_res = await client.delete(
        f"/api/admin/students/21001A0501",
        headers=headers,
    )
    assert delete_res.status_code == 200
    assert delete_res.json()["success"] is True
