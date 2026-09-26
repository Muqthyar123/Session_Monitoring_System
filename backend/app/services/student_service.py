from datetime import datetime, timezone
from typing import List, Optional
from bson import ObjectId
from fastapi import HTTPException, status
from app.db.mongodb import get_database
from app.schemas.student import StudentCreate, StudentResponse, StudentUpdate


async def create_student(data: StudentCreate, actor_id: Optional[str] = None) -> StudentResponse:
    db = get_database()
    roll_clean = data.roll_number.strip().upper()

    existing_roll = await db.students.find_one({"roll_number": roll_clean})
    if existing_roll:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Student with roll number '{roll_clean}' already exists.",
        )

    now = datetime.now(timezone.utc)
    student_doc = {
        "year": data.year.strip(),
        "name": data.name.strip(),
        "roll_number": roll_clean,
        "section": data.section.strip().upper(),
        "student_phone": data.student_phone.strip() if data.student_phone else None,
        "parent_phone": data.parent_phone.strip() if data.parent_phone else None,
        "created_at": now,
        "updated_at": now,
    }

    res = await db.students.insert_one(student_doc)
    student_id = str(res.inserted_id)
    student_doc["_id"] = student_id

    if actor_id:
        await db.audit_logs.insert_one({
            "actor_id": actor_id,
            "action": "CREATE_STUDENT",
            "target_student_id": student_id,
            "metadata": {"roll_number": roll_clean},
            "created_at": now,
        })

    return StudentResponse(**student_doc)


async def get_students(
    year: Optional[str] = None,
    section: Optional[str] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 200,
) -> List[StudentResponse]:
    db = get_database()
    query = {}

    if year and year.upper() != "ALL":
        query["year"] = year
    if section and section.upper() != "ALL":
        query["section"] = section.upper()
    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"roll_number": {"$regex": search, "$options": "i"}},
        ]

    cursor = db.students.find(query).skip(skip).limit(limit).sort("roll_number", 1)
    students = []
    async for s in cursor:
        s["_id"] = str(s["_id"])
        students.append(StudentResponse(**s))
    return students


async def update_student(student_id: str, data: StudentUpdate, actor_id: Optional[str] = None) -> StudentResponse:
    if not ObjectId.is_valid(student_id):
        raise HTTPException(status_code=400, detail="Invalid Student ID.")
    db = get_database()
    s = await db.students.find_one({"_id": ObjectId(student_id)})
    if not s:
        raise HTTPException(status_code=404, detail="Student not found.")

    updates = {}
    if data.name is not None:
        updates["name"] = data.name.strip()
    if data.year is not None:
        updates["year"] = data.year.strip()
    if data.section is not None:
        updates["section"] = data.section.strip().upper()
    if data.student_phone is not None:
        updates["student_phone"] = data.student_phone.strip() if data.student_phone else None
    if data.parent_phone is not None:
        updates["parent_phone"] = data.parent_phone.strip() if data.parent_phone else None

    if data.roll_number is not None:
        roll_clean = data.roll_number.strip().upper()
        existing = await db.students.find_one({"roll_number": roll_clean, "_id": {"$ne": ObjectId(student_id)}})
        if existing:
            raise HTTPException(status_code=400, detail=f"Roll number '{roll_clean}' is already in use.")
        updates["roll_number"] = roll_clean

    updates["updated_at"] = datetime.now(timezone.utc)

    await db.students.update_one({"_id": ObjectId(student_id)}, {"$set": updates})
    updated_doc = await db.students.find_one({"_id": ObjectId(student_id)})
    updated_doc["_id"] = str(updated_doc["_id"])

    if actor_id:
        await db.audit_logs.insert_one({
            "actor_id": actor_id,
            "action": "UPDATE_STUDENT",
            "target_student_id": student_id,
            "created_at": datetime.now(timezone.utc),
        })

    return StudentResponse(**updated_doc)


async def delete_student(student_id: str, actor_id: Optional[str] = None):
    if not ObjectId.is_valid(student_id):
        raise HTTPException(status_code=400, detail="Invalid Student ID.")
    db = get_database()
    s = await db.students.find_one({"_id": ObjectId(student_id)})
    if not s:
        raise HTTPException(status_code=404, detail="Student not found.")

    await db.students.delete_one({"_id": ObjectId(student_id)})

    if actor_id:
        await db.audit_logs.insert_one({
            "actor_id": actor_id,
            "action": "DELETE_STUDENT",
            "target_student_id": student_id,
            "created_at": datetime.now(timezone.utc),
        })
