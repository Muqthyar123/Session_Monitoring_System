from datetime import datetime, timezone
import zoneinfo
import pytest
from httpx import AsyncClient
from app.core.config import settings
from app.core.security import create_access_token
from app.db.mongodb import get_database
from app.schemas.session import FacultyResponseStatus, SessionStatus
from app.schemas.user import UserRole
from app.services.session_service import combine_continuous_periods, calculate_session_dynamic_state

tz_kolkata = zoneinfo.ZoneInfo(settings.TIMEZONE)


@pytest.mark.asyncio
async def test_submit_faculty_present(client: AsyncClient):
    db = get_database()
    today_str = datetime.now(tz_kolkata).strftime("%Y-%m-%d")
    cr_res = await db.users.insert_one({
        "name": "CR User",
        "email": "cr@test.com",
        "role": UserRole.CR.value,
        "section": "II-A",
        "is_active": True,
    })
    token = create_access_token({"sub": str(cr_res.inserted_id), "role": "CR"})
    headers = {"Authorization": f"Bearer {token}"}

    # Insert active test session with future end time
    session_res = await db.sessions.insert_one({
        "section": "II-A",
        "subject": "DBMS",
        "period": "Period 1",
        "periods_included": [1],
        "start_time": "00:00",
        "end_time": "23:59",
        "date": today_str,
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
    assert res.json()["data"]["submittedByName"] == "CR User"


@pytest.mark.asyncio
async def test_submit_substitute_validation(client: AsyncClient):
    db = get_database()
    today_str = datetime.now(tz_kolkata).strftime("%Y-%m-%d")
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
        "start_time": "00:00",
        "end_time": "23:59",
        "date": today_str,
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
    today_str = datetime.now(tz_kolkata).strftime("%Y-%m-%d")
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
        "start_time": "00:00",
        "end_time": "23:59",
        "date": today_str,
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
    assert "Faculty not available" in alert["reason"]


@pytest.mark.asyncio
async def test_unauthorized_section_access_forbidden(client: AsyncClient):
    db = get_database()
    today_str = datetime.now(tz_kolkata).strftime("%Y-%m-%d")
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
        "start_time": "00:00",
        "end_time": "23:59",
        "date": today_str,
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


@pytest.mark.asyncio
async def test_faculty_presence_deadline_enforcement(client: AsyncClient):
    """Test that CR/LR cannot submit faculty attendance once session end time has passed."""
    db = get_database()
    cr_res = await db.users.insert_one({
        "name": "CR User",
        "email": "cr_deadline@test.com",
        "role": UserRole.CR.value,
        "section": "II-A",
        "is_active": True,
    })
    token = create_access_token({"sub": str(cr_res.inserted_id), "role": "CR"})
    headers = {"Authorization": f"Bearer {token}"}

    # Ended session (past end_time 09:00 on 2026-01-01)
    session_res = await db.sessions.insert_one({
        "section": "II-A",
        "subject": "Mathematics",
        "period": "Period 1",
        "periods_included": [1],
        "start_time": "08:00",
        "end_time": "09:00",
        "date": "2026-01-01",
        "session_status": SessionStatus.EXPIRED.value,
        "faculty_response": FacultyResponseStatus.PENDING.value,
    })
    session_id = str(session_res.inserted_id)

    res = await client.post(
        "/api/attendance",
        json={"session_id": session_id, "status": "PRESENT"},
        headers=headers,
    )
    assert res.status_code == 400
    err_body = res.json()
    err_msg = err_body.get("error", {}).get("message", "") or str(err_body.get("detail", ""))
    assert "scheduled time has ended" in err_msg


@pytest.mark.asyncio
async def test_auto_marked_absent_on_session_completion():
    """Test dynamic state auto-marks pending session as absent once now >= end_time."""
    now_local = datetime(2026, 10, 7, 11, 30, tzinfo=tz_kolkata)
    session_doc = {
        "_id": "sess-1",
        "date": "2026-10-07",
        "start_time": "09:00",
        "end_time": "10:00",
        "subject": "Data Structures",
        "faculty": "Dr. Smith",
        "section": "II-CSE-A",
        "period": "Period 1",
        "periods_included": [1],
        "session_status": "Upcoming",
        "faculty_response": "Pending",
    }
    computed = calculate_session_dynamic_state(session_doc, now_local)
    assert computed["faculty_response"] == "Not Present"
    assert computed["auto_marked_absent"] is True
    assert "Automatically marked absent" in computed["auto_absence_reason"]


def test_lab_session_continuous_merging():
    """Test that two adjacent lab periods merge into ONE continuous session."""
    periods = [
        {
            "period": 1,
            "start_time": "09:00",
            "end_time": "10:00",
            "subject": "Python Lab",
            "faculty": "Dr. Alan",
            "section": "II-CSE-A",
            "year": "2nd Year",
            "day": "Monday",
        },
        {
            "period": 2,
            "start_time": "10:00",
            "end_time": "11:00",
            "subject": "Python Lab",
            "faculty": "Dr. Alan",
            "section": "II-CSE-A",
            "year": "2nd Year",
            "day": "Monday",
        },
        {
            "period": 3,
            "start_time": "11:15",
            "end_time": "12:15",
            "subject": "Discrete Maths",
            "faculty": "Prof. Euler",
            "section": "II-CSE-A",
            "year": "2nd Year",
            "day": "Monday",
        },
    ]
    merged = combine_continuous_periods(periods)
    assert len(merged) == 2
    lab_session = merged[0]
    assert lab_session["subject"] == "Python Lab"
    assert lab_session["start_time"] == "09:00"
    assert lab_session["end_time"] == "11:00"
    assert lab_session["periods_included"] == [1, 2]
    assert lab_session["period_display"] == "Period 1 - Period 2"


@pytest.mark.asyncio
async def test_student_attendance_correction_with_mandatory_reason(client: AsyncClient):
    """Test CR/LR attendance correction with mandatory reason validation."""
    db = get_database()
    today_str = datetime.now(tz_kolkata).strftime("%Y-%m-%d")

    # Create CR user for II-CSE-A
    cr_res = await db.users.insert_one({
        "name": "Alice CR",
        "email": "alice_cr@test.com",
        "role": UserRole.CR.value,
        "section": "II-CSE-A",
        "year": "2nd Year",
        "is_active": True,
    })
    token = create_access_token({"sub": str(cr_res.inserted_id), "role": "CR"})
    headers = {"Authorization": f"Bearer {token}"}

    # Seed an absentee record and submission for today
    att_res = await db.student_attendance.insert_one({
        "date": today_str,
        "year": "2nd Year",
        "section": "II-CSE-A",
        "roll_number": "22CSE099",
        "student_name": "Bob Student",
        "status": "Absent",
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    })
    record_id = str(att_res.inserted_id)

    await db.student_attendance_submissions.insert_one({
        "date": today_str,
        "year": "2nd Year",
        "section": "II-CSE-A",
        "absent_count": 1,
        "absent_rolls": ["22CSE099"],
    })

    res_err = await client.patch(
        f"/api/crlr/student-attendance/{record_id}/correct",
        json={"reason": "late", "new_status": "Present"},
        headers=headers,
    )
    assert res_err.status_code == 400
    err_body = res_err.json()
    err_msg = err_body.get("error", {}).get("message", "") or str(err_body.get("detail", ""))
    assert "mandatory reason is required" in err_msg

    # Test 2: Valid correction with detailed reason
    res_ok = await client.patch(
        f"/api/crlr/student-attendance/{record_id}/correct",
        json={
            "reason": "Student arrived late after roll call with permission from HOD",
            "new_status": "Present",
        },
        headers=headers,
    )
    assert res_ok.status_code == 200
    data = res_ok.json()["data"]
    assert data["status"] == "Present"
    assert data["originalStatus"] == "Absent"
    assert data["correctedBy"] == "Alice CR (CR)"
    assert "Student arrived late" in data["correctionReason"]

    # Verify submission aggregate updated (absent_count decremented and roll removed)
    sub = await db.student_attendance_submissions.find_one({"section": "II-CSE-A", "date": today_str})
    assert sub["absent_count"] == 0
    assert "22CSE099" not in sub["absent_rolls"]
