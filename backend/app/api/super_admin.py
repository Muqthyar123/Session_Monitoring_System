import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.dependencies import require_roles
from app.core.security import hash_password
from app.db.mongodb import get_database
from app.schemas.branch import BranchCreate, BranchResponse, BranchUpdate
from app.schemas.common import ApiResponse
from app.schemas.hod import HODCreate, HODResetPassword, HODResponse, HODUpdate
from app.schemas.site import SiteCreate, SiteResponse, SiteUpdate
from app.schemas.user import UserRole

router = APIRouter(prefix="/super-admin", tags=["Super Admin"])


# =====================================================================
# Helper: Enrich Branch Counts & Details
# =====================================================================
async def _enrich_branch_details(doc: dict) -> dict:
    db = get_database()
    code = doc.get("code", "")
    b_id = str(doc["_id"])

    # Count students
    stu_count = await db.students.count_documents({
        "$or": [
            {"branch": code},
            {"branch": {"$regex": f"^{re.escape(code)}$", "$options": "i"}},
            {"department": code},
        ]
    })

    # Count sections
    sec_count = await db.sections.count_documents({
        "$or": [
            {"branch": code},
            {"branch": {"$regex": f"^{re.escape(code)}$", "$options": "i"}},
            {"department": code},
            {"section_name": {"$regex": f"-{re.escape(code)}-|^{re.escape(code)}-|{re.escape(code)}", "$options": "i"}},
        ]
    })

    # Count mentors
    mentor_count = await db.users.count_documents({
        "role": UserRole.MENTOR.value,
        "$or": [
            {"branch": code},
            {"branch": {"$regex": f"^{re.escape(code)}$", "$options": "i"}},
            {"department": code},
            {"department": {"$regex": f"^{re.escape(code)}$", "$options": "i"}},
        ]
    })

    # Resolve HOD info if not already in doc or if stale
    hod_id = doc.get("hod_id")
    hod_name = doc.get("hod_name")
    hod_email = doc.get("hod_email")
    hod_phone = doc.get("hod_phone")

    if not hod_id or not hod_name:
        # Search users for an HOD of this branch
        hod_user = await db.users.find_one({
            "role": UserRole.ADMIN.value,
            "$or": [
                {"branch": code},
                {"branch": {"$regex": f"^{re.escape(code)}$", "$options": "i"}},
                {"department": code},
            ],
            "designation": {"$regex": "HOD|HEAD", "$options": "i"},
        })
        if hod_user:
            hod_id = str(hod_user["_id"])
            hod_name = hod_user.get("name")
            hod_email = hod_user.get("email")
            hod_phone = hod_user.get("phone")
            await db.branches.update_one(
                {"_id": doc["_id"]},
                {"$set": {
                    "hod_id": hod_id,
                    "hod_name": hod_name,
                    "hod_email": hod_email,
                    "hod_phone": hod_phone,
                    "updated_at": datetime.now(timezone.utc),
                }}
            )

    doc["_id"] = b_id
    doc["student_count"] = stu_count
    doc["section_count"] = sec_count
    doc["mentor_count"] = mentor_count
    doc["hod_id"] = hod_id
    doc["hod_name"] = hod_name
    doc["hod_email"] = hod_email
    doc["hod_phone"] = hod_phone
    return doc


# =====================================================================
# 1. Super Admin Dashboard
# =====================================================================
@router.get("/dashboard", response_model=ApiResponse[Dict[str, Any]])
async def get_super_admin_dashboard(
    current_user: dict = Depends(require_roles([UserRole.SUPER_ADMIN])),
):
    db = get_database()

    total_branches = await db.branches.count_documents({})
    total_sites = await db.sites.count_documents({})
    total_students = await db.students.count_documents({})
    total_mentors = await db.users.count_documents({"role": UserRole.MENTOR.value})

    # Count HODs (Admins with branch assignment or designation HOD)
    total_hods = await db.users.count_documents({
        "role": UserRole.ADMIN.value,
        "$or": [
            {"branch": {"$exists": True, "$ne": None, "$ne": ""}},
            {"designation": {"$regex": "HOD|HEAD", "$options": "i"}},
        ]
    })

    # Fetch all branches and enrich statistics
    branches_cursor = db.branches.find({}).sort("code", 1)
    branch_stats = []
    async for b in branches_cursor:
        enriched = await _enrich_branch_details(b)
        branch_stats.append({
            "id": enriched["_id"],
            "code": enriched.get("code", ""),
            "name": enriched.get("name", ""),
            "site_name": enriched.get("site_name") or "Main Campus",
            "hod_name": enriched.get("hod_name") or "Unassigned",
            "hod_email": enriched.get("hod_email") or "—",
            "hod_phone": enriched.get("hod_phone") or "—",
            "student_count": enriched.get("student_count", 0),
            "mentor_count": enriched.get("mentor_count", 0),
            "section_count": enriched.get("section_count", 0),
            "is_active": enriched.get("is_active", True),
        })

    # Recent branches
    recent_branches_cursor = db.branches.find({}).sort("created_at", -1).limit(5)
    recent_branches = []
    async for b in recent_branches_cursor:
        recent_branches.append({
            "id": str(b["_id"]),
            "code": b.get("code", ""),
            "name": b.get("name", ""),
            "site_name": b.get("site_name") or "Main Campus",
            "created_at": b.get("created_at"),
            "is_active": b.get("is_active", True),
        })

    # Recent HODs
    recent_hods_cursor = db.users.find({
        "role": UserRole.ADMIN.value,
        "$or": [
            {"branch": {"$exists": True, "$ne": None, "$ne": ""}},
            {"designation": {"$regex": "HOD|HEAD", "$options": "i"}},
        ]
    }).sort("created_at", -1).limit(5)
    recent_hods = []
    async for h in recent_hods_cursor:
        recent_hods.append({
            "id": str(h["_id"]),
            "name": h.get("name", ""),
            "email": h.get("email", ""),
            "phone": h.get("phone") or "—",
            "branch_code": h.get("branch") or h.get("department") or "—",
            "created_at": h.get("created_at"),
            "is_active": h.get("is_active", True),
        })

    data = {
        "total_branches": total_branches,
        "total_sites": total_sites,
        "total_hods": total_hods,
        "total_mentors": total_mentors,
        "total_students": total_students,
        "branch_stats": branch_stats,
        "recent_branches": recent_branches,
        "recent_hods": recent_hods,
    }
    return ApiResponse(success=True, data=data, message="Dashboard loaded successfully.")


# =====================================================================
# 2. Sites Management
# =====================================================================
@router.get("/sites", response_model=ApiResponse[List[SiteResponse]])
async def list_sites(
    current_user: dict = Depends(require_roles([UserRole.SUPER_ADMIN])),
):
    db = get_database()
    cursor = db.sites.find({}).sort("code", 1)
    results = []
    async for doc in cursor:
        site_id = str(doc["_id"])
        site_code = doc.get("code", "")
        # Count branches belonging to this site
        branch_count = await db.branches.count_documents({
            "$or": [
                {"site_id": site_id},
                {"site_code": site_code},
                {"site_code": {"$regex": f"^{re.escape(site_code)}$", "$options": "i"}},
            ]
        })
        doc["_id"] = site_id
        doc["branch_count"] = branch_count
        results.append(SiteResponse(**doc))
    return ApiResponse(success=True, data=results)


@router.post("/sites", response_model=ApiResponse[SiteResponse], status_code=status.HTTP_201_CREATED)
async def create_site(
    data: SiteCreate,
    current_user: dict = Depends(require_roles([UserRole.SUPER_ADMIN])),
):
    db = get_database()
    code_clean = data.code.strip().upper()
    existing = await db.sites.find_one({"code": code_clean})
    if existing:
        raise HTTPException(status_code=400, detail=f"Site with code '{code_clean}' already exists.")

    now = datetime.now(timezone.utc)
    doc = {
        "code": code_clean,
        "name": data.name.strip(),
        "location": data.location.strip() if data.location else None,
        "address": data.address.strip() if data.address else None,
        "contact_email": data.contact_email.strip().lower() if data.contact_email else None,
        "contact_phone": data.contact_phone.strip() if data.contact_phone else None,
        "description": data.description.strip() if data.description else None,
        "is_active": data.is_active,
        "created_at": now,
        "updated_at": now,
    }
    res = await db.sites.insert_one(doc)
    doc["_id"] = str(res.inserted_id)
    doc["branch_count"] = 0
    return ApiResponse(success=True, data=SiteResponse(**doc), message="Site created successfully.")


@router.get("/sites/{site_id}", response_model=ApiResponse[SiteResponse])
async def get_site_details(
    site_id: str,
    current_user: dict = Depends(require_roles([UserRole.SUPER_ADMIN])),
):
    if not ObjectId.is_valid(site_id):
        raise HTTPException(status_code=400, detail="Invalid Site ID format.")
    db = get_database()
    doc = await db.sites.find_one({"_id": ObjectId(site_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Site not found.")

    doc["_id"] = str(doc["_id"])
    doc["branch_count"] = await db.branches.count_documents({"site_id": str(doc["_id"])})
    return ApiResponse(success=True, data=SiteResponse(**doc))


@router.put("/sites/{site_id}", response_model=ApiResponse[SiteResponse])
async def update_site(
    site_id: str,
    data: SiteUpdate,
    current_user: dict = Depends(require_roles([UserRole.SUPER_ADMIN])),
):
    if not ObjectId.is_valid(site_id):
        raise HTTPException(status_code=400, detail="Invalid Site ID format.")
    db = get_database()
    existing = await db.sites.find_one({"_id": ObjectId(site_id)})
    if not existing:
        raise HTTPException(status_code=404, detail="Site not found.")

    now = datetime.now(timezone.utc)
    updates: Dict[str, Any] = {"updated_at": now}

    if data.code is not None:
        code_clean = data.code.strip().upper()
        dup = await db.sites.find_one({"code": code_clean, "_id": {"$ne": ObjectId(site_id)}})
        if dup:
            raise HTTPException(status_code=400, detail=f"Site code '{code_clean}' already in use.")
        updates["code"] = code_clean

    if data.name is not None:
        updates["name"] = data.name.strip()
    if data.location is not None:
        updates["location"] = data.location.strip() if data.location else None
    if data.address is not None:
        updates["address"] = data.address.strip() if data.address else None
    if data.contact_email is not None:
        updates["contact_email"] = data.contact_email.strip().lower() if data.contact_email else None
    if data.contact_phone is not None:
        updates["contact_phone"] = data.contact_phone.strip() if data.contact_phone else None
    if data.description is not None:
        updates["description"] = data.description.strip() if data.description else None
    if data.is_active is not None:
        updates["is_active"] = data.is_active

    await db.sites.update_one({"_id": ObjectId(site_id)}, {"$set": updates})
    updated = await db.sites.find_one({"_id": ObjectId(site_id)})
    updated["_id"] = str(updated["_id"])
    updated["branch_count"] = await db.branches.count_documents({"site_id": site_id})

    # Sync site name and code to branches assigned to this site
    if data.name or data.code:
        sync_branch_updates = {}
        if "name" in updates:
            sync_branch_updates["site_name"] = updates["name"]
        if "code" in updates:
            sync_branch_updates["site_code"] = updates["code"]
        if sync_branch_updates:
            await db.branches.update_many({"site_id": site_id}, {"$set": sync_branch_updates})

    return ApiResponse(success=True, data=SiteResponse(**updated), message="Site updated successfully.")


@router.delete("/sites/{site_id}", response_model=ApiResponse[dict])
async def delete_site(
    site_id: str,
    force: bool = Query(False, description="Force delete site and unassign associated branches"),
    current_user: dict = Depends(require_roles([UserRole.SUPER_ADMIN])),
):
    if not ObjectId.is_valid(site_id):
        raise HTTPException(status_code=400, detail="Invalid Site ID format.")
    db = get_database()
    existing = await db.sites.find_one({"_id": ObjectId(site_id)})
    if not existing:
        raise HTTPException(status_code=404, detail="Site not found.")

    site_code = existing.get("code", "")
    branch_count = await db.branches.count_documents({
        "$or": [{"site_id": site_id}, {"site_code": site_code}]
    })

    if branch_count > 0 and not force:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete Site '{existing.get('name')}': {branch_count} branches are associated with it. Please reassign the branches or use force delete.",
        )

    if branch_count > 0 and force:
        # Unassign branches from this site
        await db.branches.update_many(
            {"$or": [{"site_id": site_id}, {"site_code": site_code}]},
            {"$set": {"site_id": None, "site_code": None, "site_name": None, "updated_at": datetime.now(timezone.utc)}}
        )

    await db.sites.delete_one({"_id": ObjectId(site_id)})
    return ApiResponse(
        success=True,
        data={"deleted_site_id": site_id, "unassigned_branches": branch_count},
        message=f"Site '{existing.get('name')}' deleted successfully.",
    )


# =====================================================================
# 3. Branches Management
# =====================================================================
@router.get("/branches", response_model=ApiResponse[List[BranchResponse]])
async def list_branches(
    search: Optional[str] = Query(None),
    site_id: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    current_user: dict = Depends(require_roles([UserRole.SUPER_ADMIN])),
):
    db = get_database()
    query: Dict[str, Any] = {}

    if site_id:
        query["site_id"] = site_id
    if is_active is not None:
        query["is_active"] = is_active
    if search:
        s_clean = re.escape(search.strip())
        query["$or"] = [
            {"code": {"$regex": s_clean, "$options": "i"}},
            {"name": {"$regex": s_clean, "$options": "i"}},
            {"hod_name": {"$regex": s_clean, "$options": "i"}},
            {"site_name": {"$regex": s_clean, "$options": "i"}},
        ]

    cursor = db.branches.find(query).sort("code", 1)
    results = []
    async for b in cursor:
        enriched = await _enrich_branch_details(b)
        results.append(BranchResponse(**enriched))
    return ApiResponse(success=True, data=results)


@router.post("/branches", response_model=ApiResponse[BranchResponse], status_code=status.HTTP_201_CREATED)
async def create_branch(
    data: BranchCreate,
    current_user: dict = Depends(require_roles([UserRole.SUPER_ADMIN])),
):
    db = get_database()
    code_clean = data.code.strip().upper()

    existing = await db.branches.find_one({"code": code_clean})
    if existing:
        raise HTTPException(status_code=400, detail=f"Branch with code '{code_clean}' already exists.")

    # Resolve Site if provided
    site_id = data.site_id
    site_name = data.site_name
    site_code = data.site_code
    if site_id and ObjectId.is_valid(site_id):
        site_doc = await db.sites.find_one({"_id": ObjectId(site_id)})
        if site_doc:
            site_name = site_doc.get("name")
            site_code = site_doc.get("code")

    # Resolve HOD if provided
    hod_id = data.hod_id
    hod_name = None
    hod_email = None
    hod_phone = None
    if hod_id and ObjectId.is_valid(hod_id):
        hod_doc = await db.users.find_one({"_id": ObjectId(hod_id)})
        if hod_doc:
            hod_name = hod_doc.get("name")
            hod_email = hod_doc.get("email")
            hod_phone = hod_doc.get("phone")

    now = datetime.now(timezone.utc)
    doc = {
        "code": code_clean,
        "name": data.name.strip(),
        "site_id": site_id,
        "site_name": site_name,
        "site_code": site_code,
        "hod_id": hod_id,
        "hod_name": hod_name,
        "hod_email": hod_email,
        "hod_phone": hod_phone,
        "description": data.description.strip() if data.description else None,
        "is_active": data.is_active,
        "created_at": now,
        "updated_at": now,
    }
    res = await db.branches.insert_one(doc)
    doc["_id"] = str(res.inserted_id)

    # Sync with departments collection for backward compatibility
    dept_existing = await db.departments.find_one({"code": code_clean})
    if not dept_existing:
        await db.departments.insert_one({
            "code": code_clean,
            "name": data.name.strip(),
            "coordinator_id": hod_id,
            "coordinator_name": hod_name,
            "coordinator_email": hod_email,
            "is_active": data.is_active,
            "created_at": now,
            "updated_at": now,
        })
    else:
        await db.departments.update_one(
            {"code": code_clean},
            {"$set": {
                "name": data.name.strip(),
                "coordinator_id": hod_id,
                "coordinator_name": hod_name,
                "coordinator_email": hod_email,
                "is_active": data.is_active,
                "updated_at": now,
            }}
        )

    enriched = await _enrich_branch_details(doc)
    return ApiResponse(success=True, data=BranchResponse(**enriched), message=f"Branch '{code_clean}' created successfully.")


@router.get("/branches/{branch_id}", response_model=ApiResponse[BranchResponse])
async def get_branch_details(
    branch_id: str,
    current_user: dict = Depends(require_roles([UserRole.SUPER_ADMIN])),
):
    db = get_database()
    query = {"_id": ObjectId(branch_id)} if ObjectId.is_valid(branch_id) else {"code": branch_id.upper()}
    doc = await db.branches.find_one(query)
    if not doc:
        raise HTTPException(status_code=404, detail="Branch not found.")

    enriched = await _enrich_branch_details(doc)
    return ApiResponse(success=True, data=BranchResponse(**enriched))


@router.put("/branches/{branch_id}", response_model=ApiResponse[BranchResponse])
async def update_branch(
    branch_id: str,
    data: BranchUpdate,
    current_user: dict = Depends(require_roles([UserRole.SUPER_ADMIN])),
):
    db = get_database()
    query = {"_id": ObjectId(branch_id)} if ObjectId.is_valid(branch_id) else {"code": branch_id.upper()}
    existing = await db.branches.find_one(query)
    if not existing:
        raise HTTPException(status_code=404, detail="Branch not found.")

    doc_id = existing["_id"]
    old_code = existing.get("code")
    now = datetime.now(timezone.utc)
    updates: Dict[str, Any] = {"updated_at": now}

    if data.code is not None:
        code_clean = data.code.strip().upper()
        if code_clean != old_code:
            dup = await db.branches.find_one({"code": code_clean, "_id": {"$ne": doc_id}})
            if dup:
                raise HTTPException(status_code=400, detail=f"Branch code '{code_clean}' already exists.")
            updates["code"] = code_clean

    if data.name is not None:
        updates["name"] = data.name.strip()

    if data.site_id is not None:
        site_id = data.site_id.strip() if data.site_id else None
        updates["site_id"] = site_id
        if site_id and ObjectId.is_valid(site_id):
            s_doc = await db.sites.find_one({"_id": ObjectId(site_id)})
            if s_doc:
                updates["site_name"] = s_doc.get("name")
                updates["site_code"] = s_doc.get("code")
        else:
            updates["site_name"] = None
            updates["site_code"] = None

    if data.hod_id is not None:
        hod_id = data.hod_id.strip() if data.hod_id else None
        updates["hod_id"] = hod_id
        if hod_id and ObjectId.is_valid(hod_id):
            h_doc = await db.users.find_one({"_id": ObjectId(hod_id)})
            if h_doc:
                updates["hod_name"] = h_doc.get("name")
                updates["hod_email"] = h_doc.get("email")
                updates["hod_phone"] = h_doc.get("phone")
        else:
            updates["hod_name"] = None
            updates["hod_email"] = None
            updates["hod_phone"] = None

    if data.description is not None:
        updates["description"] = data.description.strip() if data.description else None

    if data.is_active is not None:
        updates["is_active"] = data.is_active

    await db.branches.update_one({"_id": doc_id}, {"$set": updates})

    # Sync with departments
    effective_code = updates.get("code", old_code)
    dept_updates = {}
    if "name" in updates:
        dept_updates["name"] = updates["name"]
    if "code" in updates:
        dept_updates["code"] = updates["code"]
    if "hod_id" in updates:
        dept_updates["coordinator_id"] = updates["hod_id"]
        dept_updates["coordinator_name"] = updates.get("hod_name")
        dept_updates["coordinator_email"] = updates.get("hod_email")
    if "is_active" in updates:
        dept_updates["is_active"] = updates["is_active"]
    if dept_updates:
        dept_updates["updated_at"] = now
        await db.departments.update_one({"code": old_code}, {"$set": dept_updates})

    updated_doc = await db.branches.find_one({"_id": doc_id})
    enriched = await _enrich_branch_details(updated_doc)
    return ApiResponse(success=True, data=BranchResponse(**enriched), message="Branch updated successfully.")


@router.delete("/branches/{branch_id}", response_model=ApiResponse[dict])
async def delete_branch(
    branch_id: str,
    force: bool = Query(False, description="Confirm deletion even if associated records exist"),
    current_user: dict = Depends(require_roles([UserRole.SUPER_ADMIN])),
):
    db = get_database()
    query = {"_id": ObjectId(branch_id)} if ObjectId.is_valid(branch_id) else {"code": branch_id.upper()}
    existing = await db.branches.find_one(query)
    if not existing:
        raise HTTPException(status_code=404, detail="Branch not found.")

    doc_id = existing["_id"]
    code = existing.get("code", "")

    # Pre-check associated records to prevent accidental data loss
    stu_count = await db.students.count_documents({
        "$or": [{"branch": code}, {"department": code}]
    })
    sec_count = await db.sections.count_documents({
        "$or": [{"branch": code}, {"department": code}]
    })
    mentor_count = await db.users.count_documents({
        "role": UserRole.MENTOR.value,
        "$or": [{"branch": code}, {"department": code}]
    })
    hod_count = await db.users.count_documents({
        "role": UserRole.ADMIN.value,
        "$or": [{"branch": code}, {"department": code}]
    })

    total_associations = stu_count + sec_count + mentor_count + hod_count

    if total_associations > 0 and not force:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Cannot delete branch '{code}': It has {stu_count} students, {sec_count} sections, "
                f"{mentor_count} mentors, and {hod_count} HOD/Admin accounts. "
                "Confirm deletion with force=true to proceed with deactivation/removal."
            ),
        )

    # Deactivate or delete
    if total_associations > 0 and force:
        # Soft deactivate to protect relational integrity
        await db.branches.update_one(
            {"_id": doc_id},
            {"$set": {"is_active": False, "updated_at": datetime.now(timezone.utc)}}
        )
        await db.departments.update_one(
            {"code": code},
            {"$set": {"is_active": False, "updated_at": datetime.now(timezone.utc)}}
        )
        return ApiResponse(
            success=True,
            data={"id": str(doc_id), "code": code, "action": "DEACTIVATED"},
            message=f"Branch '{code}' has associated records and was deactivated to prevent data loss.",
        )

    await db.branches.delete_one({"_id": doc_id})
    await db.departments.delete_one({"code": code})
    return ApiResponse(
        success=True,
        data={"id": str(doc_id), "code": code, "action": "DELETED"},
        message=f"Branch '{code}' deleted successfully.",
    )


# =====================================================================
# 4. HOD Management
# =====================================================================
@router.get("/hods", response_model=ApiResponse[List[HODResponse]])
async def list_hods(
    search: Optional[str] = Query(None),
    branch_code: Optional[str] = Query(None),
    current_user: dict = Depends(require_roles([UserRole.SUPER_ADMIN])),
):
    db = get_database()
    query: Dict[str, Any] = {
        "role": UserRole.ADMIN.value,
        "$or": [
            {"branch": {"$exists": True, "$ne": None, "$ne": ""}},
            {"designation": {"$regex": "HOD|HEAD", "$options": "i"}},
        ]
    }

    if branch_code and branch_code.upper() != "ALL":
        b_clean = re.escape(branch_code.strip())
        query["$and"] = [
            {"$or": [
                {"branch": {"$regex": f"^{b_clean}$", "$options": "i"}},
                {"department": {"$regex": f"^{b_clean}$", "$options": "i"}},
            ]}
        ]

    if search:
        s_clean = re.escape(search.strip())
        s_clause = {
            "$or": [
                {"name": {"$regex": s_clean, "$options": "i"}},
                {"email": {"$regex": s_clean, "$options": "i"}},
                {"phone": {"$regex": s_clean, "$options": "i"}},
                {"branch": {"$regex": s_clean, "$options": "i"}},
            ]
        }
        if "$and" in query:
            query["$and"].append(s_clause)
        else:
            query["$and"] = [s_clause]

    cursor = db.users.find(query).sort("created_at", -1)
    hods = []

    # Cache branches for fast name resolution
    branches = await db.branches.find({}).to_list(length=200)
    branch_map = {b.get("code", "").upper(): b for b in branches}

    async for u in cursor:
        u_id = str(u["_id"])
        b_code = (u.get("branch") or u.get("department") or "").upper()
        b_info = branch_map.get(b_code, {})
        b_name = b_info.get("name") or b_code

        # Count branch students & mentors
        stu_count = await db.students.count_documents({
            "$or": [{"branch": b_code}, {"department": b_code}]
        })
        mentor_count = await db.users.count_documents({
            "role": UserRole.MENTOR.value,
            "$or": [{"branch": b_code}, {"department": b_code}]
        })

        hods.append(HODResponse(
            id=u_id,
            name=u.get("name", ""),
            email=u.get("email", ""),
            phone=u.get("phone"),
            branch_code=b_code,
            branch_name=b_name,
            branch_id=str(b_info.get("_id")) if b_info.get("_id") else None,
            role="ADMIN",
            designation=u.get("designation") or "HOD",
            is_active=u.get("is_active", True),
            student_count=stu_count,
            mentor_count=mentor_count,
            created_at=u.get("created_at"),
            updated_at=u.get("updated_at"),
        ))

    return ApiResponse(success=True, data=hods)


@router.post("/hods", response_model=ApiResponse[HODResponse], status_code=status.HTTP_201_CREATED)
async def create_hod(
    data: HODCreate,
    current_user: dict = Depends(require_roles([UserRole.SUPER_ADMIN])),
):
    db = get_database()
    email_clean = data.email.strip().lower()
    branch_code = data.branch_code.strip().upper()

    # 1. Verify branch exists
    branch_doc = await db.branches.find_one({
        "$or": [{"code": branch_code}, {"code": {"$regex": f"^{re.escape(branch_code)}$", "$options": "i"}}]
    })
    if not branch_doc:
        raise HTTPException(status_code=404, detail=f"Branch '{branch_code}' does not exist. Please create the branch first.")

    # 2. Check for duplicate email
    existing_user = await db.users.find_one({"email": email_clean})
    if existing_user:
        raise HTTPException(status_code=400, detail=f"An account with email '{email_clean}' already exists.")

    # 3. Prevent duplicate active HOD assignment for the branch
    existing_hod = await db.users.find_one({
        "role": UserRole.ADMIN.value,
        "is_active": True,
        "$or": [{"branch": branch_code}, {"department": branch_code}],
        "designation": {"$regex": "HOD|HEAD", "$options": "i"},
    })
    if existing_hod:
        raise HTTPException(
            status_code=400,
            detail=f"Branch '{branch_code}' already has an active HOD ({existing_hod.get('name')}). Please deactivate or reassign the existing HOD first.",
        )

    # 4. Hash password
    initial_pwd = data.password.strip() if data.password else f"{branch_code.lower()}@hod123"
    hashed_pwd = hash_password(initial_pwd)

    now = datetime.now(timezone.utc)
    user_doc = {
        "name": data.name.strip(),
        "email": email_clean,
        "password_hash": hashed_pwd,
        "role": UserRole.ADMIN.value,
        "designation": "HOD",
        "branch": branch_code,
        "department": branch_code,
        "branch_id": str(branch_doc["_id"]),
        "phone": data.phone.strip() if data.phone else None,
        "is_active": data.is_active,
        "created_at": now,
        "updated_at": now,
    }
    res = await db.users.insert_one(user_doc)
    user_id = str(res.inserted_id)

    # 5. Update branch with assigned HOD
    await db.branches.update_one(
        {"_id": branch_doc["_id"]},
        {"$set": {
            "hod_id": user_id,
            "hod_name": data.name.strip(),
            "hod_email": email_clean,
            "hod_phone": data.phone.strip() if data.phone else None,
            "updated_at": now,
        }}
    )

    # 6. Backward-compatible sync with departments
    await db.departments.update_one(
        {"code": branch_code},
        {"$set": {
            "coordinator_id": user_id,
            "coordinator_name": data.name.strip(),
            "coordinator_email": email_clean,
            "updated_at": now,
        }}
    )

    # 7. Audit log
    await db.audit_logs.insert_one({
        "actor_id": current_user["id"],
        "action": "CREATE_HOD",
        "target_user_id": user_id,
        "metadata": {"name": data.name.strip(), "email": email_clean, "branch": branch_code},
        "created_at": now,
    })

    return ApiResponse(
        success=True,
        data=HODResponse(
            id=user_id,
            name=data.name.strip(),
            email=email_clean,
            phone=data.phone.strip() if data.phone else None,
            branch_code=branch_code,
            branch_name=branch_doc.get("name", branch_code),
            branch_id=str(branch_doc["_id"]),
            role="ADMIN",
            designation="HOD",
            is_active=data.is_active,
            student_count=0,
            mentor_count=0,
            created_at=now,
            updated_at=now,
        ),
        message=f"HOD '{data.name.strip()}' created and assigned to {branch_code} successfully.",
    )


@router.get("/hods/{hod_id}", response_model=ApiResponse[HODResponse])
async def get_hod_details(
    hod_id: str,
    current_user: dict = Depends(require_roles([UserRole.SUPER_ADMIN])),
):
    if not ObjectId.is_valid(hod_id):
        raise HTTPException(status_code=400, detail="Invalid HOD ID format.")
    db = get_database()
    u = await db.users.find_one({"_id": ObjectId(hod_id)})
    if not u:
        raise HTTPException(status_code=404, detail="HOD account not found.")

    b_code = (u.get("branch") or u.get("department") or "").upper()
    b_doc = await db.branches.find_one({"code": b_code}) if b_code else None

    stu_count = await db.students.count_documents({"$or": [{"branch": b_code}, {"department": b_code}]})
    mentor_count = await db.users.count_documents({"role": UserRole.MENTOR.value, "$or": [{"branch": b_code}, {"department": b_code}]})

    return ApiResponse(
        success=True,
        data=HODResponse(
            id=str(u["_id"]),
            name=u.get("name", ""),
            email=u.get("email", ""),
            phone=u.get("phone"),
            branch_code=b_code,
            branch_name=b_doc.get("name") if b_doc else b_code,
            branch_id=str(b_doc["_id"]) if b_doc else None,
            role="ADMIN",
            designation=u.get("designation") or "HOD",
            is_active=u.get("is_active", True),
            student_count=stu_count,
            mentor_count=mentor_count,
            created_at=u.get("created_at"),
            updated_at=u.get("updated_at"),
        )
    )


@router.put("/hods/{hod_id}", response_model=ApiResponse[HODResponse])
async def update_hod(
    hod_id: str,
    data: HODUpdate,
    current_user: dict = Depends(require_roles([UserRole.SUPER_ADMIN])),
):
    if not ObjectId.is_valid(hod_id):
        raise HTTPException(status_code=400, detail="Invalid HOD ID format.")
    db = get_database()
    u = await db.users.find_one({"_id": ObjectId(hod_id)})
    if not u:
        raise HTTPException(status_code=404, detail="HOD account not found.")

    doc_id = ObjectId(hod_id)
    now = datetime.now(timezone.utc)
    updates: Dict[str, Any] = {"updated_at": now}
    old_branch = (u.get("branch") or u.get("department") or "").upper()
    new_branch = data.branch_code.strip().upper() if data.branch_code else old_branch

    if data.name is not None:
        updates["name"] = data.name.strip()

    if data.email is not None:
        email_clean = data.email.strip().lower()
        if email_clean != u.get("email"):
            dup = await db.users.find_one({"email": email_clean, "_id": {"$ne": doc_id}})
            if dup:
                raise HTTPException(status_code=400, detail=f"Email '{email_clean}' is already in use.")
            updates["email"] = email_clean

    if data.phone is not None:
        updates["phone"] = data.phone.strip() if data.phone else None

    if data.is_active is not None:
        updates["is_active"] = data.is_active

    if data.password:
        updates["password_hash"] = hash_password(data.password.strip())

    # Branch reassignment
    if new_branch != old_branch:
        # Check that new branch exists
        new_b_doc = await db.branches.find_one({"code": new_branch})
        if not new_b_doc:
            raise HTTPException(status_code=404, detail=f"Target branch '{new_branch}' does not exist.")

        # Check if new branch already has another active HOD
        another_hod = await db.users.find_one({
            "_id": {"$ne": doc_id},
            "role": UserRole.ADMIN.value,
            "is_active": True,
            "$or": [{"branch": new_branch}, {"department": new_branch}],
            "designation": {"$regex": "HOD|HEAD", "$options": "i"},
        })
        if another_hod:
            raise HTTPException(
                status_code=400,
                detail=f"Branch '{new_branch}' is already assigned to active HOD '{another_hod.get('name')}'.",
            )

        updates["branch"] = new_branch
        updates["department"] = new_branch
        updates["branch_id"] = str(new_b_doc["_id"])

        # Clear old branch HOD assignment
        await db.branches.update_one(
            {"code": old_branch, "hod_id": hod_id},
            {"$set": {"hod_id": None, "hod_name": None, "hod_email": None, "hod_phone": None, "updated_at": now}}
        )
        # Assign to new branch
        await db.branches.update_one(
            {"_id": new_b_doc["_id"]},
            {"$set": {
                "hod_id": hod_id,
                "hod_name": updates.get("name", u.get("name")),
                "hod_email": updates.get("email", u.get("email")),
                "hod_phone": updates.get("phone", u.get("phone")),
                "updated_at": now,
            }}
        )
    else:
        # If name/email/phone updated, sync to current branch
        branch_sync = {}
        if "name" in updates:
            branch_sync["hod_name"] = updates["name"]
        if "email" in updates:
            branch_sync["hod_email"] = updates["email"]
        if "phone" in updates:
            branch_sync["hod_phone"] = updates["phone"]
        if branch_sync:
            branch_sync["updated_at"] = now
            await db.branches.update_one({"code": old_branch}, {"$set": branch_sync})

    await db.users.update_one({"_id": doc_id}, {"$set": updates})
    updated_user = await db.users.find_one({"_id": doc_id})

    b_doc = await db.branches.find_one({"code": new_branch})
    stu_count = await db.students.count_documents({"$or": [{"branch": new_branch}, {"department": new_branch}]})
    mentor_count = await db.users.count_documents({"role": UserRole.MENTOR.value, "$or": [{"branch": new_branch}, {"department": new_branch}]})

    return ApiResponse(
        success=True,
        data=HODResponse(
            id=hod_id,
            name=updated_user.get("name", ""),
            email=updated_user.get("email", ""),
            phone=updated_user.get("phone"),
            branch_code=new_branch,
            branch_name=b_doc.get("name") if b_doc else new_branch,
            branch_id=str(b_doc["_id"]) if b_doc else None,
            role="ADMIN",
            designation="HOD",
            is_active=updated_user.get("is_active", True),
            student_count=stu_count,
            mentor_count=mentor_count,
            created_at=updated_user.get("created_at"),
            updated_at=updated_user.get("updated_at"),
        ),
        message="HOD account updated successfully.",
    )


@router.post("/hods/{hod_id}/reset-password", response_model=ApiResponse[dict])
async def reset_hod_password(
    hod_id: str,
    data: HODResetPassword,
    current_user: dict = Depends(require_roles([UserRole.SUPER_ADMIN])),
):
    if not ObjectId.is_valid(hod_id):
        raise HTTPException(status_code=400, detail="Invalid HOD ID format.")
    db = get_database()
    u = await db.users.find_one({"_id": ObjectId(hod_id)})
    if not u:
        raise HTTPException(status_code=404, detail="HOD account not found.")

    new_hash = hash_password(data.new_password.strip())
    now = datetime.now(timezone.utc)
    await db.users.update_one(
        {"_id": ObjectId(hod_id)},
        {"$set": {"password_hash": new_hash, "updated_at": now}}
    )
    return ApiResponse(success=True, message=f"Password for HOD '{u.get('name')}' reset successfully.")


@router.patch("/hods/{hod_id}/toggle-status", response_model=ApiResponse[dict])
async def toggle_hod_status(
    hod_id: str,
    current_user: dict = Depends(require_roles([UserRole.SUPER_ADMIN])),
):
    if not ObjectId.is_valid(hod_id):
        raise HTTPException(status_code=400, detail="Invalid HOD ID format.")
    db = get_database()
    u = await db.users.find_one({"_id": ObjectId(hod_id)})
    if not u:
        raise HTTPException(status_code=404, detail="HOD account not found.")

    new_status = not u.get("is_active", True)
    now = datetime.now(timezone.utc)
    await db.users.update_one(
        {"_id": ObjectId(hod_id)},
        {"$set": {"is_active": new_status, "updated_at": now}}
    )
    action_str = "activated" if new_status else "deactivated"
    return ApiResponse(
        success=True,
        data={"id": hod_id, "is_active": new_status},
        message=f"HOD '{u.get('name')}' account {action_str} successfully.",
    )


@router.delete("/hods/{hod_id}", response_model=ApiResponse[dict])
async def delete_hod(
    hod_id: str,
    current_user: dict = Depends(require_roles([UserRole.SUPER_ADMIN])),
):
    if not ObjectId.is_valid(hod_id):
        raise HTTPException(status_code=400, detail="Invalid HOD ID format.")
    db = get_database()
    u = await db.users.find_one({"_id": ObjectId(hod_id)})
    if not u:
        raise HTTPException(status_code=404, detail="HOD account not found.")

    b_code = (u.get("branch") or u.get("department") or "").upper()
    now = datetime.now(timezone.utc)

    # Clear HOD assignment from branch
    if b_code:
        await db.branches.update_one(
            {"code": b_code, "hod_id": hod_id},
            {"$set": {"hod_id": None, "hod_name": None, "hod_email": None, "hod_phone": None, "updated_at": now}}
        )
        await db.departments.update_one(
            {"code": b_code, "coordinator_id": hod_id},
            {"$set": {"coordinator_id": None, "coordinator_name": None, "coordinator_email": None, "updated_at": now}}
        )

    await db.users.delete_one({"_id": ObjectId(hod_id)})
    return ApiResponse(
        success=True,
        data={"deleted_hod_id": hod_id, "branch_code": b_code},
        message=f"HOD account for '{u.get('name')}' deleted successfully.",
    )
