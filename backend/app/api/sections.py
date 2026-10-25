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


import re

def _normalize_academic_year(value: str) -> Optional[str]:
    token = re.sub(r"[^a-z0-9]", "", (value or "").lower())
    if token.startswith(("4", "iv", "fourth")): return "4th Year"
    if token.startswith(("3", "iii", "third")): return "3rd Year"
    if token.startswith(("2", "ii", "second")): return "2nd Year"
    if token.startswith(("1", "i", "first")): return "1st Year"
    return None


def _section_inventory_key(year: str, branch: str, section_name: str) -> tuple:
    name = str(section_name or "").strip().upper()
    parts = name.split("-")
    if len(parts) >= 3 and parts[0] in {"I", "II", "III", "IV"}:
        branch = parts[1]
    label = parts[-1] if parts else name
    return (_normalize_academic_year(year or ""), (branch or "CSE").strip().upper(), label)

async def _enrich_section_details(doc: dict) -> dict:
    db = get_database()
    sec_id = str(doc["_id"])
    year = doc.get("year", "")
    sec_name = doc.get("section_name", "")
    branch = doc.get("branch") or doc.get("department")
    if not branch:
        if "-" in sec_name:
            parts = sec_name.split("-")
            if len(parts) >= 2 and parts[1].isalpha():
                branch = parts[1].upper()
        if not branch:
            branch = "CSE"

    clean_sec = sec_name.split("-")[-1].strip() if "-" in sec_name else sec_name.strip()

    # Calculate real student count matching year + branch + section
    sec_matchers = [
        {"section": sec_name},
        {"section": clean_sec},
        {"section": f"{branch}-{sec_name}"},
        {"section": f"{branch}-{clean_sec}"},
        {"section": {"$regex": f"^{re.escape(sec_name)}$", "$options": "i"}},
        {"section": {"$regex": f"^{re.escape(clean_sec)}$", "$options": "i"}},
    ]

    stu_query = {
        "$and": [
            {"$or": sec_matchers}
        ]
    }
    if year:
        stu_query["$and"].append({
            "$or": [
                {"year": year},
                {"year": {"$regex": f"^{re.escape(year)}$", "$options": "i"}},
            ]
        })
    if branch:
        stu_query["$and"].append({
            "$or": [
                {"branch": branch},
                {"branch": {"$regex": f"^{re.escape(branch)}$", "$options": "i"}},
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


async def _enrich_section_details_bulk(docs: List[dict]) -> List[dict]:
    """Enrich the section page with two batch reads instead of three reads per row."""
    db = get_database()
    student_counts = {}
    students = db.students.find({}, {"year": 1, "branch": 1, "department": 1, "section": 1})
    async for student in students:
        key = _section_inventory_key(
            student.get("year", ""), student.get("branch") or student.get("department") or "CSE", student.get("section", "")
        )
        student_counts[key] = student_counts.get(key, 0) + 1

    user_names = {}
    representatives = {}
    users = db.users.find({"role": {"$in": ["CR", "LR"]}}, {"name": 1, "role": 1, "year": 1, "section": 1})
    async for user in users:
        user_names[str(user["_id"])] = user.get("name")
        key = _section_inventory_key(user.get("year", ""), "CSE", user.get("section", ""))
        if key[0] and key[2]:
            representatives.setdefault((key, user.get("role")), user.get("name"))

    enriched_docs = []
    for doc in docs:
        year = doc.get("year", "")
        name = doc.get("section_name", "")
        branch = doc.get("branch") or doc.get("department") or "CSE"
        key = _section_inventory_key(year, branch, name)
        doc["_id"] = str(doc["_id"])
        doc["branch"] = branch
        doc["department"] = branch
        doc["student_count"] = student_counts.get(key, 0)
        doc["cr_name"] = user_names.get(str(doc.get("assigned_cr_id"))) or representatives.get((key, "CR"))
        doc["lr_name"] = user_names.get(str(doc.get("assigned_lr_id"))) or representatives.get((key, "LR"))
        enriched_docs.append(doc)
    return enriched_docs


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
        query["$or"] = [
            {"branch": b_clean},
            {"department": b_clean},
            {"branch": {"$regex": f"^{b_clean}$", "$options": "i"}},
            {"section_name": {"$regex": f"-{b_clean}-|^{b_clean}-|{b_clean}", "$options": "i"}},
        ]
    if is_active is not None:
        query["is_active"] = is_active

    timetable_docs = await db.timetables.find({}, {"year": 1, "section": 1}).to_list(length=10000)
    timetable_inventory = {}
    for tt in timetable_docs:
        identity = _section_inventory_key(tt.get("year", ""), "CSE", tt.get("section", ""))
        if identity[0] and identity[2]:
            timetable_inventory.setdefault(identity, {
                "year": identity[0], "branch": identity[1], "section_name": str(tt.get("section")).strip().upper(),
            })

    cursor = db.sections.find(query).sort([("year", 1), ("branch", 1), ("section_name", 1)])
    docs = await cursor.to_list(length=1000)
    unique_docs = []
    seen_section_keys = set()
    for doc in docs:
        identity = _section_inventory_key(
            doc.get("year", ""), doc.get("branch") or doc.get("department") or "CSE", doc.get("section_name", "")
        )
        if identity not in timetable_inventory or identity in seen_section_keys:
            continue
        seen_section_keys.add(identity)
        doc.update(timetable_inventory[identity])
        unique_docs.append(doc)

    enriched_docs = await _enrich_section_details_bulk(unique_docs)
    sections = [SectionResponse(**doc) for doc in enriched_docs]

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
