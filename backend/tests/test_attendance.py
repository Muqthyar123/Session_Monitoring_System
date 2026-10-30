from datetime import datetime, timezone, timedelta
import zoneinfo
import pytest
from httpx import AsyncClient
from app.core.config import settings
from app.core.security import create_access_token
from app.db.mongodb import get_database
from app.schemas.session import FacultyResponseStatus, SessionStatus
from app.schemas.user import UserRole
from app.services.session_service import combine_continuous_periods, calculate_session_dynamic_state


@pytest.mark.asyncio
async def test_crlr_attendance_uses_fixed_before_and_after_lunch_windows():
    from app.services.student_attendance_service import get_attendance_windows

    db = get_database()
    await db.timetables.insert_many([
        {"year": "4th Year", "section": "IV-CSE-C5", "day": "Friday", "start_time": "09:10", "end_time": "12:40"},
        {"year": "4th Year", "section": "IV-CSE-C5", "day": "Friday", "start_time": "13:30", "end_time": "16:00"},
    ])

    def friday_at(hour: int, minute: int):
        return datetime(2026, 10, 30, hour, minute, tzinfo=tz_kolkata)

    morning = await get_attendance_windows("4th Year", "IV-CSE-C5", friday_at(12, 0))
    assert morning["configured"] is True
    assert [(w["startTime"], w["endTime"]) for w in morning["windows"]] == [
        ("09:10 AM", "12:40 PM"),
        ("01:30 PM", "04:00 PM"),
    ]
    assert [w["isOpen"] for w in morning["windows"]] == [True, False]

    afternoon = await get_attendance_windows("4th Year", "IV-CSE-C5", friday_at(13, 30))
    assert [w["isOpen"] for w in afternoon["windows"]] == [False, True]

    after_school = await get_attendance_windows("4th Year", "IV-CSE-C5", friday_at(16, 0))
    assert [w["isOpen"] for w in after_school["windows"]] == [False, False]

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
    assert computed["faculty_response"] == "CR/LR Not Marked"
    assert computed["crlr_not_marked"] is True
    assert "CR/LR has not marked" in computed["auto_absence_reason"]


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


@pytest.mark.asyncio
async def test_marking_attendance_strictly_within_class_hour_enforcement(client: AsyncClient):
    """Test that CR/LR can mark attendance ONLY within class hour and cannot modify after completion."""
    db = get_database()
    now_local = datetime.now(tz_kolkata)
    today_str = now_local.strftime("%Y-%m-%d")

    cr_res = await db.users.insert_one({
        "name": "Class Rep",
        "email": "cr_window@test.com",
        "role": UserRole.CR.value,
        "section": "II-CSE-B",
        "is_active": True,
    })
    token = create_access_token({"sub": str(cr_res.inserted_id), "role": "CR"})
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Upcoming session: scheduled in the future today (e.g. 23:58 - 23:59) if now is before that
    future_start = "23:58"
    future_end = "23:59"
    if now_local.hour == 23 and now_local.minute >= 57:
        future_start = "23:59"
        future_end = "23:59"

    # Only test before-start if current time is actually before future_start
    if now_local.hour < 23 or (now_local.hour == 23 and now_local.minute < 58):
        future_sess = await db.sessions.insert_one({
            "section": "II-CSE-B",
            "subject": "Cloud Computing",
            "period": "Period 7",
            "periods_included": [7],
            "start_time": future_start,
            "end_time": future_end,
            "date": today_str,
            "session_status": SessionStatus.UPCOMING.value,
            "faculty_response": FacultyResponseStatus.PENDING.value,
        })
        res_future = await client.post(
            "/api/attendance",
            json={"session_id": str(future_sess.inserted_id), "status": "PRESENT"},
            headers=headers,
        )
        assert res_future.status_code == 400
        err_msg_future = res_future.json().get("error", {}).get("message", "") or str(res_future.json().get("detail", ""))
        assert "only be marked during the assigned class hour" in err_msg_future

    # 2. Completed session: scheduled in the past
    past_date = today_str if now_local.hour > 0 else (now_local - timedelta(days=1)).strftime("%Y-%m-%d")
    past_start = "00:00" if now_local.hour > 0 else "09:00"
    past_end = f"{max(0, now_local.hour - 1):02d}:00" if now_local.hour > 0 else "10:00"

    past_sess = await db.sessions.insert_one({
        "section": "II-CSE-B",
        "subject": "Theory of Computation",
        "period": "Period 1",
        "periods_included": [1],
        "start_time": past_start,
        "end_time": past_end,
        "date": past_date,
        "session_status": SessionStatus.EXPIRED.value,
        "faculty_response": FacultyResponseStatus.PENDING.value,
    })
    res_past = await client.post(
        "/api/attendance",
        json={"session_id": str(past_sess.inserted_id), "status": "PRESENT"},
        headers=headers,
    )
    assert res_past.status_code == 400
    err_msg_past = res_past.json().get("error", {}).get("message", "") or str(res_past.json().get("detail", ""))
    assert "scheduled time has ended" in err_msg_past

    # 3. Active session: start_time=00:00, end_time=23:59 (covering current time)
    active_sess = await db.sessions.insert_one({
        "section": "II-CSE-B",
        "subject": "Data Mining",
        "period": "Period 2",
        "periods_included": [2],
        "start_time": "00:00",
        "end_time": "23:59",
        "date": today_str,
        "session_status": SessionStatus.ACTIVE.value,
        "faculty_response": FacultyResponseStatus.PENDING.value,
    })
    res_active = await client.post(
        "/api/attendance",
        json={"session_id": str(active_sess.inserted_id), "status": "PRESENT"},
        headers=headers,
    )
    assert res_active.status_code == 200
    assert res_active.json()["data"]["facultyResponse"] == "Present"

    # 4. Attempting to remark/modify an already completed session whose hour has ended
    completed_past_sess = await db.sessions.insert_one({
        "section": "II-CSE-B",
        "subject": "Web Tech",
        "period": "Period 3",
        "periods_included": [3],
        "start_time": past_start,
        "end_time": past_end,
        "date": past_date,
        "session_status": SessionStatus.COMPLETED.value,
        "faculty_response": "Present",
    })
    res_completed_past = await client.post(
        "/api/attendance",
        json={"session_id": str(completed_past_sess.inserted_id), "status": "ABSENT"},
        headers=headers,
    )
    assert res_completed_past.status_code == 400
    err_msg_completed = res_completed_past.json().get("error", {}).get("message", "") or str(res_completed_past.json().get("detail", ""))
    assert "scheduled time has ended" in err_msg_completed

