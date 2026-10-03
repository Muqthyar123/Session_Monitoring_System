import pytest
from datetime import datetime, timezone
from app.db.mongodb import get_database
from app.schemas.student_attendance import AbsenteeItem, StudentAttendanceSubmitRequest
from app.services.student_attendance_service import (
    get_absentee_years,
    get_absentee_sections,
    get_students_analytics_summary,
    get_student_complete_history,
    save_absence_reason,
    submit_student_attendance,
)


@pytest.mark.asyncio
async def test_student_history_and_reason_audit():
    db = get_database()

    # Seed a student
    await db.students.delete_many({})
    await db.student_attendance.delete_many({})
    await db.student_attendance_submissions.delete_many({})

    stu_doc = {
        "name": "BODAPATI PALLAVI",
        "roll_number": "24471A0575",
        "year": "2nd Year",
        "section": "J",
        "branch": "CSE",
        "student_phone": "9505371832",
        "parent_phone": "9642648130",
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    await db.students.insert_one(stu_doc)

    # Submit attendance marking student as absent
    crlr_user = {"id": "crlr-1", "name": "CR Student", "role": "CR", "section": "J", "year": "2nd Year"}
    submit_req = StudentAttendanceSubmitRequest(
        year="2nd Year",
        section="J",
        absentees=[
            AbsenteeItem(
                rollNumber="24471A0575",
                studentName="BODAPATI PALLAVI",
                studentPhone="9505371832",
                parentPhone="9642648130",
            )
        ]
    )
    sub_res = await submit_student_attendance(submit_req, crlr_user)
    assert sub_res["absent_count"] == 1

    # Check years & sections API
    years = await get_absentee_years()
    assert "2nd Year" in years

    secs = await get_absentee_sections("2nd Year")
    assert "J" in secs

    # Check student analytics summary
    summary = await get_students_analytics_summary("2nd Year", "J")
    assert len(summary) >= 1
    pallavi_sum = next(s for s in summary if s.roll_number == "24471A0575")
    assert pallavi_sum.total_absences == 1

    # Check student complete history
    history = await get_student_complete_history("24471A0575")
    assert len(history) == 1
    rec = history[0]
    assert rec.roll_number == "24471A0575"
    assert rec.status == "Absent"
    assert rec.subject == "Academic Session"

    # Save mentor absence reason
    updated_rec = await save_absence_reason(rec.id, "Medical Emergency - approved by Mentor", "Dr. SIVA NAGESWARA RAO")
    assert updated_rec.reason == "Medical Emergency - approved by Mentor"
    assert updated_rec.reason_updated_by == "Dr. SIVA NAGESWARA RAO"
    assert updated_rec.updated_at is not None

    # Re-fetch history to ensure permanence in MongoDB
    history_after = await get_student_complete_history("24471A0575")
    assert history_after[0].reason == "Medical Emergency - approved by Mentor"
    assert history_after[0].reason_updated_by == "Dr. SIVA NAGESWARA RAO"
