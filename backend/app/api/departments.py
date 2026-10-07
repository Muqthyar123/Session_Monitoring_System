from typing import List, Optional
from datetime import datetime, timezone
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, status
from app.core.dependencies import get_current_user, require_roles
from app.db.mongodb import get_database
from app.schemas.common import ApiResponse
from app.schemas.department import (
    DepartmentCreate,
    DepartmentResponse,
    DepartmentUpdate,
)
from app.schemas.user import UserRole

router = APIRouter(prefix="/admin/departments", tags=["Department Management"])


DEFAULT_DEPARTMENTS = [
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


async def _enrich_department_counts(doc: dict) -> dict:
    db = get_database()
    code = doc.get("code", "")
    # Count students matching branch/department
    stu_count = await db.students.count_documents({
        "$or": [
            {"branch": code},
            {"branch": {"$regex": f"^{code}$", "$options": "i"}},
            {"department": code},
        ]
    })
    # Count sections
    sec_count = await db.sections.count_documents({
        "$or": [
            {"branch": code},
            {"branch": {"$regex": f"^{code}$", "$options": "i"}},
            {"department": code},
        ]
    })
    # Count mentors/faculty
    fac_count = await db.users.count_documents({
        "role": UserRole.MENTOR.value,
        "$or": [
            {"department": code},
            {"department": {"$regex": f"^{code}$", "$options": "i"}},
        ]
    })

    # Resolve coordinator details if assigned
    coord_id = doc.get("coordinator_id")
    coord_name = doc.get("coordinator_name")
    coord_email = doc.get("coordinator_email")
    if coord_id and ObjectId.is_valid(coord_id):
        coord_user = await db.users.find_one({"_id": ObjectId(coord_id)})
        if coord_user:
            coord_name = coord_user.get("name")
            coord_email = coord_user.get("email")

    doc["_id"] = str(doc["_id"])
    doc["student_count"] = stu_count
    doc["section_count"] = sec_count
    doc["faculty_count"] = fac_count
    doc["coordinator_name"] = coord_name
    doc["coordinator_email"] = coord_email
    return doc


@router.get("", response_model=ApiResponse[List[DepartmentResponse]])
async def list_departments_api(
    current_user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.DEPARTMENT_COORDINATOR, UserRole.COORDINATOR])),
):
    db = get_database()
    # Auto-seed defaults if database is empty
    count = await db.departments.count_documents({})
    if count == 0:
        now = datetime.now(timezone.utc)
        seed_docs = [
            {
                "code": d["code"],
                "name": d["name"],
                "coordinator_id": None,
                "coordinator_name": None,
                "coordinator_email": None,
                "is_active": True,
                "created_at": now,
                "updated_at": now,
            }
            for d in DEFAULT_DEPARTMENTS
        ]
        await db.departments.insert_many(seed_docs)

    # If coordinator, check if restricted to their department
    user_role = current_user.get("role")
    query = {}
    if user_role in [UserRole.DEPARTMENT_COORDINATOR.value, UserRole.COORDINATOR.value]:
        user_dept = current_user.get("department") or current_user.get("branch")
        if user_dept:
            query = {"$or": [{"code": user_dept.upper()}, {"code": {"$regex": f"^{user_dept}$", "$options": "i"}}]}

    cursor = db.departments.find(query).sort("code", 1)
    results = []
    async for d in cursor:
        enriched = await _enrich_department_counts(d)
        results.append(DepartmentResponse(**enriched))

    return ApiResponse(success=True, data=results)


@router.post("", response_model=ApiResponse[DepartmentResponse], status_code=status.HTTP_201_CREATED)
async def create_department_api(
    data: DepartmentCreate,
    admin: dict = Depends(require_roles([UserRole.ADMIN])),
):
    db = get_database()
    code_clean = data.code.strip().upper()
    existing = await db.departments.find_one({"code": code_clean})
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Department with code '{code_clean}' already exists.",
        )

    now = datetime.now(timezone.utc)
    doc = {
        "code": code_clean,
        "name": data.name.strip(),
        "coordinator_id": data.coordinator_id,
        "coordinator_name": data.coordinator_name,
        "coordinator_email": data.coordinator_email,
        "is_active": data.is_active,
        "created_at": now,
        "updated_at": now,
    }

    # If coordinator_id provided, sync user role to DEPARTMENT_COORDINATOR
    if data.coordinator_id and ObjectId.is_valid(data.coordinator_id):
        await db.users.update_one(
            {"_id": ObjectId(data.coordinator_id)},
            {
                "$set": {
                    "role": UserRole.DEPARTMENT_COORDINATOR.value,
                    "department": code_clean,
                    "updated_at": now,
                }
            },
        )

    res = await db.departments.insert_one(doc)
    doc["_id"] = str(res.inserted_id)
    enriched = await _enrich_department_counts(doc)
    return ApiResponse(
        success=True,
        data=DepartmentResponse(**enriched),
        message=f"Department '{code_clean}' created successfully.",
    )


@router.put("/{dept_id}", response_model=ApiResponse[DepartmentResponse])
async def update_department_api(
    dept_id: str,
    data: DepartmentUpdate,
    admin: dict = Depends(require_roles([UserRole.ADMIN])),
):
    if not ObjectId.is_valid(dept_id):
        raise HTTPException(status_code=400, detail="Invalid Department ID format.")

    db = get_database()
    existing = await db.departments.find_one({"_id": ObjectId(dept_id)})
    if not existing:
        raise HTTPException(status_code=404, detail="Department not found.")

    updates = {}
    now = datetime.now(timezone.utc)

    if data.code is not None:
        code_clean = data.code.strip().upper()
        # Check duplicate code
        dup = await db.departments.find_one({"code": code_clean, "_id": {"$ne": ObjectId(dept_id)}})
        if dup:
            raise HTTPException(
                status_code=400,
                detail=f"Department with code '{code_clean}' already exists.",
            )
        updates["code"] = code_clean

    if data.name is not None:
        updates["name"] = data.name.strip()
    if data.is_active is not None:
        updates["is_active"] = data.is_active
    if data.coordinator_id is not None:
        updates["coordinator_id"] = data.coordinator_id
        if data.coordinator_id and ObjectId.is_valid(data.coordinator_id):
            coord_user = await db.users.find_one({"_id": ObjectId(data.coordinator_id)})
            if coord_user:
                updates["coordinator_name"] = coord_user.get("name")
                updates["coordinator_email"] = coord_user.get("email")
                # Update user role to DEPARTMENT_COORDINATOR
                await db.users.update_one(
                    {"_id": ObjectId(data.coordinator_id)},
                    {
                        "$set": {
                            "role": UserRole.DEPARTMENT_COORDINATOR.value,
                            "department": updates.get("code", existing.get("code")),
                            "updated_at": now,
                        }
                    },
                )
        else:
            updates["coordinator_name"] = None
            updates["coordinator_email"] = None

    updates["updated_at"] = now
    await db.departments.update_one({"_id": ObjectId(dept_id)}, {"$set": updates})
    updated_doc = await db.departments.find_one({"_id": ObjectId(dept_id)})
    enriched = await _enrich_department_counts(updated_doc)
    return ApiResponse(
        success=True,
        data=DepartmentResponse(**enriched),
        message="Department updated successfully.",
    )


@router.delete("/{dept_id}", response_model=ApiResponse[dict])
async def delete_department_api(
    dept_id: str,
    admin: dict = Depends(require_roles([UserRole.ADMIN])),
):
    if not ObjectId.is_valid(dept_id):
        raise HTTPException(status_code=400, detail="Invalid Department ID format.")

    db = get_database()
    dept = await db.departments.find_one({"_id": ObjectId(dept_id)})
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found.")

    code = dept.get("code")
    # Check if active students or sections are attached
    stu_count = await db.students.count_documents({"$or": [{"branch": code}, {"department": code}]})
    if stu_count > 0:
        # Soft deactivate instead of hard delete to preserve relationships
        await db.departments.update_one(
            {"_id": ObjectId(dept_id)},
            {"$set": {"is_active": False, "updated_at": datetime.now(timezone.utc)}},
        )
        return ApiResponse(
            success=True,
            data={"id": dept_id, "action": "DEACTIVATED"},
            message=f"Department '{code}' has {stu_count} enrolled students and was safely deactivated.",
        )

    await db.departments.delete_one({"_id": ObjectId(dept_id)})
    return ApiResponse(
        success=True,
        data={"id": dept_id, "action": "DELETED"},
        message=f"Department '{code}' deleted successfully.",
    )
