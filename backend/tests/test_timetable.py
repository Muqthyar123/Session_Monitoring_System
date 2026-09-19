import io
import openpyxl
import pytest
from app.services.excel_service import parse_and_import_timetable_excel
from app.db.mongodb import get_database


def create_matrix_timetable_excel_bytes() -> bytes:
    """Helper to construct an in-memory openpyxl workbook matching the College Matrix Grid format."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "CSE-A"

    # Title block
    ws["A1"] = "NARASARAOPETA ENGINEERING COLLEGE :: NARASARAOPET"
    ws["A2"] = "(AUTONOMOUS)"
    ws["A3"] = "Department of Computer Science & Engineering"
    ws["A4"] = "ACADEMIC YEAR : 2026-2027 II SEMESTER"
    ws["A5"] = "II B.Tech [CSE - A] II SEMESTER TIME TABLE"
    ws["A6"] = "With effect from : 03-08-2026"

    # Header Row (Row 7)
    headers = ["DAY", "1", "2", "Break", "3", "4", "Lunch", "5", "6", "7"]
    for col_idx, h in enumerate(headers, start=1):
        ws.cell(row=7, column=col_idx, value=h)

    # Time Row (Row 8)
    times = ["", "09:10 - 10:00", "10:00 - 10:50", "10:50 - 11:00", "11:00 - 11:50", "11:50 - 12:40", "12:40 - 01:30", "01:30 - 02:20", "02:20 - 03:10", "03:10 - 04:00"]
    for col_idx, t in enumerate(times, start=1):
        ws.cell(row=8, column=col_idx, value=t)

    # Days rows
    # Tuesday row (Row 9)
    tue_row = ["T U E", "DMGT (2103)", "ADS&AA (2103)", "BREAK", "UHV-UV (2103)", "ADS&AA (2103)", "LUNCH", "DL&CO (2103)", "JAVA (2103)", "DL&CO (2103)"]
    for col_idx, val in enumerate(tue_row, start=1):
        ws.cell(row=9, column=col_idx, value=val)

    # Thursday row (Row 10) - Merged Python Lab with multiline text across Period 1 & 2
    ws.cell(row=10, column=1, value="T H U")
    ws.merge_cells("B10:C10")  # Merge Period 1 and 2
    ws.cell(row=10, column=2, value="PYTHON LAB\n(2201 LAB)")
    ws.cell(row=10, column=4, value="BREAK")
    ws.cell(row=10, column=5, value="DMGT (2103)")
    ws.cell(row=10, column=6, value="ADS&AA (2103)")
    ws.cell(row=10, column=7, value="LUNCH")
    ws.cell(row=10, column=8, value="JAVA (2103)")
    ws.cell(row=10, column=9, value="DMGT (2103)")
    ws.cell(row=10, column=10, value="JAVA (2103)")

    # Faculty Legend (Rows 12-15)
    ws.cell(row=12, column=1, value="ADS&AA : M.VENKATA RAO")
    ws.cell(row=12, column=5, value="DMGT : V.Radha")
    ws.cell(row=13, column=1, value="DL&CO : B.NAGAIAH")
    ws.cell(row=13, column=5, value="JAVA : V.MAHESH BABU")
    ws.cell(row=14, column=1, value="PYTHON LAB : M.SATHYAM REDDY")
    ws.cell(row=14, column=5, value="UHV-UV : Dr.P.PATTABHIRAM")

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


@pytest.mark.asyncio
async def test_matrix_grid_timetable_import():
    file_bytes = create_matrix_timetable_excel_bytes()
    res = await parse_and_import_timetable_excel(file_bytes, "college_timetable.xlsx", "actor-123")

    assert res["inserted"] > 0
    assert res["failed"] == 0

    db = get_database()
    # Check auto-upsert in db.sections
    sec_doc = await db.sections.find_one({"section_name": "CSE-A"})
    assert sec_doc is not None
    assert sec_doc["year"] == "2nd Year"

    # Check inserted Tuesday records
    records = await db.timetables.find({"section": "CSE-A", "day": "Tuesday"}).sort("period", 1).to_list(100)
    assert len(records) == 7

    # Tuesday Period 1: DMGT by V.Radha in 2103
    p1 = next(r for r in records if r["period"] == 1)
    assert p1["subject"] == "DMGT"
    assert p1["faculty"] == "V.Radha"
    assert p1["room"] == "2103"
    assert p1["start_time"] == "09:10"
    assert p1["end_time"] == "10:00"

    # Tuesday Period 5: DL&CO (afternoon PM time 13:30)
    p5 = next(r for r in records if r["period"] == 5)
    assert p5["subject"] == "DL&CO"
    assert p5["faculty"] == "B.NAGAIAH"
    assert p5["start_time"] == "13:30"
    assert p5["end_time"] == "14:20"

    # Check Thursday merged Python Lab records (Periods 1 & 2)
    thu_records = await db.timetables.find({"section": "CSE-A", "day": "Thursday"}).sort("period", 1).to_list(100)
    p1_thu = next(r for r in thu_records if r["period"] == 1)
    p2_thu = next(r for r in thu_records if r["period"] == 2)

    assert p1_thu["subject"] == "PYTHON LAB"
    assert p1_thu["faculty"] == "M.SATHYAM REDDY"
    assert p1_thu["room"] == "2201 LAB"

    assert p2_thu["subject"] == "PYTHON LAB"
    assert p2_thu["faculty"] == "M.SATHYAM REDDY"
    assert p2_thu["room"] == "2201 LAB"
