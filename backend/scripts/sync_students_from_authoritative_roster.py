"""Refresh student records from the authoritative uploaded CSE workbook.

Run with the backend virtualenv. The script updates/creates students by roll
number and reports unmatched rows; it never prints student PII.
"""
import argparse
import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.mongodb import close_mongo_connection, connect_to_mongo, get_database, db_manager
from app.services.excel_service import extract_raw_rows_from_file, parse_and_import_student_excel


async def run(apply: bool, allow_mock: bool) -> None:
    logging.disable(logging.CRITICAL)
    source = Path(__file__).resolve().parents[1] / "data" / "uploads" / "CSE - DATA.xlsx"
    if not source.exists():
        raise SystemExit(f"Authoritative roster not found: {source}")
    content = source.read_bytes()
    rows = extract_raw_rows_from_file(content, source.name)
    if not rows:
        raise SystemExit("Roster workbook could not be read.")

    await connect_to_mongo()
    try:
        if db_manager.is_mock_mode and not allow_mock:
            raise SystemExit("Backend fell back to mock mode. Refusing to update a local snapshot; pass --allow-mock only when that is intended.")
        db = get_database()
        before = await db.students.count_documents({})
        admin = await db.users.find_one({"role": "ADMIN"})
        actor_id = str(admin["_id"]) if admin else "authoritative-roster-sync"
        print(f"Source workbook: {source.name}")
        print(f"Non-empty source rows: {sum(1 for row in rows[1:] if any(row))}")
        print(f"Student records before sync: {before}")
        if not apply:
            print("Dry run only. Re-run with --apply to update students.")
            return

        result = await parse_and_import_student_excel(content, source.name, actor_id)
        after = await db.students.count_documents({})
        print(f"Created: {result['created']}; updated: {result['updated']}; rejected rows: {result['failed']}")
        print(f"Student records after sync: {after}")
        if result["failed"]:
            print("Some roster rows were rejected. See the import audit/errors before relying on those records.")
    finally:
        await close_mongo_connection()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Write roster changes to the configured database.")
    parser.add_argument("--allow-mock", action="store_true", help="Allow updating the local mock DB snapshot if MongoDB is unavailable.")
    args = parser.parse_args()
    asyncio.run(run(args.apply, args.allow_mock))
