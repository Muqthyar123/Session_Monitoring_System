import pytest
from app.services.excel_service import parse_and_import_mentor_excel
from app.db.mongodb import get_database

SAMPLE_1_CSV = """NON-TEACHING,,,,,,
S.NO,NAME,ID,MAIL ID,DESIGN,BRANCH,MOBILE NO
1.0,NAGESWARA RAO KUKKAMUDI,705201,knag1999@nrtec.in,COM.OPERATOR (CAMU COORDINATOR),CSE,9705672051
2.0,SUBASH CHANDRA POTTURI,1005201,subashpotturi@gmail.com,HARDWARE,CSE,9885013488
"""

SAMPLE_2_CSV = """S.NO,NAME,ID/EMPLOYEE ID,MAIL ID/ EMAIL,DESIGN/DESIGNATION,BRANCH/DEPARTMENT,MOBILE NO
1.0,SIVA NAGESWARA RAO SIVARATRI,605101,drssnr@nrtec.in,PROFESSOR,CSE,8977987777
2.0,MOTURI SIREESHA,905101,moturisireesha@gmail.com,ASSOCIATE PROFESSOR,CSE,9492468445
"""

SAMPLE_3_CSV = """S.No,Name,User name,Email,Employee ID,Designation,Department,Mobile,Profile
1.0,SIVA NAGESWARA RAO SIVARATRI,605101,drssnr@nrtec.in,605101,PROFESSOR,CSE,8977987777,"Administrator, Administrator"
2.0,NAGESWARA RAO KUKKAMUDI,705201,knag1999@nrtec.in,705201,COM.OPERATOR,CSE,9705672051,"Course Coordinator"
"""


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
S.NO,NAME,ID/EMPLOYEE ID,MAIL ID/ EMAIL,DESIGN/DESIGNATION,BRANCH/DEPARTMENT,MOBILE NO
52.0,YESAIAHÂ BATHULA,2505103,â yesaiahb@nrtec.in,ASSISTANT PROFESSOR,CSE,Â 8790424793
53.0,NAGOOR BABUÂ Â SHAIK,2505104,â nagoorbabusk@nrtec.in,ASSISTANT PROFESSOR,CSE,8790424794
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




