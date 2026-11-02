from datetime import datetime, timezone

import pytest
from bson import ObjectId
from fastapi import HTTPException

from app.api.attendance_controls import (
    DraftUpdate,
    SuspensionCreate,
    _matching_suspensions,
    cancel_suspension,
    create_suspension,
    save_attendance_draft,
)
from app.db.mongodb import get_database
from app.services.student_attendance_service import submit_student_attendance
from app.schemas.student_attendance import StudentAttendanceSubmitRequest


@pytest.mark.asyncio
async def test_draft_is_scoped_to_user_and_session_and_saved_in_database():
    db = get_database()
    await db.students.insert_one({"year": "2nd Year", "section": "CSE-A", "roll_number": "R001"})
    user_a = {"_id": ObjectId(), "name": "CR A", "role": "CR", "year": "2nd Year", "section": "CSE-A"}
    user_b = {**user_a, "_id": ObjectId()}
    payload = DraftUpdate(year="2nd Year", section="CSE-A", date=datetime.now().astimezone().strftime("%Y-%m-%d"), sessionId="SESSION_1", absentRolls=["R001"])
    # Use the institutional date, independently of the host timezone.
    import zoneinfo
    from app.core.config import settings
    payload.date = datetime.now(zoneinfo.ZoneInfo(settings.TIMEZONE)).strftime("%Y-%m-%d")
    response = await save_attendance_draft(payload, user_a)
    assert response.data["absent_rolls"] == ["R001"]
    assert response.data["version"] == 1
    assert await db.attendance_drafts.count_documents({"user_id": str(user_b["_id"])}) == 0
    assert await db.attendance_drafts.count_documents({"session_id": "SESSION_2"}) == 0


@pytest.mark.asyncio
async def test_overlapping_suspension_remains_effective_after_cancelling_one():
    user = {"_id": ObjectId(), "name": "Admin", "role": "ADMIN"}
    payload = SuspensionCreate(years=["2nd Year"], sectionsByYear={"2nd Year": ["CSE-A"]}, startDate="2026-01-01", endDate="2030-12-31", attendanceType="STUDENT")
    first = await create_suspension(payload, user)
    second = await create_suspension(payload, user)
    await cancel_suspension(first.data["id"], user)
    active = await _matching_suspensions(get_database(), "2nd Year", "CSE-A", "2026-11-01", "STUDENT")
    assert len(active) == 1
    assert str(active[0]["_id"]) == second.data["id"]


@pytest.mark.asyncio
async def test_suspension_request_id_makes_activation_retry_idempotent():
    db = get_database()
    user = {"_id": ObjectId(), "name": "Admin", "role": "ADMIN"}
    payload = SuspensionCreate(years=["3rd Year"], sectionsByYear={"3rd Year": ["CSE-B"]}, startDate="2026-01-01", endDate="2030-12-31", attendanceType="BOTH", requestId="0123456789abcdef01234567")
    first = await create_suspension(payload, user)
    retry = await create_suspension(payload, user)
    assert first.data["id"] == retry.data["id"]
    assert await db.attendance_suspensions.count_documents({}) == 1


@pytest.mark.asyncio
async def test_suspension_blocks_direct_student_attendance_submission():
    db = get_database()
    user = {"_id": ObjectId(), "id": "admin-1", "name": "CR", "role": "CR", "year": "2nd Year", "section": "CSE-A"}
    today = datetime.now(timezone.utc).date().isoformat()
    await db.attendance_suspensions.insert_one({
        "years": ["2nd Year"], "sections_by_year": {"2nd Year": ["CSE-A"]}, "all_sections_years": [],
        "start_date": "2020-01-01", "end_date": "2035-12-31", "attendance_type": "STUDENT", "status": "ACTIVE",
    })
    request = StudentAttendanceSubmitRequest(year="2nd Year", section="CSE-A", sessionId="SESSION_1", absentees=[])
    with pytest.raises(HTTPException) as exc:
        await submit_student_attendance(request, user)
    assert exc.value.status_code == 423
    assert await db.student_attendance_submissions.count_documents({"date": today}) == 0
