import pytest
from datetime import datetime, timezone
from fastapi import HTTPException
from app.db.mongodb import get_database
from app.schemas.student_attendance import AbsenteeItem, StudentAttendanceSubmitRequest
from app.services.analytics_service import (
    extract_individual_faculties,
    get_faculty_analytics,
    get_year_cards_summary,
)
from app.services.mentor_service import update_absence_comment
from app.services.student_attendance_service import (
    get_student_attendance_submission_status,
    save_absence_reason,
    submit_student_attendance,
)


@pytest.mark.asyncio
async def test_extract_individual_faculties_colon_comma():
    # Case 1: Subject has colon and multiple comma-separated faculty
    doc1 = {
        "subject": "FSD - 2 LAB: D.Malleswari, N.Lakshmi Gayatri, GVVSS.Vijayasaradhi",
        "faculty": None,
    }
    clean_subj, fac_list = extract_individual_faculties(doc1)
    assert clean_subj == "FSD - 2 LAB"
    assert len(fac_list) == 3
    assert "D.Malleswari" in fac_list
    assert "N.Lakshmi Gayatri" in fac_list
    assert "GVVSS.Vijayasaradhi" in fac_list

    # Case 2: Subject is Mathematics and Faculty is string with colon
    doc2 = {
        "subject": "Mathematics",
        "faculty": "Maths Lab: John Smith, David Kumar, Rahul Sharma",
    }
    clean_subj2, fac_list2 = extract_individual_faculties(doc2)
    assert clean_subj2 == "Mathematics"
    assert len(fac_list2) == 3
    assert "John Smith" in fac_list2
    assert "David Kumar" in fac_list2
    assert "Rahul Sharma" in fac_list2

    # Case 3: faculty_names list given
    doc3 = {
        "subject": "Cloud Computing",
        "faculty_names": ["Dr. Ramesh", "Prof. Suresh"],
    }
    clean_subj3, fac_list3 = extract_individual_faculties(doc3)
    assert clean_subj3 == "Cloud Computing"
    assert len(fac_list3) == 2
    assert "Dr. Ramesh" in fac_list3
    assert "Prof. Suresh" in fac_list3


@pytest.mark.asyncio
async def test_faculty_analytics_multi_faculty_sessions():
    db = get_database()
    await db.timetables.delete_many({})
    await db.sessions.delete_many({})
    await db.attendance_records.delete_many({})

    # Seed timetable with multi-faculty lab
    tt_doc = {
        "year": "2nd Year",
        "section": "II-CSE-A",
        "day": "Monday",
        "period": 1,
        "subject": "FSD - 2 LAB: D.Malleswari, N.Lakshmi Gayatri, GVVSS.Vijayasaradhi",
        "faculty_names": ["D.Malleswari", "N.Lakshmi Gayatri", "GVVSS.Vijayasaradhi"],
        "updated_at": datetime.now(timezone.utc),
    }
    await db.timetables.insert_one(tt_doc)

    # Seed a session attended
    sess_doc = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "year": "2nd Year",
        "section": "II-CSE-A",
        "subject": "FSD - 2 LAB: D.Malleswari, N.Lakshmi Gayatri, GVVSS.Vijayasaradhi",
        "faculty_names": ["D.Malleswari", "N.Lakshmi Gayatri", "GVVSS.Vijayasaradhi"],
        "faculty_response": "PRESENT",
        "periods_included": [1, 2],
        "created_at": datetime.now(timezone.utc),
    }
    await db.sessions.insert_one(sess_doc)

    # Fetch faculty analytics
    analytics = await get_faculty_analytics()
    assert len(analytics) == 3

    fac_names = [f["facultyName"] for f in analytics]
    assert "D.Malleswari" in fac_names
    assert "N.Lakshmi Gayatri" in fac_names
    assert "GVVSS.Vijayasaradhi" in fac_names

    for item in analytics:
        assert item["attendedClasses"] == 2
        assert item["attendancePercentage"] == 100.0
        assert item["subject"] == "FSD - 2 LAB"


@pytest.mark.asyncio
async def test_crlr_duplicate_prevention_and_status():
    db = get_database()
    await db.student_attendance.delete_many({})
    await db.student_attendance_submissions.delete_many({})

    crlr_user1 = {"id": "cr-1", "_id": "cr-1", "name": "Rahul Kumar", "role": "CR", "section": "A", "year": "2nd Year"}
    crlr_user2 = {"id": "lr-1", "_id": "lr-1", "name": "Sneha Sharma", "role": "LR", "section": "A", "year": "2nd Year"}

    # Initial status should be not submitted
    status_before = await get_student_attendance_submission_status("2nd Year", "A")
    assert status_before["isSubmittedToday"] is False

    # 1. First submission by CR
    req1 = StudentAttendanceSubmitRequest(
        year="2nd Year",
        section="A",
        absentees=[
            AbsenteeItem(
                rollNumber="22CS2A01",
                studentName="Student One",
            )
        ]
    )
    res1 = await submit_student_attendance(req1, crlr_user1)
    assert res1["absent_count"] == 1

    # 2. Check status after submission
    status_after = await get_student_attendance_submission_status("2nd Year", "A")
    assert status_after["isSubmittedToday"] is True
    assert "Rahul Kumar" in status_after["submittedBy"]
    assert status_after["absentCount"] == 1
    assert "22CS2A01" in status_after["absentRolls"]

    # 3. Second submission attempt by LR should raise 409 Conflict
    req2 = StudentAttendanceSubmitRequest(
        year="2nd Year",
        section="A",
        absentees=[]
    )
    with pytest.raises(HTTPException) as exc_info:
        await submit_student_attendance(req2, crlr_user2)
    assert exc_info.value.status_code == 409
    assert "already been submitted" in exc_info.value.detail


@pytest.mark.asyncio
async def test_mentor_absence_reason_save_and_comment():
    db = get_database()
    await db.student_attendance.delete_many({})

    # Seed an absentee record
    ins_res = await db.student_attendance.insert_one({
        "date": datetime.now().strftime("%Y-%m-%d"),
        "year": "2nd Year",
        "section": "A",
        "roll_number": "22CS2A09",
        "student_name": "Test Absentee",
        "status": "Absent",
        "reason": None,
        "created_at": datetime.now(timezone.utc),
    })
    rec_id = str(ins_res.inserted_id)

    # 1. Update reason via save_absence_reason
    res1 = await save_absence_reason(rec_id, "High Fever with Doctor Note", "Dr. Rao", "mentor-99")
    assert res1.reason == "High Fever with Doctor Note"
    assert res1.reason_updated_by == "Dr. Rao"

    # 2. Update reason via update_absence_comment
    mentor_user = {"_id": "mentor-99", "name": "Dr. Rao", "email": "rao@example.com"}
    res2 = await update_absence_comment(rec_id, "Followed up with father - will return Monday", mentor_user)
    assert res2.reason == "Followed up with father - will return Monday"
    assert res2.reason_updated_by == "Dr. Rao"
