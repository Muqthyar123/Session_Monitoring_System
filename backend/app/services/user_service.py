from datetime import datetime, timezone
from typing import List, Optional
from bson import ObjectId
from fastapi import HTTPException, status
from app.core.security import hash_password
from app.db.mongodb import get_database
from app.schemas.user import UserCreate, UserResponse, UserRole, UserUpdate


async def create_user(data: UserCreate, actor_id: Optional[str] = None) -> UserResponse:
    db = get_database()
    email_clean = data.email.strip().lower()

    existing_email = await db.users.find_one({"email": email_clean})
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User with email '{email_clean}' already exists.",
        )

    if data.roll_number:
        roll_clean = data.roll_number.strip().upper()
        existing_roll = await db.users.find_one({"roll_number": roll_clean})
        if existing_roll:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"User with roll number '{roll_clean}' already exists.",
            )
    else:
        roll_clean = None

    now = datetime.now(timezone.utc)
    if data.role == UserRole.MENTOR:
        raw_pwd = data.password or data.mentor_id or data.roll_number or "mentor1234"
    else:
        raw_pwd = data.password or data.roll_number or "crlr1234"
    hashed_pwd = hash_password(raw_pwd)

    user_doc = {
        "name": data.name.strip(),
        "email": email_clean,
        "password_hash": hashed_pwd,
        "role": data.role.value,
        "roll_number": roll_clean,
        "mentor_id": data.mentor_id.strip().upper() if data.mentor_id else None,
        "phone": data.phone.strip() if data.phone else None,
        "year": data.year.strip() if data.year else None,
        "section": data.section.strip() if data.section else None,
        "designation": data.designation.strip() if data.designation else None,
        "department": data.department.strip() if data.department else None,
        "profile": data.profile.strip() if data.profile else None,
        "is_active": data.is_active,
        "created_at": now,
        "updated_at": now,
    }

    result = await db.users.insert_one(user_doc)
    user_id = str(result.inserted_id)
    user_doc["_id"] = user_id

    # Sync CR/LR assignment to sections collection
    if data.section and data.role in [UserRole.CR, UserRole.LR]:
        await _sync_user_to_section(user_id, data.role.value, data.section)

    if actor_id:
        await db.audit_logs.insert_one(
            {
                "actor_id": actor_id,
                "action": "CREATE_USER",
                "target_user_id": user_id,
                "metadata": {"role": data.role.value, "email": email_clean},
                "created_at": now,
            }
        )

    return UserResponse(**user_doc)


async def _sync_user_to_section(user_id: str, role: str, section_name: str):
    db = get_database()
    section_doc = await db.sections.find_one({"section_name": section_name})
    if section_doc:
        field = "assigned_cr_id" if role == UserRole.CR.value else "assigned_lr_id"
        await db.sections.update_one(
            {"_id": section_doc["_id"]},
            {"$set": {field: user_id, "updated_at": datetime.now(timezone.utc)}},
        )
    else:
        # Create section if it does not exist
        field = "assigned_cr_id" if role == UserRole.CR.value else "assigned_lr_id"
        await db.sections.insert_one(
            {
                "year": "Unknown",
                "section_name": section_name,
                field: user_id,
                "is_active": True,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            }
        )


async def get_users(
    role: Optional[UserRole] = None,
    crlr_only: bool = False,
    section: Optional[str] = None,
    year: Optional[str] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 500,
) -> List[UserResponse]:
    db = get_database()
    query = {}

    if role:
        query["role"] = role.value
    elif crlr_only:
        query["role"] = {"$in": ["CR", "LR"]}

    if section:
        query["section"] = section
    if year:
        query["year"] = year
    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"email": {"$regex": search, "$options": "i"}},
            {"roll_number": {"$regex": search, "$options": "i"}},
            {"mentor_id": {"$regex": search, "$options": "i"}},
            {"designation": {"$regex": search, "$options": "i"}},
            {"department": {"$regex": search, "$options": "i"}},
        ]

    cursor = db.users.find(query).skip(skip).limit(limit).sort("created_at", -1)
    users = []
    async for u in cursor:
        u["_id"] = str(u["_id"])
        users.append(UserResponse(**u))
    return users


def _build_user_query(user_id: str) -> dict:
    user_id_clean = user_id.strip()
    clauses = [
        {"_id": user_id_clean},
        {"mentor_id": user_id_clean.upper()},
        {"roll_number": user_id_clean.upper()},
    ]
    if ObjectId.is_valid(user_id_clean):
        clauses.append({"_id": ObjectId(user_id_clean)})
    return {"$or": clauses}


async def get_user_by_id(user_id: str) -> UserResponse:
    if not user_id or not user_id.strip():
        raise HTTPException(status_code=400, detail="User ID is required.")
    db = get_database()
    u = await db.users.find_one(_build_user_query(user_id))
    if not u:
        raise HTTPException(status_code=404, detail="User not found.")
    u["_id"] = str(u["_id"])
    return UserResponse(**u)


async def update_user(
    user_id: str, data: UserUpdate, actor_id: Optional[str] = None
) -> UserResponse:
    if not user_id or not user_id.strip():
        raise HTTPException(status_code=400, detail="User ID is required.")
    db = get_database()
    u = await db.users.find_one(_build_user_query(user_id))
    if not u:
        raise HTTPException(status_code=404, detail="User not found.")

    doc_id = u["_id"]

    updates = {}
    if data.name is not None:
        updates["name"] = data.name.strip()
    if data.email is not None:
        email_clean = data.email.strip().lower()
        existing = await db.users.find_one(
            {"email": email_clean, "_id": {"$ne": doc_id}}
        )
        if existing:
            raise HTTPException(status_code=400, detail="Email already in use.")
        updates["email"] = email_clean

    if data.role is not None:
        updates["role"] = data.role.value
    if data.mentor_id is not None:
        updates["mentor_id"] = data.mentor_id.strip().upper() if data.mentor_id else None
    if data.roll_number is not None:
        roll_clean = data.roll_number.strip().upper() if data.roll_number else None
        if roll_clean:
            existing_roll = await db.users.find_one(
                {"roll_number": roll_clean, "_id": {"$ne": doc_id}}
            )
            if existing_roll:
                raise HTTPException(
                    status_code=400, detail="Roll number already in use."
                )
        updates["roll_number"] = roll_clean

    if data.phone is not None:
        updates["phone"] = data.phone.strip() if data.phone else None
    if data.year is not None:
        updates["year"] = data.year.strip() if data.year else None
    if data.section is not None:
        updates["section"] = data.section.strip() if data.section else None
    if data.designation is not None:
        updates["designation"] = data.designation.strip() if data.designation else None
    if data.department is not None:
        updates["department"] = data.department.strip() if data.department else None
    if data.profile is not None:
        updates["profile"] = data.profile.strip() if data.profile else None
    if data.is_active is not None:
        updates["is_active"] = data.is_active

    if data.password:
        updates["password_hash"] = hash_password(data.password)

    updates["updated_at"] = datetime.now(timezone.utc)

    await db.users.update_one({"_id": doc_id}, {"$set": updates})
    updated_doc = await db.users.find_one({"_id": doc_id})
    updated_doc["_id"] = str(updated_doc["_id"])

    # Sync section link if role or section updated
    current_role = updated_doc.get("role")
    current_sec = updated_doc.get("section")
    if current_sec and current_role in [UserRole.CR.value, UserRole.LR.value]:
        await _sync_user_to_section(str(doc_id), current_role, current_sec)

    if actor_id:
        await db.audit_logs.insert_one(
            {
                "actor_id": actor_id,
                "action": "UPDATE_USER",
                "target_user_id": str(doc_id),
                "metadata": updates,
                "created_at": datetime.now(timezone.utc),
            }
        )

    return UserResponse(**updated_doc)


async def delete_user(user_id: str, actor_id: Optional[str] = None):
    if not user_id or not user_id.strip():
        raise HTTPException(status_code=400, detail="User ID is required.")
    db = get_database()
    u = await db.users.find_one(_build_user_query(user_id))
    if not u:
        raise HTTPException(status_code=404, detail="User not found.")

    doc_id = u["_id"]
    await db.users.delete_one({"_id": doc_id})

    if actor_id:
        await db.audit_logs.insert_one(
            {
                "actor_id": actor_id,
                "action": "DELETE_USER",
                "target_user_id": str(doc_id),
                "created_at": datetime.now(timezone.utc),
            }
        )


async def delete_all_mentors(actor_id: Optional[str] = None) -> int:
    db = get_database()
    res = await db.users.delete_many({"role": UserRole.MENTOR.value})
    if actor_id:
        await db.audit_logs.insert_one(
            {
                "actor_id": actor_id,
                "action": "RESET_MENTORS",
                "metadata": {"deleted_count": res.deleted_count},
                "created_at": datetime.now(timezone.utc),
            }
        )
    return res.deleted_count

