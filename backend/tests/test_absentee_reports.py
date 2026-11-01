import pytest
from bson import ObjectId

from app.api import absentee_reports
from app.db.mongodb import get_database


@pytest.mark.asyncio
async def test_mentor_export_uses_dashboard_filtered_legacy_mode(monkeypatch):
    db = get_database()
    await db.student_attendance.insert_many([
        {"_id": ObjectId(), "student_id": "student-1", "roll_number": "R001", "year": "2nd Year", "section": "CSE-A", "date": "2026-10-20", "status": "Absent"},
        {"_id": ObjectId(), "student_id": "student-2", "roll_number": "R002", "year": "3rd Year", "section": "CSE-A", "date": "2026-10-20", "status": "Absent"},
    ])

    async def no_assignment_data(_user):
        # None is the established legacy mode when assignments are not
        # configured anywhere; an empty list means a mapped mentor has none.
        return None

    monkeypatch.setattr(absentee_reports, "get_mentor_assigned_student_ids", no_assignment_data)
    response = await absentee_reports.export_absentee_history(
        format="csv",
        year="2nd Year",
        branch=None,
        section="CSE-A",
        roll_number=None,
        from_date="2026-10-20",
        to_date="2026-10-20",
        user={"_id": ObjectId(), "role": "MENTOR"},
    )

    exported = response.body.decode("utf-8-sig")
    assert "R001" in exported
    assert "R002" not in exported
