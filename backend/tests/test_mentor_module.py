import pytest
from httpx import AsyncClient
from app.core.security import create_access_token, hash_password
from app.db.mongodb import get_database
from app.schemas.user import UserRole
from datetime import datetime, timezone
import zoneinfo
from app.core.config import settings

tz_kolkata = zoneinfo.ZoneInfo(settings.TIMEZONE)


@pytest.mark.asyncio
async def test_complete_mentor_flow(client: AsyncClient):
    db = get_database()
    now_utc = datetime.now(timezone.utc)
    today_date = datetime.now(tz_kolkata).strftime("%Y-%m-%d")

    # 1. Create a Mentor user in MongoDB with bcrypt hashed password
    mentor_res = await db.users.insert_one({
        "name": "Dr. Siva Nageswara Rao",
        "email": "drssnr@nrtec.in",
        "mentor_id": "605101",
        "role": UserRole.MENTOR.value,
        "password_hash": hash_password("mentor@123"),
        "department": "CSE",
        "designation": "Professor",
        "phone": "8977987777",
        "is_active": True,
        "created_at": now_utc,
        "updated_at": now_utc,
    })
    mentor_user_id = str(mentor_res.inserted_id)

    # 2. Test Mentor Login via API
    login_res = await client.post(
        "/api/auth/login",
        json={
            "email": "605101",
            "password": "mentor@123",
            "portal": "MENTOR",
        },
    )
    assert login_res.status_code == 200
    login_data = login_res.json()["data"]
    token = login_data["access_token"]
    assert token is not None
    assert login_data["user"]["role"] == "MENTOR"
    headers = {"Authorization": f"Bearer {token}"}

    # 3. Insert Students for testing hierarchy
    await db.students.insert_many([
        {
            "batch": 2029,
            "branch": "CSE",
            "year": "2nd Year",
            "name": "Bodapati Pallavi",
            "roll_number": "24471A0575",
            "section": "CSE-J",
            "student_phone": "9505371832",
            "parent_phone": "9642648130",
            "crlr_name": "CR Student J",
            "created_at": now_utc,
            "updated_at": now_utc,
        },
        {
            "batch": 2029,
            "branch": "CSE",
            "year": "2nd Year",
            "name": "Rahul Sharma",
            "roll_number": "24471A0576",
            "section": "CSE-J",
            "student_phone": "9876543210",
            "parent_phone": "9123456780",
            "crlr_name": "CR Student J",
            "created_at": now_utc,
            "updated_at": now_utc,
        },
        {
            "batch": 2028,
            "branch": "CSE",
            "year": "3rd Year",
            "name": "Ananya Reddy",
            "roll_number": "23471A0501",
            "section": "CSE-A",
            "student_phone": "9848012345",
            "parent_phone": "9848054321",
            "crlr_name": "CR Student A",
            "created_at": now_utc,
            "updated_at": now_utc,
        },
    ])

    # 4. Insert Today's Absentee Record
    att_res = await db.student_attendance.insert_one({
        "date": today_date,
        "year": "2nd Year",
        "section": "CSE-J",
        "roll_number": "24471A0575",
        "student_name": "Bodapati Pallavi",
        "student_phone": "9505371832",
        "parent_phone": "9642648130",
        "submitted_by": "CR Student J",
        "status": "Absent",
        "reason": None,
        "created_at": now_utc,
        "updated_at": now_utc,
    })
    att_id = str(att_res.inserted_id)

    # 5. Test Mentor Dashboard API
    dash_res = await client.get("/api/mentor/dashboard", headers=headers)
    assert dash_res.status_code == 200
    dash_data = dash_res.json()["data"]
    assert dash_data["totalStudents"] >= 3
    assert dash_data["totalAbsenteesToday"] >= 1
    assert dash_data["mentorInfo"]["name"] == "Dr. Siva Nageswara Rao"
    assert any(y["year"] == "2nd Year" and y["studentCount"] >= 2 for y in dash_data["yearCounts"])

    # 6. Test All Students Year Cards
    years_res = await client.get("/api/mentor/students/years", headers=headers)
    assert years_res.status_code == 200
    years_data = years_res.json()["data"]
    assert any(y["year"] == "2nd Year" for y in years_data)

    # 7. Test All Students Section Cards for 2nd Year
    secs_res = await client.get("/api/mentor/students/sections?year=2nd Year", headers=headers)
    assert secs_res.status_code == 200
    secs_data = secs_res.json()["data"]
    assert any(s["section"] == "CSE-J" for s in secs_data)

    # 8. Test Section Students
    stus_res = await client.get("/api/mentor/students?year=2nd Year&section=CSE-J", headers=headers)
    assert stus_res.status_code == 200
    stus_data = stus_res.json()["data"]
    assert len(stus_data) == 2
    assert any(s["rollNumber"] == "24471A0575" for s in stus_data)

    # 9. Test Global Student Search
    search_res = await client.get("/api/mentor/students/search?q=Pallavi", headers=headers)
    assert search_res.status_code == 200
    search_data = search_res.json()["data"]
    assert len(search_data) >= 1
    assert search_data[0]["rollNumber"] == "24471A0575"

    search_roll = await client.get("/api/mentor/students/search?q=23471A", headers=headers)
    assert search_roll.status_code == 200
    assert any(s["rollNumber"] == "23471A0501" for s in search_roll.json()["data"])

    # 10. Test Absentee Year Cards
    abs_years_res = await client.get("/api/mentor/absentees/years", headers=headers)
    assert abs_years_res.status_code == 200
    abs_years = abs_years_res.json()["data"]
    assert any(y["year"] == "2nd Year" and y["absenteeCount"] >= 1 for y in abs_years)

    # 11. Test Absentee Section Cards for 2nd Year
    abs_secs_res = await client.get("/api/mentor/absentees/sections?year=2nd Year", headers=headers)
    assert abs_secs_res.status_code == 200
    abs_secs = abs_secs_res.json()["data"]
    assert any(s["section"] == "CSE-J" and s["absenteeCount"] >= 1 for s in abs_secs)

    # 12. Test Section Absentees
    abs_list_res = await client.get("/api/mentor/absentees?year=2nd Year&section=CSE-J", headers=headers)
    assert abs_list_res.status_code == 200
    abs_list = abs_list_res.json()["data"]
    assert len(abs_list) == 1
    assert abs_list[0]["rollNumber"] == "24471A0575"

    # 13. Test Global Absentee Search
    abs_search_res = await client.get("/api/mentor/absentees/search?q=Pallavi", headers=headers)
    assert abs_search_res.status_code == 200
    assert len(abs_search_res.json()["data"]) == 1

    # 14. Test Absence Comment API (PATCH and PUT)
    comment_res = await client.patch(
        f"/api/mentor/absentees/{att_id}/comment",
        json={"comment": "Medical emergency, fever reported by parent."},
        headers=headers,
    )
    assert comment_res.status_code == 200
    updated_rec = comment_res.json()["data"]
    assert updated_rec["reason"] == "Medical emergency, fever reported by parent."
    assert updated_rec["reasonUpdatedBy"] == "Dr. Siva Nageswara Rao"

    # Verify MongoDB persistence
    persisted_doc = await db.student_attendance.find_one({"_id": att_res.inserted_id})
    assert persisted_doc["reason"] == "Medical emergency, fever reported by parent."

    # 15. Role Authorization check: CRLR user cannot access Mentor endpoints
    crlr_u = await db.users.insert_one({
        "name": "CR Student",
        "email": "cr@test.com",
        "role": UserRole.CR.value,
        "is_active": True,
    })
    crlr_token = create_access_token({"sub": str(crlr_u.inserted_id), "role": "CR"})
    crlr_headers = {"Authorization": f"Bearer {crlr_token}"}
    forbidden_res = await client.get("/api/mentor/dashboard", headers=crlr_headers)
    assert forbidden_res.status_code == 403


@pytest.mark.asyncio
async def test_mentor_default_password_is_id_number(client: AsyncClient):
    db = get_database()
    admin_u = await db.users.insert_one({
        "name": "Admin",
        "email": "admin_mentor_test@test.com",
        "role": UserRole.ADMIN.value,
        "is_active": True,
    })
    admin_token = create_access_token({"sub": str(admin_u.inserted_id), "role": "ADMIN"})
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Admin creates mentor without specifying password
    create_res = await client.post(
        "/api/admin/mentors",
        json={
            "name": "Moturi Sireesha",
            "mentorId": "905101",
            "email": "moturisireesha@gmail.com",
            "department": "CSE",
            "designation": "Associate Professor",
            "phone": "9492468445",
            "role": "MENTOR",
        },
        headers=admin_headers,
    )
    assert create_res.status_code == 201

    # 2. Mentor logs in using Mentor ID as username AND Mentor ID as password
    login_id_res = await client.post(
        "/api/auth/login",
        json={
            "email": "905101",
            "password": "905101",
            "portal": "MENTOR",
        },
    )
    assert login_id_res.status_code == 200
    assert login_id_res.json()["data"]["user"]["mentorId"] == "905101"

    # 3. Mentor can also log in using Email as username AND Mentor ID as password
    login_email_res = await client.post(
        "/api/auth/login",
        json={
            "email": "moturisireesha@gmail.com",
            "password": "905101",
            "portal": "MENTOR",
        },
    )
    assert login_email_res.status_code == 200

