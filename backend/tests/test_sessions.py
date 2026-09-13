import pytest
from httpx import AsyncClient
from app.core.security import create_access_token, hash_password
from app.db.mongodb import get_database
from app.schemas.user import UserRole
from app.services.session_service import combine_continuous_periods


def test_continuous_period_combination():
    periods = [
        {"period": 1, "start_time": "09:10", "end_time": "10:00", "subject": "DBMS", "faculty": "Dr. Sharma", "section": "II-A"},
        {"period": 2, "start_time": "10:00", "end_time": "10:50", "subject": "DBMS", "faculty": "Dr. Sharma", "section": "II-A"},
        {"period": 3, "start_time": "10:50", "end_time": "11:40", "subject": "DBMS", "faculty": "Dr. Sharma", "section": "II-A"},
        {"period": 4, "start_time": "11:40", "end_time": "12:30", "subject": "JAVA", "faculty": "Prof. Verma", "section": "II-A"},
    ]

    combined = combine_continuous_periods(periods)
    assert len(combined) == 2, f"Expected 2 sessions, got {len(combined)}"

    # First session: DBMS continuous 09:10 to 11:40
    assert combined[0]["subject"] == "DBMS"
    assert combined[0]["start_time"] == "09:10"
    assert combined[0]["end_time"] == "11:40"
    assert combined[0]["periods_included"] == [1, 2, 3]

    # Second session: JAVA 11:40 to 12:30
    assert combined[1]["subject"] == "JAVA"
    assert combined[1]["start_time"] == "11:40"
    assert combined[1]["end_time"] == "12:30"
    assert combined[1]["periods_included"] == [4]


@pytest.mark.asyncio
async def test_get_today_sessions_api(client: AsyncClient):
    db = get_database()
    cr_res = await db.users.insert_one({
        "name": "CR User",
        "email": "cr@test.com",
        "role": UserRole.CR.value,
        "section": "II-A",
        "is_active": True,
    })
    token = create_access_token({"sub": str(cr_res.inserted_id), "role": "CR"})
    headers = {"Authorization": f"Bearer {token}"}

    res = await client.get("/api/sessions/today", headers=headers)
    assert res.status_code == 200
    assert res.json()["success"] is True
