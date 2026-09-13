import pytest
from httpx import AsyncClient
from app.core.security import create_access_token
from app.db.mongodb import get_database
from app.schemas.session import FacultyResponseStatus, SessionStatus
from app.schemas.user import UserRole


@pytest.mark.asyncio
async def test_submit_faculty_present(client: AsyncClient):
    db = get_database()
    cr_res = await db.users.insert_one({
        "name": "CR User",
        "email": "cr@test.com",
        "role": UserRole.CR.value,
        "section": "II-A",
        "is_active": True,
    })
    token = create_access_token({"sub": str(cr_res.inserted_id), "role": "CR"})
    headers = {"Authorization": f"Bearer {token}"}

    # Insert test session
    session_res = await db.sessions.insert_one({
        "section": "II-A",
        "subject": "DBMS",
        "period": "Period 1",
        "periods_included": [1],
        "start_time": "09:10",
        "end_time": "10:00",
        "date": "2026-09-13",
        "session_status": SessionStatus.ACTIVE.value,
        "faculty_response": FacultyResponseStatus.PENDING.value,
    })
    session_id = str(session_res.inserted_id)

    res = await client.post(
        "/api/attendance",
        json={"session_id": session_id, "status": "PRESENT"},
        headers=headers,
    )
    assert res.status_code == 200
    assert res.json()["data"]["facultyResponse"] == "Present"


@pytest.mark.asyncio
async def test_submit_substitute_validation(client: AsyncClient):
    db = get_database()
    cr_res = await db.users.insert_one({
        "name": "CR User",
        "email": "cr@test.com",
        "role": UserRole.CR.value,
        "section": "II-A",
        "is_active": True,
    })
    token = create_access_token({"sub": str(cr_res.inserted_id), "role": "CR"})
    headers = {"Authorization": f"Bearer {token}"}

    session_res = await db.sessions.insert_one({
        "section": "II-A",
        "subject": "DBMS",
        "period": "Period 1",
        "periods_included": [1],
        "start_time": "09:10",
        "end_time": "10:00",
        "date": "2026-09-13",
        "session_status": SessionStatus.ACTIVE.value,
        "faculty_response": FacultyResponseStatus.PENDING.value,
    })
    session_id = str(session_res.inserted_id)

    # Error: PRESENT with substitute_name
    res1 = await client.post(
        "/api/attendance",
        json={"session_id": session_id, "status": "PRESENT", "substitute_name": "Dr. Sub"},
        headers=headers,
    )
    assert res1.status_code == 400

    # Error: SUBSTITUTE without substitute_name
    res2 = await client.post(
        "/api/attendance",
        json={"session_id": session_id, "status": "SUBSTITUTE"},
        headers=headers,
    )
    assert res2.status_code == 400

    # Valid SUBSTITUTE submission
    res3 = await client.post(
        "/api/attendance",
        json={"session_id": session_id, "status": "SUBSTITUTE", "substitute_name": "Dr. Sub"},
        headers=headers,
    )
    assert res3.status_code == 200
    assert res3.json()["data"]["facultyResponse"] == "Substitute"
    assert res3.json()["data"]["substituteName"] == "Dr. Sub"


@pytest.mark.asyncio
async def test_submit_absent_triggers_immediate_admin_alert(client: AsyncClient):
    db = get_database()
    cr_res = await db.users.insert_one({
        "name": "CR User",
        "email": "cr@test.com",
        "role": UserRole.CR.value,
        "section": "II-A",
        "is_active": True,
    })
    token = create_access_token({"sub": str(cr_res.inserted_id), "role": "CR"})
    headers = {"Authorization": f"Bearer {token}"}

    session_res = await db.sessions.insert_one({
        "section": "II-A",
        "subject": "Operating Systems",
        "period": "Period 2",
        "periods_included": [2],
        "start_time": "10:00",
        "end_time": "10:50",
        "date": "2026-09-13",
        "session_status": SessionStatus.ACTIVE.value,
        "faculty_response": FacultyResponseStatus.PENDING.value,
    })
    session_id = str(session_res.inserted_id)

    res = await client.post(
        "/api/attendance",
        json={"session_id": session_id, "status": "ABSENT"},
        headers=headers,
    )
    assert res.status_code == 200

    # Check that an admin alert record was created immediately
    alert = await db.admin_alerts.find_one({"session_id": session_id})
    assert alert is not None
    assert alert["reason"] == "Faculty not available"


@pytest.mark.asyncio
async def test_unauthorized_section_access_forbidden(client: AsyncClient):
    db = get_database()
    # CR belongs to II-A
    cr_res = await db.users.insert_one({
        "name": "CR User",
        "email": "cr@test.com",
        "role": UserRole.CR.value,
        "section": "II-A",
        "is_active": True,
    })
    token = create_access_token({"sub": str(cr_res.inserted_id), "role": "CR"})
    headers = {"Authorization": f"Bearer {token}"}

    # Session belongs to II-B
    session_res = await db.sessions.insert_one({
        "section": "II-B",
        "subject": "Networks",
        "period": "Period 1",
        "periods_included": [1],
        "start_time": "09:10",
        "end_time": "10:00",
        "date": "2026-09-13",
        "session_status": SessionStatus.ACTIVE.value,
        "faculty_response": FacultyResponseStatus.PENDING.value,
    })
    session_id = str(session_res.inserted_id)

    res = await client.post(
        "/api/attendance",
        json={"session_id": session_id, "status": "PRESENT"},
        headers=headers,
    )
    assert res.status_code == 403
