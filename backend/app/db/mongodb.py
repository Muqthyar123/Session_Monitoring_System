import asyncio
import atexit
import logging
from datetime import datetime, timezone
import os
from pathlib import Path
import threading
from typing import Optional

import certifi
from bson import json_util
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
try:
    from mongomock_motor import AsyncMongoMockClient
    import mongomock
except ImportError:
    AsyncMongoMockClient = None
    mongomock = None

from app.core.config import settings
from app.core.security import hash_password

logger = logging.getLogger("fams.db")

DATA_DIR = Path(settings.DATA_DIR)
DB_STORE_PATH = Path(settings.DB_STORE_FILE)
UPLOAD_DIR = Path(settings.UPLOAD_DIR)

_save_timer: Optional[threading.Timer] = None
_save_lock = threading.Lock()
_is_persistence_installed = False


class MongoManager:
    client = None
    db: AsyncIOMotorDatabase = None
    is_mock_mode: bool = False


db_manager = MongoManager()


def save_mock_db_to_disk_sync():
    """Synchronously serializes all in-memory collections and writes them atomically to DB_STORE_PATH."""
    if db_manager.db is None or not db_manager.is_mock_mode:
        return

    try:
        sync_db = getattr(db_manager.db, "delegate", None)
        if sync_db is None:
            return

        DATA_DIR.mkdir(parents=True, exist_ok=True)

        data = {}
        for cname in sync_db.list_collection_names():
            data[cname] = list(sync_db[cname].find())

        json_bytes = json_util.dumps(data, indent=2).encode("utf-8")
        tmp_path = DB_STORE_PATH.with_suffix(".tmp")

        with open(tmp_path, "wb") as f:
            f.write(json_bytes)
            f.flush()
            os.fsync(f.fileno())

        if tmp_path.exists():
            tmp_path.replace(DB_STORE_PATH)

        logger.debug(
            "Persisted mock database to %s (%d collections, %d bytes)",
            DB_STORE_PATH.name,
            len(data),
            len(json_bytes),
        )
    except Exception as e:
        logger.error("Failed to persist mock database to disk: %s", str(e), exc_info=True)


async def save_mock_db_to_disk():
    """Asynchronous wrapper around save_mock_db_to_disk_sync to prevent blocking the event loop."""
    await asyncio.to_thread(save_mock_db_to_disk_sync)


def schedule_db_save(delay: float = 0.5):
    """Debounces disk persistence across rapid burst operations."""
    global _save_timer
    if db_manager.db is None or not db_manager.is_mock_mode:
        return

    with _save_lock:
        if _save_timer is not None:
            try:
                _save_timer.cancel()
            except Exception:
                pass
        _save_timer = threading.Timer(delay, save_mock_db_to_disk_sync)
        _save_timer.daemon = True
        _save_timer.start()


def load_mock_db_from_disk_sync(db) -> bool:
    """Restores database collections and documents from DB_STORE_PATH if the file exists."""
    if not DB_STORE_PATH.exists():
        return False

    try:
        sync_db = getattr(db, "delegate", None)
        if sync_db is None:
            return False

        with open(DB_STORE_PATH, "rb") as f:
            raw = f.read()

        if not raw.strip():
            return False

        data = json_util.loads(raw.decode("utf-8"))
        if not isinstance(data, dict):
            return False

        for cname, docs in data.items():
            sync_db[cname].delete_many({})
            if docs and isinstance(docs, list):
                sync_db[cname].insert_many(docs)

        logger.info(
            "Restored mock database successfully from %s (%d collections)",
            DB_STORE_PATH,
            len(data),
        )
        return True
    except Exception as e:
        logger.error("Failed to load mock database from %s: %s", DB_STORE_PATH, str(e), exc_info=True)
        return False


def install_mock_db_persistence():
    """Monkey-patches mongomock collection mutation methods so all writes trigger scheduled persistence."""
    global _is_persistence_installed
    if _is_persistence_installed:
        return

    try:
        import mongomock.collection

        write_methods = [
            "insert_one",
            "insert_many",
            "update_one",
            "update_many",
            "replace_one",
            "delete_one",
            "delete_many",
            "find_one_and_update",
            "find_one_and_delete",
            "find_one_and_replace",
            "drop",
            "drop_indexes",
            "bulk_write",
        ]

        for method_name in write_methods:
            orig = getattr(mongomock.collection.Collection, method_name, None)
            if not orig or getattr(orig, "_is_persisted_wrapped", False):
                continue

            def make_wrapper(orig_fn):
                def wrapper(self, *args, **kwargs):
                    res = orig_fn(self, *args, **kwargs)
                    schedule_db_save()
                    return res

                wrapper._is_persisted_wrapped = True
                return wrapper

            setattr(mongomock.collection.Collection, method_name, make_wrapper(orig))

        _is_persistence_installed = True
        logger.info("Installed mock database disk persistence hooks.")
    except Exception as e:
        logger.warning("Failed to install mock persistence hooks: %s", str(e))


async def seed_from_uploaded_files_if_needed(db):
    """If database is empty and files exist in UPLOAD_DIR or Downloads, import them immediately."""
    from app.services.excel_service import (
        parse_and_import_mentor_excel,
        parse_and_import_student_excel,
        parse_and_import_timetable_excel,
    )
    from app.services.mentor_mapping_service import (
        preview_mentor_mappings,
        commit_mentor_mappings,
    )
    from app.schemas.mentor_mapping import MentorMappingConfirmRequest

    # Check if we already have timetables or students
    tt_count = await db.timetables.count_documents({})
    stu_count = await db.students.count_documents({})
    if tt_count > 0 or stu_count > 0:
        return

    admin_user = await db.users.find_one({"role": "ADMIN"})
    admin_id = str(admin_user["_id"]) if admin_user else "system-root"

    upload_dir = Path(settings.UPLOAD_DIR)
    downloads_dir = Path.home() / "Downloads"

    def find_file(filename: str) -> Optional[Path]:
        p1 = upload_dir / filename
        if p1.exists():
            return p1
        p2 = downloads_dir / filename
        if p2.exists():
            return p2
        return None

    # 1. Faculty / Mentors
    fac_path = find_file("CSE FACULTY LIST.xls")
    if fac_path:
        try:
            with open(fac_path, "rb") as f:
                content = f.read()
            res = await parse_and_import_mentor_excel(content, fac_path.name, admin_id)
            logger.info("Auto-seeded mentors from %s: %s", fac_path.name, res)
        except Exception as e:
            logger.warning("Auto-seed mentors warning: %s", str(e))

    # 2. Students
    stu_path = find_file("Students_Roster.csv")
    if stu_path:
        try:
            with open(stu_path, "rb") as f:
                content = f.read()
            res = await parse_and_import_student_excel(content, stu_path.name, admin_id)
            logger.info("Auto-seeded students from %s: %s", stu_path.name, res)
        except Exception as e:
            logger.warning("Auto-seed students warning: %s", str(e))

    # 3. Timetables
    tt_names = [
        "14-08-2026 MASTER  TIME TABLE  - 2 YEAR -Updated.xlsx",
        "3  YEAR - TIME TABLES - 51026-26-1 SEM.xlsx",
        "Updated 4th Master Time Tables - 05-10-2026.xlsx",
    ]
    for ttf in tt_names:
        tt_path = find_file(ttf)
        if tt_path:
            try:
                with open(tt_path, "rb") as f:
                    content = f.read()
                res = await parse_and_import_timetable_excel(content, tt_path.name, admin_id)
                logger.info("Auto-seeded timetable from %s: %s inserted", tt_path.name, res.get("inserted", 0))
            except Exception as e:
                logger.warning("Auto-seed timetable warning for %s: %s", ttf, str(e))

    # 4. Mentor Mappings
    map_path = find_file("Mentor_Student_Mapping_Template.xlsx")
    if map_path:
        try:
            with open(map_path, "rb") as f:
                content = f.read()
            prev = await preview_mentor_mappings(content, map_path.name)
            if prev.valid_rows > 0:
                req = MentorMappingConfirmRequest(
                    mode="ADD_UPDATE",
                    rows=[r.model_dump() for r in prev.rows if r.status == "VALID"],
                )
                res_map = await commit_mentor_mappings(req, {"id": admin_id, "email": "admin@example.com"})
                logger.info("Auto-seeded mentor mappings from %s: %s", map_path.name, res_map)
        except Exception as e:
            logger.warning("Auto-seed mentor mappings warning: %s", str(e))


async def seed_in_memory_db(db):
    """Seed initial Root Admin user into database, keeping all section, timetable, and CR/LR collections fresh."""
    now = datetime.now(timezone.utc)
    admin_pwd_hash = hash_password("demo1234")

    # Root System Administrator
    existing_admin = await db.users.find_one({"role": "ADMIN"})
    if not existing_admin:
        await db.users.insert_one(
            {
                "name": "System Administrator",
                "email": "admin@example.com",
                "password_hash": admin_pwd_hash,
                "role": "ADMIN",
                "roll_number": None,
                "phone": "9876543210",
                "year": None,
                "section": None,
                "is_active": True,
                "created_at": now,
                "updated_at": now,
            }
        )

    # Seed CR and LR accounts for sections (II-CSE-A to II-CSE-J) if not already present.
    # Default password for each CR/LR is their roll number (e.g. 22CSA01 for CR of II-CSE-A).
    # Login can be done using email OR roll number.
    sections = [
        "II-CSE-A",
        "II-CSE-B",
        "II-CSE-C",
        "II-CSE-D",
        "II-CSE-E",
        "II-CSE-F",
        "II-CSE-G",
        "II-CSE-H",
        "II-CSE-I",
        "II-CSE-J",
    ]

    for sec in sections:
        sec_letter = sec.split("-")[-1]
        slug = sec_letter.lower()

        cr_roll = f"22CS{sec_letter}01"
        lr_roll = f"22CS{sec_letter}02"
        cr_email = f"cr.{slug}@college.edu"
        lr_email = f"lr.{slug}@college.edu"

        # Password = roll number (unique per CR/LR, not a shared dummy password)
        cr_pwd_hash = hash_password(cr_roll)
        lr_pwd_hash = hash_password(lr_roll)

        # CR User — insert if absent, update password/email if stale dummy credentials exist
        cr_existing = await db.users.find_one(
            {"$or": [{"email": cr_email}, {"roll_number": cr_roll, "role": "CR"}]}
        )
        if not cr_existing:
            cr_res = await db.users.insert_one(
                {
                    "name": f"{sec} CR",
                    "email": cr_email,
                    "password_hash": cr_pwd_hash,
                    "role": "CR",
                    "roll_number": cr_roll,
                    "phone": "9876543211",
                    "year": "2nd Year",
                    "section": sec,
                    "is_active": True,
                    "created_at": now,
                    "updated_at": now,
                }
            )
            cr_id = str(cr_res.inserted_id)
        else:
            cr_id = str(cr_existing["_id"])
            # Migrate: update email to new pattern and set roll-number password if it was the old demo password
            update_fields: dict = {"email": cr_email, "section": sec, "updated_at": now}
            if cr_existing.get("password_hash") == hash_password("demo1234"):
                update_fields["password_hash"] = cr_pwd_hash
            await db.users.update_one({"_id": cr_existing["_id"]}, {"$set": update_fields})

        # LR User — insert if absent, update password/email if stale dummy credentials exist
        lr_existing = await db.users.find_one(
            {"$or": [{"email": lr_email}, {"roll_number": lr_roll, "role": "LR"}]}
        )
        if not lr_existing:
            lr_res = await db.users.insert_one(
                {
                    "name": f"{sec} LR",
                    "email": lr_email,
                    "password_hash": lr_pwd_hash,
                    "role": "LR",
                    "roll_number": lr_roll,
                    "phone": "9876543212",
                    "year": "2nd Year",
                    "section": sec,
                    "is_active": True,
                    "created_at": now,
                    "updated_at": now,
                }
            )
            lr_id = str(lr_res.inserted_id)
        else:
            lr_id = str(lr_existing["_id"])
            # Migrate: update email to new pattern and set roll-number password if it was the old demo password
            update_fields = {"email": lr_email, "section": sec, "updated_at": now}
            if lr_existing.get("password_hash") == hash_password("demo1234"):
                update_fields["password_hash"] = lr_pwd_hash
            await db.users.update_one({"_id": lr_existing["_id"]}, {"$set": update_fields})

        # Upsert Section document
        await db.sections.update_one(
            {"section_name": sec},
            {
                "$set": {
                    "year": "2nd Year",
                    "branch": "CSE",
                    "department": "CSE",
                    "section_name": sec,
                    "assigned_cr_id": cr_id,
                    "assigned_lr_id": lr_id,
                    "is_active": True,
                    "updated_at": now,
                },
                "$setOnInsert": {"created_at": now},
            },
            upsert=True,
        )


async def ensure_indexes(db):
    """Ensure database indexes exist for high-performance querying."""
    try:
        await db.sessions.create_index([("date", 1), ("section", 1)])
        await db.sessions.create_index([("date", 1), ("start_time", 1)])
        await db.sessions.create_index([("section", 1)])
        await db.sessions.create_index([("status", 1)])
        await db.timetables.create_index([("section", 1), ("day", 1), ("period", 1)])
        await db.timetables.create_index([("section", 1)])
        await db.timetables.create_index([("year", 1)])
        await db.users.create_index([("email", 1)])
        await db.users.create_index([("roll_number", 1)])
        await db.users.create_index([("mentor_id", 1)])
        await db.users.create_index([("role", 1)])
        await db.students.create_index([("roll_number", 1)])
        await db.students.create_index([("section", 1)])
        await db.students.create_index([("year", 1)])
        await db.student_attendance.create_index([("year", 1), ("section", 1), ("date", 1)])
        await db.student_attendance.create_index([("roll_number", 1)])
        await db.student_attendance.create_index([("status", 1)])
        await db.student_attendance_submissions.create_index([("year", 1), ("section", 1), ("date", 1)])
        await db.admin_alerts.create_index([("created_at", -1)])
        logger.info("MongoDB indexes verified successfully.")
    except Exception as e:
        logger.warning("Index creation warning: %s", str(e))


async def connect_to_mongo():
    db_name = settings.get_database_name()
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    logger.info("Connecting to MongoDB at %s...", settings.MONGODB_URI)

    client_kwargs = {
        "serverSelectionTimeoutMS": settings.MONGODB_SERVER_SELECTION_TIMEOUT_MS,
    }

    if "mongodb+srv" in settings.MONGODB_URI or "tls=true" in settings.MONGODB_URI.lower():
        client_kwargs["tlsCAFile"] = certifi.where()

    # Attempt connecting to external MongoDB
    try:
        real_client = AsyncIOMotorClient(settings.MONGODB_URI, **client_kwargs)
        await real_client.admin.command("ping")
        db_manager.client = real_client
        db_manager.db = real_client[db_name]
        db_manager.is_mock_mode = False
        await ensure_indexes(db_manager.db)
        await seed_in_memory_db(db_manager.db)
        logger.info("MongoDB connection successful. Connected to real database: %s", db_name)
        return
    except Exception as e:
        logger.warning(
            "Primary MongoDB connection attempt failed (%s). Attempting TLS fallback...",
            str(e),
        )
        try:
            client_kwargs["tlsAllowInvalidCertificates"] = True
            real_client = AsyncIOMotorClient(settings.MONGODB_URI, **client_kwargs)
            await real_client.admin.command("ping")
            db_manager.client = real_client
            db_manager.db = real_client[db_name]
            db_manager.is_mock_mode = False
            await ensure_indexes(db_manager.db)
            await seed_in_memory_db(db_manager.db)
            logger.info("MongoDB connection successful with TLS options. Connected to database: %s", db_name)
            return
        except Exception as retry_err:
            logger.warning(
                "Unable to reach external MongoDB Atlas (%s). Switching to Persistent Mock Database Mode...",
                str(retry_err),
            )

    # In-Memory Fallback Mock Database with Durable File-Backed Persistence
    if AsyncMongoMockClient is None:
        raise RuntimeError(
            "Neither real MongoDB nor 'mongomock-motor' is available. "
            "Please check your MONGODB_URI in environment variables or add 'mongomock-motor' to requirements.txt."
        )

    mock_client = AsyncMongoMockClient()
    db_manager.client = mock_client
    db_manager.db = mock_client[db_name]
    db_manager.is_mock_mode = True

    # 1. Install mutation persistence hooks
    install_mock_db_persistence()

    # 2. Load stored collections from disk if db_store.json exists
    loaded = load_mock_db_from_disk_sync(db_manager.db)

    # 3. If no stored snapshot on disk yet, auto-seed from uploaded source files
    if not loaded:
        await seed_from_uploaded_files_if_needed(db_manager.db)

    # 4. Ensure admin and base accounts are intact
    await seed_in_memory_db(db_manager.db)
    await ensure_indexes(db_manager.db)

    # 5. Ensure all existing sections have branch & department populated
    try:
        all_secs = await db_manager.db.sections.find({}).to_list(1000)
        for s in all_secs:
            s_name = s.get("section_name", "")
            b = s.get("branch") or s.get("department")
            if not b:
                b = "CSE"
                if "-" in s_name:
                    parts = s_name.split("-")
                    if len(parts) >= 2 and parts[1].isalpha():
                        b = parts[1].upper()
                await db_manager.db.sections.update_one(
                    {"_id": s["_id"]},
                    {"$set": {"branch": b, "department": b}}
                )
    except Exception as sec_sync_err:
        logger.warning("Section branch sync warning: %s", str(sec_sync_err))

    # 6. Flush current database state to disk
    save_mock_db_to_disk_sync()

    logger.info(
        "Activated Persistent Mock Database Mode. Database '%s' backed by '%s'.",
        db_name,
        DB_STORE_PATH,
    )


async def close_mongo_connection():
    if db_manager.is_mock_mode:
        save_mock_db_to_disk_sync()
    if db_manager.client:
        logger.info("Closing MongoDB connection.")
        db_manager.client.close()
        logger.info("MongoDB connection closed.")


# Ensure database state is saved on clean process exit
atexit.register(save_mock_db_to_disk_sync)


def get_database() -> AsyncIOMotorDatabase:
    if db_manager.db is None:
        raise RuntimeError("Database connection has not been initialized.")
    return db_manager.db
