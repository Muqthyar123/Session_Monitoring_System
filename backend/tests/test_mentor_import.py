import pytest
from app.core.security import verify_password
from app.core.security import DEFAULT_MENTOR_PASSWORD
from app.services.excel_service import parse_and_import_mentor_excel
from app.db.mongodb import get_database
from app.core.security import create_access_token
from app.schemas.user import UserRole
from httpx import AsyncClient

SAMPLE_1_CSV = """NON-TEACHING,,,,,,
S.NO,NAME,ID,MAIL ID,DESIGN,BRANCH,MOBILE NO,PASSWORD
1.0,NAGESWARA RAO KUKKAMUDI,705201,knag1999@nrtec.in,COM.OPERATOR (CAMU COORDINATOR),CSE,9705672051,MentorPass1!
2.0,SUBASH CHANDRA POTTURI,1005201,subashpotturi@gmail.com,HARDWARE,CSE,9885013488,Mentor456!"""

SAMPLE_2_CSV = """S.NO,NAME,ID/EMPLOYEE ID,MAIL ID/ EMAIL,DESIGN/DESIGNATION,BRANCH/DEPARTMENT,MOBILE NO,PASSWORD
1.0,SIVA NAGESWARA RAO SIVARATRI,605101,drssnr@nrtec.in,PROFESSOR,CSE,8977987777,MentorPass1!
2.0,MOTURI SIREESHA,905101,moturisireesha@gmail.com,ASSOCIATE PROFESSOR,CSE,9492468445,Mentor456!"""

SAMPLE_3_CSV = """S.No,Name,User name,Email,Employee ID,Designation,Department,Mobile,Profile,PASSWORD
1.0,SIVA NAGESWARA RAO SIVARATRI,605101,drssnr@nrtec.in,605101,PROFESSOR,CSE,8977987777,"Administrator, Administrator",MentorPass1!
2.0,NAGESWARA RAO KUKKAMUDI,705201,knag1999@nrtec.in,705201,COM.OPERATOR,CSE,9705672051,"Course Coordinator",Mentor456!"""


@pytest.mark.asyncio
async def test_mentor_import_sample1():
    res = await parse_and_import_mentor_excel(SAMPLE_1_CSV.encode("utf-8"), "non_teaching.csv", "admin123")
    assert res["created"] + res["updated"] == 2
    assert res["failed"] == 0

    db = get_database()
    u = await db.users.find_one({"mentor_id": "705201"})
    assert u is not None
    assert u["name"] == "NAGESWARA RAO KUKKAMUDI"
    assert u["designation"] == "COM.OPERATOR (CAMU COORDINATOR)"
    assert u["department"] == "CSE"
    assert u["phone"] == "9705672051"


@pytest.mark.asyncio
async def test_mentor_import_sample2():
    res = await parse_and_import_mentor_excel(SAMPLE_2_CSV.encode("utf-8"), "faculty.csv", "admin123")
    assert res["created"] + res["updated"] == 2
    assert res["failed"] == 0

    db = get_database()
    u = await db.users.find_one({"mentor_id": "605101"})
    assert u is not None
    assert u["name"] == "SIVA NAGESWARA RAO SIVARATRI"
    assert u["designation"] == "PROFESSOR"
    assert u["department"] == "CSE"


@pytest.mark.asyncio
async def test_mentor_import_sample3():
    res = await parse_and_import_mentor_excel(SAMPLE_3_CSV.encode("utf-8"), "roles.csv", "admin123")
    assert res["created"] + res["updated"] == 2
    assert res["failed"] == 0

    db = get_database()
    u = await db.users.find_one({"mentor_id": "605101"})
    assert u is not None
    assert u["profile"] == "Administrator, Administrator"


@pytest.mark.asyncio
async def test_mentor_import_special_chars_and_unicode():
    csv_data = """NON-TEACHING ROSTER 2026-2027,,,,,,
DEPARTMENT OF COMPUTER SCIENCE AND ENGINEERING,,,,,,
,,,,,,
S.NO,NAME,ID/EMPLOYEE ID,MAIL ID/ EMAIL,DESIGN/DESIGNATION,BRANCH/DEPARTMENT,MOBILE NO,PASSWORD
52.0,YESAIAHÂ BATHULA,2505103,â yesaiahb@nrtec.in,ASSISTANT PROFESSOR,CSE,Â 8790424793,MentorUni1!
53.0,NAGOOR BABUÂ Â SHAIK,2505104,â nagoorbabusk@nrtec.in,ASSISTANT PROFESSOR,CSE,8790424794,MentorUni2!
"""
    res = await parse_and_import_mentor_excel(csv_data.encode("utf-8"), "unicode_mentors.csv", "admin123")
    assert res["created"] + res["updated"] == 2
    assert res["failed"] == 0

    db = get_database()
    u1 = await db.users.find_one({"mentor_id": "2505103"})
    assert u1 is not None
    assert u1["name"] == "YESAIAH BATHULA"
    assert u1["email"] == "yesaiahb@nrtec.in"
    assert u1["phone"] == "8790424793"

    u2 = await db.users.find_one({"mentor_id": "2505104"})
    assert u2 is not None
    assert u2["name"] == "NAGOOR BABU SHAIK"
    assert u2["email"] == "nagoorbabusk@nrtec.in"
    assert u2["phone"] == "8790424794"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("password", "created", "failed"),
    [
        ("Abc123!@", 1, 0),
        ("MentorPass1!", 1, 0),
        ("Short7!", 0, 1),
        ("MentorPassword1!", 0, 1),
    ],
)
async def test_mentor_import_password_must_be_8_to_12_characters(password, created, failed):
    csv_data = (
        "NAME,ID/EMPLOYEE ID,MAIL ID/ EMAIL,PASSWORD\n"
        f"Test Mentor,991001,test-{len(password)}@example.invalid,{password}\n"
    )
    result = await parse_and_import_mentor_excel(
        csv_data.encode("utf-8"), "password_limits.csv", "test-admin"
    )
    assert result["created"] == created
    assert result["failed"] == failed

    user = await get_database().users.find_one({"mentor_id": "991001"})
    if created:
        assert user is not None
        assert verify_password(password, user["password_hash"])
    else:
        assert user is None
        assert "8-12 characters" in result["errors"][0]["errors"][0]


@pytest.mark.asyncio
async def test_mentor_without_password_gets_employee_id_login_and_hashed_default(client: AsyncClient):
    csv_data = "NAME,ID/EMPLOYEE ID,MAIL ID/ EMAIL\nDefault Mentor,992001,default-mentor@example.invalid\n"
    result = await parse_and_import_mentor_excel(
        csv_data.encode("utf-8"), "default_mentor.csv", "test-admin"
    )
    assert result["created"] == 1
    assert result["failed"] == 0

    user = await get_database().users.find_one({"employee_id": "992001"})
    assert user is not None
    assert user["mentor_id"] == "992001"
    assert verify_password(DEFAULT_MENTOR_PASSWORD, user["password_hash"])
    assert user["password_hash"] != DEFAULT_MENTOR_PASSWORD

    login = await client.post(
        "/api/auth/login",
        json={"email": "992001", "password": DEFAULT_MENTOR_PASSWORD, "portal": "MENTOR"},
    )
    assert login.status_code == 200
    assert login.json()["data"]["user"]["employeeId"] == "992001"


@pytest.mark.asyncio
async def test_all_invalid_mentor_import_returns_rejected_row_summary(client: AsyncClient):
    db = get_database()
    admin = await db.users.insert_one({
        "name": "Import Test Admin",
        "email": "mentor-import-rejections@example.invalid",
        "role": UserRole.ADMIN.value,
        "is_active": True,
    })
    token = create_access_token({"sub": str(admin.inserted_id), "role": UserRole.ADMIN.value})
    response = await client.post(
        "/api/admin/mentors/import",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("invalid-mentors.csv", b"NAME,ID/EMPLOYEE ID,MAIL ID/ EMAIL\n,991003,,\n", "text/csv")},
    )
    assert response.status_code == 200, response.text
    summary = response.json()["data"]
    assert summary["created"] == 0
    assert summary["failed"] == 1
    assert "Mentor Name is required." in summary["errors"][0]["errors"]
    assert await db.users.find_one({"mentor_id": "991003"}) is None




