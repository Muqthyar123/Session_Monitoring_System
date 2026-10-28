import pytest

from app.db.mongodb import get_database
from app.services.section_service import reconcile_sections_with_timetables
from app.services.timetable_service import delete_all_timetables


@pytest.mark.asyncio
async def test_timetable_reconciliation_deactivates_stale_sections_instead_of_deleting():
    db = get_database()
    section = await db.sections.insert_one({
        "year": "2nd Year",
        "branch": "CSE",
        "section_name": "II-CSE-OLD",
        "is_active": True,
        "assigned_cr_id": "preserved-cr-id",
    })

    result = await reconcile_sections_with_timetables()

    stored = await db.sections.find_one({"_id": section.inserted_id})
    assert stored is not None
    assert stored["is_active"] is False
    assert stored["assigned_cr_id"] == "preserved-cr-id"
    assert result["stale_sections_deactivated"] == 1


@pytest.mark.asyncio
async def test_timetable_reset_reports_all_related_deletions_and_audits():
    db = get_database()
    await db.timetables.insert_one({"section": "II-CSE-A"})
    await db.sessions.insert_one({"section": "II-CSE-A"})
    await db.attendance_records.insert_one({"section": "II-CSE-A"})

    counts = await delete_all_timetables(actor_id="admin-reset-test")

    assert counts == {
        "timetables_deleted": 1,
        "sessions_deleted": 1,
        "attendance_records_deleted": 1,
    }
    audit = await db.audit_logs.find_one({"action": "RESET_TIMETABLES"})
    assert audit["actor_id"] == "admin-reset-test"
    assert audit["metadata"] == counts
