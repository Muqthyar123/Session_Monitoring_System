import logging
from datetime import datetime, timezone
from app.core.security import hash_password
from app.db.mongodb import get_database
from app.schemas.user import UserRole

logger = logging.getLogger("fams.migration")

DEFAULT_DEPARTMENTS_DATA = [
    {"code": "CSE", "name": "Computer Science & Engineering"},
    {"code": "ECE", "name": "Electronics & Communication Engineering"},
    {"code": "IT", "name": "Information Technology"},
    {"code": "AIDS", "name": "Artificial Intelligence & Data Science"},
    {"code": "AIML", "name": "Artificial Intelligence & Machine Learning"},
    {"code": "EEE", "name": "Electrical & Electronics Engineering"},
    {"code": "MECH", "name": "Mechanical Engineering"},
    {"code": "CIVIL", "name": "Civil Engineering"},
    {"code": "CSBS", "name": "Computer Science & Business Systems"},
]

DEFAULT_SUPER_ADMIN_EMAIL = "superadmin@fams.edu"
DEFAULT_SUPER_ADMIN_PASSWORD = "SuperAdmin@123"


async def run_branch_and_superadmin_migrations():
    """
    Safely migrates and initializes:
    1. Default institutional Site ('Main Campus')
    2. Branches collection populated and synced with departments
    3. Backfill missing branch fields on students, sections, and mentors
    4. Default Super Admin account provisioned if none exists
    """
    db = get_database()
    now = datetime.now(timezone.utc)

    # 1. Initialize default Site
    default_site = await db.sites.find_one({"code": "MAIN"})
    if not default_site:
        site_doc = {
            "code": "MAIN",
            "name": "Main Campus",
            "location": "College Campus, Academic Block",
            "address": "College Road, Tech City",
            "contact_email": "admin@fams.edu",
            "contact_phone": "+91 98765 43210",
            "description": "Primary Institutional Campus Site",
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
        res = await db.sites.insert_one(site_doc)
        default_site_id = str(res.inserted_id)
        logger.info("Initialized default Site: Main Campus (MAIN).")
    else:
        default_site_id = str(default_site["_id"])

    # 2. Initialize and sync branches
    for dept in DEFAULT_DEPARTMENTS_DATA:
        code = dept["code"]
        name = dept["name"]
        existing_branch = await db.branches.find_one({"code": code})
        if not existing_branch:
            # Check if an HOD already exists in users
            hod_user = await db.users.find_one({
                "role": UserRole.ADMIN.value,
                "$or": [{"branch": code}, {"department": code}],
                "designation": {"$regex": "HOD|HEAD", "$options": "i"},
            })
            b_doc = {
                "code": code,
                "name": name,
                "site_id": default_site_id,
                "site_code": "MAIN",
                "site_name": "Main Campus",
                "hod_id": str(hod_user["_id"]) if hod_user else None,
                "hod_name": hod_user.get("name") if hod_user else None,
                "hod_email": hod_user.get("email") if hod_user else None,
                "hod_phone": hod_user.get("phone") if hod_user else None,
                "description": f"{name} Department",
                "is_active": True,
                "created_at": now,
                "updated_at": now,
            }
            await db.branches.insert_one(b_doc)
            logger.info("Initialized branch: %s", code)

        # Also ensure departments collection is populated
        existing_dept = await db.departments.find_one({"code": code})
        if not existing_dept:
            await db.departments.insert_one({
                "code": code,
                "name": name,
                "coordinator_id": None,
                "coordinator_name": None,
                "coordinator_email": None,
                "is_active": True,
                "created_at": now,
                "updated_at": now,
            })

    # 3. Ensure students have a valid branch (default to CSE or infer from section)
    students_without_branch = await db.students.count_documents({
        "$or": [{"branch": None}, {"branch": ""}, {"branch": {"$exists": False}}]
    })
    if students_without_branch > 0:
        logger.info("Found %d students without branch. Backfilling...", students_without_branch)
        # Update matching sections or default to CSE
        await db.students.update_many(
            {"$or": [{"branch": None}, {"branch": ""}, {"branch": {"$exists": False}}]},
            {"$set": {"branch": "CSE", "updated_at": now}}
        )

    # 4. Ensure sections have a valid branch
    sections_without_branch = await db.sections.count_documents({
        "$or": [{"branch": None}, {"branch": ""}, {"branch": {"$exists": False}}]
    })
    if sections_without_branch > 0:
        logger.info("Found %d sections without branch. Backfilling...", sections_without_branch)
        await db.sections.update_many(
            {"$or": [{"branch": None}, {"branch": ""}, {"branch": {"$exists": False}}]},
            {"$set": {"branch": "CSE", "department": "CSE", "updated_at": now}}
        )

    # 5. Provision default Super Admin account if none exists
    superadmin_count = await db.users.count_documents({"role": UserRole.SUPER_ADMIN.value})
    if superadmin_count == 0:
        superadmin_doc = {
            "name": "Super Administrator",
            "email": DEFAULT_SUPER_ADMIN_EMAIL,
            "password_hash": hash_password(DEFAULT_SUPER_ADMIN_PASSWORD),
            "role": UserRole.SUPER_ADMIN.value,
            "designation": "System Super Admin",
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
        await db.users.insert_one(superadmin_doc)
        logger.info(
            "Auto-provisioned default Super Admin: %s (password: %s)",
            DEFAULT_SUPER_ADMIN_EMAIL,
            DEFAULT_SUPER_ADMIN_PASSWORD,
        )
    else:
        logger.info("Super Admin account exists (%d registered).", superadmin_count)
