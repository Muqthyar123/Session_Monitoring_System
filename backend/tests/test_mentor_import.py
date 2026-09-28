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
async def test_mentor_import_binary_xls():
    import os
    file_path = r"C:\Users\Shaik Meera Muqthyar\.gemini\antigravity\brain\2e72ca59-040a-4bdf-b2f2-8301c1fb5322\.user_uploaded\media_1790617556901.xls"
    if os.path.exists(file_path):
        with open(file_path, "rb") as f:
            file_bytes = f.read()
        res = await parse_and_import_mentor_excel(file_bytes, "media_1790617556901.xls", "admin123")
        assert res["created"] + res["updated"] >= 50
        assert res["failed"] == 0



