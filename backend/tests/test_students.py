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


@pytest.mark.asyncio
async def test_batch_year_calculation_and_crlr_mapping(client: AsyncClient):
    db = get_database()
    admin_res = await db.users.insert_one({
        "name": "Admin",
        "email": "admin2@test.com",
        "role": UserRole.ADMIN.value,
        "is_active": True,
    })
    token = create_access_token({"sub": str(admin_res.inserted_id), "role": "ADMIN"})
    headers = {"Authorization": f"Bearer {token}"}

    # Create CR/LR user for 2nd Year Section J
    crlr_res = await db.users.insert_one({
        "name": "CR Student J",
        "email": "cr.j@test.com",
        "role": UserRole.CR.value,
        "year": "2nd Year",
        "section": "CSE-J",
        "is_active": True,
    })

    # Create Student with Batch 2029 and Section J (without year)
    create_res = await client.post(
        "/api/admin/students",
        json={
            "name": "BODAPATI PALLAVI",
            "rollNumber": "24471A0575",
            "branch": "CSE",
            "batch": 2029,
            "section": "J",
            "studentPhone": "9505371832",
            "parentPhone": "9642648130",
        },
        headers=headers,
    )
    assert create_res.status_code == 201
    data = create_res.json()["data"]
    assert data["batch"] == 2029
    assert data["year"] == "2nd Year"
    assert data["branch"] == "CSE"
    assert (data.get("crlrId") or data.get("crlr_id")) == str(crlr_res.inserted_id)
    assert (data.get("crlrName") or data.get("crlr_name")) == "CR Student J"

    # Test CR/LR listing scope: calling student list filtered for 2nd Year / CSE-J
    crlr_token = create_access_token({"sub": str(crlr_res.inserted_id), "role": "CR"})
    crlr_headers = {"Authorization": f"Bearer {crlr_token}"}
    crlr_students_res = await client.get("/api/crlr/students", headers=crlr_headers)
    assert crlr_students_res.status_code == 200
    stu_list = crlr_students_res.json()["data"]
    assert len(stu_list) >= 1
    assert any(s["rollNumber"] == "24471A0575" for s in stu_list)

