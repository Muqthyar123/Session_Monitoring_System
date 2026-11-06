import logging
from datetime import datetime, timezone
from app.db.mongodb import get_database

logger = logging.getLogger("fams.migration")

async def run_branch_and_superadmin_migrations():
    """
    Safely migrates and initializes:
    1. Default institutional Site ('Main Campus')
    Only create the neutral main site when absent. Legacy record ownership is not
    inferred here: unknown branch/department assignments need operator review.
    Super Admin accounts are provisioned explicitly through seed_db.py.
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
        logger.info("Initialized default Site: Main Campus (MAIN).")
    else:
        logger.info("Main site already exists; legacy ownership fields were left unchanged.")
