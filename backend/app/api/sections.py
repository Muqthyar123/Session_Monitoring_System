from typing import List
from datetime import datetime, timezone
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status
from app.core.dependencies import get_current_user, require_roles
from app.db.mongodb import get_database
from app.schemas.common import ApiResponse
from app.schemas.section import SectionCreate, SectionResponse, SectionUpdate
from app.schemas.user import UserRole

router = APIRouter(prefix="/sections", tags=["Sections"])


@router.get("", response_model=ApiResponse[List[SectionResponse]])
async def list_sections_api(current_user: dict = Depends(get_current_user)):
    db = get_database()
    cursor = db.sections.find().sort("section_name", 1)
    sections = []
    async for doc in cursor:
        sec_id = str(doc["_id"])
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

        sections.append(
            SectionResponse(
                _id=sec_id,
                year=doc.get("year", ""),
                section_name=doc.get("section_name", ""),
                department=doc.get("department"),
                assigned_cr_id=doc.get("assigned_cr_id"),
                assigned_lr_id=doc.get("assigned_lr_id"),
                is_active=doc.get("is_active", True),
                cr_name=cr_name,
                lr_name=lr_name,
                created_at=doc.get("created_at"),
                updated_at=doc.get("updated_at"),
            )
        )
    return ApiResponse(success=True, data=sections)


@router.post("", response_model=ApiResponse[SectionResponse], status_code=status.HTTP_201_CREATED)
async def create_section_api(
    data: SectionCreate, admin: dict = Depends(require_roles([UserRole.ADMIN]))
):
    db = get_database()
    sec_name = data.section_name.strip().upper()
    existing = await db.sections.find_one({"section_name": sec_name})
    if existing:
        raise HTTPException(
            status_code=400, detail=f"Section '{sec_name}' already exists."
        )

    now = datetime.now(timezone.utc)
    doc = {
        "year": data.year.strip(),
        "section_name": sec_name,
        "department": data.department.strip() if data.department else None,
        "assigned_cr_id": data.assigned_cr_id,
        "assigned_lr_id": data.assigned_lr_id,
        "is_active": data.is_active,
        "created_at": now,
        "updated_at": now,
    }
    res = await db.sections.insert_one(doc)
    doc["_id"] = str(res.inserted_id)
    return ApiResponse(
        success=True,
        data=SectionResponse(**doc),
        message="Section created successfully.",
    )
