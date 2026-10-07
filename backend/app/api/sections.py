from typing import List, Optional
from datetime import datetime, timezone
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, status
from app.core.dependencies import get_current_user, require_roles
from app.db.mongodb import get_database
from app.schemas.common import ApiResponse
from app.schemas.section import SectionCreate, SectionResponse, SectionUpdate
from app.schemas.user import UserRole

router = APIRouter(prefix="/sections", tags=["Sections"])


async def _enrich_section_details(doc: dict) -> dict:
    db = get_database()
    sec_id = str(doc["_id"])
    year = doc.get("year", "")
    branch = doc.get("branch") or doc.get("department") or "CSE"
    sec_name = doc.get("section_name", "")

    # Calculate real student count matching year + branch + section
    stu_query = {
        "$and": [
            {
                "$or": [
                    {"section": sec_name},
                    {"section": f"{branch}-{sec_name}"},
                    {"section": {"$regex": f"^{sec_name}$", "$options": "i"}},
                ]
            }
        ]
    }
    if year:
        stu_query["$and"].append({
            "$or": [
                {"year": year},
                {"year": {"$regex": f"^{year}$", "$options": "i"}},
            ]
        })
    if branch:
        stu_query["$and"].append({
            "$or": [
                {"branch": branch},
                {"branch": {"$regex": f"^{branch}$", "$options": "i"}},
                {"department": branch},
            ]
        })

    student_count = await db.students.count_documents(stu_query)

    # Resolve CR / LR names if assigned
    cr_name = None
    lr_name = None
    if doc.get("assigned_cr_id") and ObjectId.is_valid(doc["assigned_cr_id"]):
        cr = await db.users.find_one({"_id": ObjectId(doc["assigned_cr_id"])})
        if cr:
            cr_name = cr.get("name")
    if doc.get("assigned_lr_id") and ObjectId.is_valid(doc["assigned_lr_id"]):
        lr = await db.users.find_one({"_id": ObjectId(doc["assigned_lr_id"])})
        if lr:
            lr_name = lr.get("name")

    doc["_id"] = sec_id
    doc["branch"] = branch
    doc["department"] = branch
    doc["student_count"] = student_count
    doc["cr_name"] = cr_name
    doc["lr_name"] = lr_name
    return doc


@router.get("", response_model=ApiResponse[List[SectionResponse]])
async def list_sections_api(
    year: Optional[str] = Query(None, description="Filter by Academic Year"),
    branch: Optional[str] = Query(None, description="Filter by Branch / Department"),
    is_active: Optional[bool] = Query(None),
    current_user: dict = Depends(get_current_user),
):
    db = get_database()
    query = {}

    user_role = current_user.get("role")
    # Department Coordinator RBAC filter
    if user_role in [UserRole.DEPARTMENT_COORDINATOR.value, UserRole.COORDINATOR.value]:
        user_dept = current_user.get("department") or current_user.get("branch")
        if user_dept:
            branch = user_dept

    if year and year != "ALL" and year != "all":
        query["year"] = year
    if branch and branch != "ALL" and branch != "all":
        b_clean = branch.strip().upper()
        query["$or"] = [{"branch": b_clean}, {"department": b_clean}, {"branch": {"$regex": f"^{b_clean}$", "$options": "i"}}]
    if is_active is not None:
        query["is_active"] = is_active

    cursor = db.sections.find(query).sort([("year", 1), ("branch", 1), ("section_name", 1)])
    sections = []
    async for doc in cursor:
        enriched = await _enrich_section_details(doc)
        sections.append(SectionResponse(**enriched))

    return ApiResponse(success=True, data=sections)


@router.post("", response_model=ApiResponse[SectionResponse], status_code=status.HTTP_201_CREATED)
async def create_section_api(
    data: SectionCreate, admin: dict = Depends(require_roles([UserRole.ADMIN]))
):
    db = get_database()
    year_clean = data.year.strip()
    branch_clean = (data.branch or data.department or "CSE").strip().upper()
    sec_name = data.section_name.strip().upper()

    # Feature 1 Validation: Prevent duplicate section for Year + Branch
    existing = await db.sections.find_one({
        "year": year_clean,
        "$or": [{"branch": branch_clean}, {"department": branch_clean}],
        "section_name": sec_name,
    })
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Section {sec_name} already exists for {year_clean} {branch_clean}.",
        )

    now = datetime.now(timezone.utc)
    doc = {
        "year": year_clean,
        "branch": branch_clean,
        "department": branch_clean,
        "section_name": sec_name,
        "assigned_cr_id": data.assigned_cr_id,
        "assigned_lr_id": data.assigned_lr_id,
        "is_active": data.is_active,
        "created_at": now,
        "updated_at": now,
    }
    res = await db.sections.insert_one(doc)
    doc["_id"] = str(res.inserted_id)
    enriched = await _enrich_section_details(doc)
    return ApiResponse(
        success=True,
        data=SectionResponse(**enriched),
        message=f"Section '{sec_name}' created successfully for {year_clean} {branch_clean}.",
    )


@router.put("/{section_id}", response_model=ApiResponse[SectionResponse])
async def update_section_api(
    section_id: str,
    data: SectionUpdate,
    admin: dict = Depends(require_roles([UserRole.ADMIN])),
):
    if not ObjectId.is_valid(section_id):
        raise HTTPException(status_code=400, detail="Invalid Section ID format.")

    db = get_database()
    existing = await db.sections.find_one({"_id": ObjectId(section_id)})
    if not existing:
        raise HTTPException(status_code=404, detail="Section not found.")

    now = datetime.now(timezone.utc)
    updates = {}

    target_year = data.year.strip() if data.year else existing.get("year")
    target_branch = (data.branch or data.department or existing.get("branch") or "CSE").strip().upper()
    target_sec = data.section_name.strip().upper() if data.section_name else existing.get("section_name")

    # Check duplicate uniqueness on update
    dup = await db.sections.find_one({
        "_id": {"$ne": ObjectId(section_id)},
        "year": target_year,
        "$or": [{"branch": target_branch}, {"department": target_branch}],
        "section_name": target_sec,
    })
    if dup:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Section {target_sec} already exists for {target_year} {target_branch}.",
        )

    if data.year is not None:
        updates["year"] = target_year
    if data.branch is not None or data.department is not None:
        updates["branch"] = target_branch
        updates["department"] = target_branch
    if data.section_name is not None:
        updates["section_name"] = target_sec
    if data.is_active is not None:
        updates["is_active"] = data.is_active
    if data.assigned_cr_id is not None:
        updates["assigned_cr_id"] = data.assigned_cr_id
    if data.assigned_lr_id is not None:
        updates["assigned_lr_id"] = data.assigned_lr_id

    updates["updated_at"] = now
    await db.sections.update_one({"_id": ObjectId(section_id)}, {"$set": updates})

    updated_doc = await db.sections.find_one({"_id": ObjectId(section_id)})
    enriched = await _enrich_section_details(updated_doc)
    return ApiResponse(
        success=True,
        data=SectionResponse(**enriched),
        message="Section updated successfully.",
    )


@router.delete("/{section_id}", response_model=ApiResponse[dict])
async def delete_section_api(
    section_id: str,
    admin: dict = Depends(require_roles([UserRole.ADMIN])),
):
    if not ObjectId.is_valid(section_id):
        raise HTTPException(status_code=400, detail="Invalid Section ID format.")

    db = get_database()
    sec = await db.sections.find_one({"_id": ObjectId(section_id)})
    if not sec:
        raise HTTPException(status_code=404, detail="Section not found.")

    sec_name = sec.get("section_name")
    year = sec.get("year")
    branch = sec.get("branch")

    # Check if student records exist
    stu_count = await db.students.count_documents({
        "section": sec_name,
        "$or": [{"branch": branch}, {"department": branch}],
    })

    if stu_count > 0:
        # Soft deactivate
        await db.sections.update_one(
            {"_id": ObjectId(section_id)},
            {"$set": {"is_active": False, "updated_at": datetime.now(timezone.utc)}},
        )
        return ApiResponse(
            success=True,
            data={"id": section_id, "action": "DEACTIVATED"},
            message=f"Section '{sec_name}' has {stu_count} enrolled students and was deactivated.",
        )

    await db.sections.delete_one({"_id": ObjectId(section_id)})
    return ApiResponse(
        success=True,
        data={"id": section_id, "action": "DELETED"},
        message=f"Section '{sec_name}' for {year} {branch} deleted successfully.",
    )
