import io
import pytest
from httpx import AsyncClient
import openpyxl
from app.core.security import hash_password
from app.db.mongodb import get_database
from app.schemas.user import UserRole
from app.services.analytics_service import get_faculty_analytics, get_faculty_history
from app.services.session_service import calculate_session_dynamic_state
from datetime import datetime
import zoneinfo
from app.core.config import settings

tz_kolkata = zoneinfo.ZoneInfo(settings.TIMEZONE)


@pytest.mark.asyncio
async def test_mentor_login_with_employee_id_and_explicit_password(client: AsyncClient):
    db = get_database()
    emp_id = "605101"

    password = "Mentor123!"
    await db.users.insert_one({
        "name": "Dr. Mentor Test",
        "email": "605101@nrtec.in",
        "employee_id": emp_id,
        "mentor_id": emp_id,
        "password_hash": hash_password(password),
        "role": UserRole.MENTOR.value,
        "is_active": True,
    })

    # Test login with employee_id as identifier and the explicit password.
    res = await client.post(
        "/api/auth/login",
        json={"email": emp_id, "password": password, "portal": "MENTOR"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["data"]["user"]["role"] == "MENTOR"
    assert data["data"]["user"]["employeeId"] == emp_id
    assert "access_token" in data["data"]


@pytest.mark.asyncio
async def test_crlr_import_with_google_form_headers(client: AsyncClient):
    db = get_database()

    # Create admin user for token
    admin_hash = hash_password("adminpass")
    admin_doc = {
        "name": "Super Admin",
        "email": "superadmin@test.com",
        "password_hash": admin_hash,
        "role": UserRole.ADMIN.value,
        "is_active": True,
    }
    insert_res = await db.users.insert_one(admin_doc)
    admin_id = str(insert_res.inserted_id)

    # Login admin to obtain access token
    login_res = await client.post(
        "/api/auth/login",
        json={"email": "superadmin@test.com", "password": "adminpass", "portal": "ADMIN"},
    )
    assert login_res.status_code == 200
    token = login_res.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Build an in-memory Excel file matching the user's screenshot media_1792773957928.png
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "CR and LR details"

    # Headers matching the user's image exactly
    headers_row = [
        "Email Address",
        "Enter Full Name",
        "Enter Roll Number",
        "Enter Mobile Number",
        "Select the Year",
        "Select the Department",
        "Select the Section",
        "CR/LR",
        "Password",
    ]
    ws.append(headers_row)

    sample_rows = [
        ["palibandla.karu999@gmail.com", "Palibandla Karunya", "23471A0549", "7275502755", "4th", "CSE", "C2", "LR", ""],
        ["vallalapremkumarprem@gmail.com", "VALLALA PREM KUMAR", "23471A05F2", "8712151559", "4th", "CSE", "C3", "CR", "CRLRPass123!"],
        ["shaikyasmintaj0312@gmail.com", "Shaik Yasmin Taj", "23471A05D1", "8019188630", "4th", "CSE", "C1", "LR", "CRLR789!"],
    ]
    for r in sample_rows:
        ws.append(r)

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    files = {
        "file": (
            "CR_and_LR_details_of_all_years.xlsx",
            buf.getvalue(),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    }

    # Upload via /api/admin/users/import
    res = await client.post("/api/admin/users/import", files=files, headers=headers)
    assert res.status_code == 200
    res_data = res.json()
    assert res_data["success"] is True
    assert res_data["data"]["created"] == 3

    default_password_attempt = await client.post(
        "/api/auth/login",
        json={"email": "23471A0549", "password": "23471A0549", "portal": "CRLR"},
    )
    # A new CR/LR account with a blank password uses its roll number.
    cr_login_res = default_password_attempt
    assert cr_login_res.status_code == 200
    cr_data = cr_login_res.json()
    assert cr_data["success"] is True
    assert cr_data["data"]["user"]["role"] == "LR"
    assert cr_data["data"]["user"]["rollNumber"] == "23471A0549"


@pytest.mark.asyncio
async def test_expired_session_is_marked_crlr_not_marked():
    now_local = datetime(2026, 10, 23, 11, 30, tzinfo=tz_kolkata)
    session_data = {
        "_id": "sess_1",
        "date": "2026-10-23",
        "start_time": "09:00",
        "end_time": "10:00",
        "section": "III-CSE-C1",
        "subject": "FLAT",
        "faculty": "(M.Murali Krishna",
        "faculty_names": ["(M.Murali Krishna"],
        "periods_included": [1],
        "faculty_response": "Pending",
    }

    # Compute dynamic state when current time is after session end time
    computed = calculate_session_dynamic_state(session_data, now_local)
    assert computed["faculty_response"] == "CR/LR Not Marked"
    assert computed["crlr_not_marked"] is True
    assert "CR/LR has not marked" in computed["auto_absence_reason"]


@pytest.mark.asyncio
async def test_absence_reason_locking_for_mentors():
    from fastapi import HTTPException
    from app.services.student_attendance_service import save_absence_reason
    from app.services.mentor_service import update_absence_comment

    db = get_database()
    # Create an absent record
    ins_res = await db.student_attendance.insert_one({
        "year": "II",
        "section": "CSE-A",
        "date": "2026-10-24",
        "roll_number": "22CS2LOCK01",
        "student_name": "Lock Test Student",
        "status": "Absent",
        "reason": None,
        "created_at": datetime.now(tz_kolkata),
    })
    rec_id = str(ins_res.inserted_id)

    # 1. First save as Mentor should succeed
    res1 = await save_absence_reason(
        rec_id, "Sick with viral fever", "Dr. Mentor", actor_role="MENTOR"
    )
    assert res1.reason == "Sick with viral fever"
    assert res1.reason_updated_by == "Dr. Mentor"

    # 2. Resubmission / modification as Mentor MUST fail with 400 Bad Request
    with pytest.raises(HTTPException) as exc_info:
        await save_absence_reason(
            rec_id, "Trying to change reason", "Dr. Mentor", actor_role="MENTOR"
        )
    assert exc_info.value.status_code == 400
    assert "already been recorded and cannot be modified again" in exc_info.value.detail

    # 3. Resubmission via update_absence_comment as Mentor MUST also fail with 400 Bad Request
    mentor_user = {
        "_id": "mentor_lock_id",
        "role": "MENTOR",
        "name": "Dr. Mentor",
        "assigned_students": ["22CS2LOCK01"],
        "assigned_sections": ["CSE-A"],
    }
    with pytest.raises(HTTPException) as exc_info2:
        await update_absence_comment(rec_id, "Attempted resubmit via patch", mentor_user)
    assert exc_info2.value.status_code == 400
    assert "already been recorded and cannot be modified again" in exc_info2.value.detail

    # 4. Admin override CAN still modify if needed
    admin_user = {
        "_id": "admin_lock_id",
        "role": "ADMIN",
        "name": "Admin Officer",
    }
    admin_res = await update_absence_comment(rec_id, "Admin verified medical excuse", admin_user)
    assert admin_res.reason == "Admin verified medical excuse"

