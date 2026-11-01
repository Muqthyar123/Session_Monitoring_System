import pytest
from bson import ObjectId
from fastapi import HTTPException

from app.api.absentee_reports import export_absentee_history
from app.api.student_attendance import get_student_analytics_summary_api, get_student_complete_history_api
from app.db.mongodb import get_database
from app.services.mentor_mapping_service import get_mentor_assigned_student_ids


async def _export(user, *, format="csv", roll_number=None):
    return await export_absentee_history(
        format=format,
        year="2nd Year",
        branch=None,
        section="A",
        roll_number=roll_number,
        from_date="2026-10-20",
        to_date="2026-10-20",
        user=user,
    )


@pytest.mark.asyncio
async def test_mentor_export_uses_existing_student_mapping_for_all_formats():
    db = get_database()
    mentor_id = ObjectId()
    assigned_id = ObjectId()
    unassigned_id = ObjectId()
    user = {"_id": mentor_id, "id": str(mentor_id), "name": "Assigned Mentor", "email": "mentor@example.edu", "role": "MENTOR"}
    await db.students.insert_many([
        {"_id": assigned_id, "name": "Assigned Student", "roll_number": "R001", "year": "2nd Year", "section": "A"},
        {"_id": unassigned_id, "name": "Other Student", "roll_number": "R002", "year": "2nd Year", "section": "A"},
    ])
    await db.mentor_student_mappings.insert_one({
        "mentor_id": mentor_id,  # Legacy BSON ObjectId form is supported.
        "mentor_name": "Assigned Mentor",
        "year": "2nd Year",
        "section": "A",
        "student_ids": [str(assigned_id)],
        "is_full_section": False,
    })
    await db.student_attendance.insert_many([
        {"_id": ObjectId(), "student_id": str(assigned_id), "roll_number": "R001", "student_name": "Assigned Student", "year": "2nd Year", "section": "A", "date": "2026-10-20", "status": "Absent"},
        {"_id": ObjectId(), "student_id": str(unassigned_id), "roll_number": "R002", "student_name": "Other Student", "year": "2nd Year", "section": "A", "date": "2026-10-20", "status": "Absent"},
    ])

    assert await get_mentor_assigned_student_ids(user) == [str(assigned_id)]
    csv_response = await _export(user, format="csv")
    csv_text = csv_response.body.decode("utf-8-sig")
    assert "R001" in csv_text
    assert "R002" not in csv_text
    assert (await _export(user, format="xlsx")).body.startswith(b"PK")
    assert (await _export(user, format="pdf")).body.startswith(b"%PDF")
    admin_response = await _export({"_id": ObjectId(), "role": "ADMIN"})
    assert "R001" in admin_response.body.decode("utf-8-sig")
    assert "R002" in admin_response.body.decode("utf-8-sig")

    with pytest.raises(HTTPException) as denied:
        await _export(user, roll_number="R002")
    assert denied.value.status_code == 403

    # The resolver reads mappings on every request; reassignment takes effect
    # immediately without relying on stale process or browser caches.
    await db.mentor_student_mappings.update_one(
        {"mentor_id": mentor_id}, {"$set": {"student_ids": [str(unassigned_id)]}}
    )
    assert await get_mentor_assigned_student_ids(user) == [str(unassigned_id)]
    with pytest.raises(HTTPException) as reassigned:
        await _export(user, roll_number="R001")
    assert reassigned.value.status_code == 403


@pytest.mark.asyncio
async def test_full_section_mapping_includes_current_roster_only_for_that_section():
    db = get_database()
    mentor_id = ObjectId()
    assigned_id = ObjectId()
    newly_enrolled_id = ObjectId()
    other_section_id = ObjectId()
    other_branch_id = ObjectId()
    user = {"_id": mentor_id, "name": "Section Mentor", "role": "MENTOR"}
    await db.students.insert_many([
        {"_id": assigned_id, "roll_number": "R101", "year": "2nd Year", "section": "CSE-A"},
        {"_id": newly_enrolled_id, "roll_number": "R103", "year": "2nd Year", "section": "A"},
        {"_id": other_section_id, "roll_number": "R102", "year": "2nd Year", "section": "CSE-B"},
        {"_id": other_branch_id, "roll_number": "R104", "year": "2nd Year", "section": "ECE-A", "branch": "ECE"},
    ])
    await db.mentor_student_mappings.insert_one({
        "mentor_id": str(mentor_id), "year": "2nd Year", "section": "A",
        "student_ids": [str(assigned_id)], "is_full_section": True,
    })

    assigned = await get_mentor_assigned_student_ids(user)
    assert assigned == sorted([str(assigned_id), str(newly_enrolled_id)])


@pytest.mark.asyncio
async def test_unmapped_mentor_export_fails_closed_with_admin_guidance():
    user = {"_id": ObjectId(), "name": "Unmapped Mentor", "role": "MENTOR"}
    assert await get_mentor_assigned_student_ids(user) == []

    with pytest.raises(HTTPException) as denied:
        await _export(user)
    assert denied.value.status_code == 403
    assert "administrator" in denied.value.detail


@pytest.mark.asyncio
async def test_legacy_name_only_mapping_is_not_shared_by_duplicate_names():
    db = get_database()
    first_id = ObjectId()
    second_id = ObjectId()
    assigned_student_id = ObjectId()
    await db.users.insert_many([
        {"_id": first_id, "name": "Same Name", "role": "MENTOR"},
        {"_id": second_id, "name": "Same Name", "role": "MENTOR"},
    ])
    await db.mentor_student_mappings.insert_one({
        "mentor_name": "Same Name", "year": "2nd Year", "section": "A",
        "student_ids": [str(assigned_student_id)],
    })

    assert await get_mentor_assigned_student_ids(
        {"_id": first_id, "name": "Same Name", "role": "MENTOR"}
    ) == []
    assert await get_mentor_assigned_student_ids(
        {"_id": second_id, "name": "Same Name", "role": "MENTOR"}
    ) == []


@pytest.mark.asyncio
async def test_mentor_attendance_history_api_filters_students_and_denies_unassigned_history():
    db = get_database()
    mentor_id = ObjectId()
    assigned_id = ObjectId()
    unassigned_id = ObjectId()
    user = {"_id": mentor_id, "role": "MENTOR"}
    await db.students.insert_many([
        {"_id": assigned_id, "name": "Assigned", "roll_number": "R201", "year": "2nd Year", "section": "A"},
        {"_id": unassigned_id, "name": "Unassigned", "roll_number": "R202", "year": "2nd Year", "section": "A"},
    ])
    await db.mentor_student_mappings.insert_one({
        "mentor_id": str(mentor_id), "year": "2nd Year", "section": "A",
        "student_ids": [str(assigned_id)], "is_full_section": False,
    })
    await db.student_attendance.insert_many([
        {"_id": ObjectId(), "student_id": str(assigned_id), "roll_number": "R201", "student_name": "Assigned", "year": "2nd Year", "section": "A", "date": "2026-10-20", "status": "Absent"},
        {"_id": ObjectId(), "student_id": str(unassigned_id), "roll_number": "R202", "student_name": "Unassigned", "year": "2nd Year", "section": "A", "date": "2026-10-20", "status": "Absent"},
    ])

    summary = await get_student_analytics_summary_api("2nd Year", "A", user)
    assert [student.roll_number for student in summary.data] == ["R201"]
    history = await get_student_complete_history_api("R201", user)
    assert [record.roll_number for record in history.data] == ["R201"]
    with pytest.raises(HTTPException) as denied:
        await get_student_complete_history_api("R202", user)
    assert denied.value.status_code == 403
