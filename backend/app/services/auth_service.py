from datetime import datetime, timezone
from bson import ObjectId
from fastapi import HTTPException, status
from app.core.security import create_access_token, hash_password, verify_password
from app.db.mongodb import get_database
from app.schemas.auth import AuthUserInfo, LoginRequest, LoginResponse
from app.schemas.user import UserRole


async def authenticate_user(login_data: LoginRequest) -> LoginResponse:
    db = get_database()
    raw_ident = login_data.email.strip()
    email_clean = raw_ident.lower()
    
    # Try finding user by email, mentor_id, or roll_number
    user = await db.users.find_one({
        "$or": [
            {"email": email_clean},
            {"mentor_id": raw_ident},
            {"mentor_id": raw_ident.upper()},
            {"roll_number": raw_ident},
            {"roll_number": raw_ident.upper()}
        ]
    })

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials.",
        )

    if not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled. Please contact administrator.",
        )

    pwd_valid = verify_password(login_data.password, user.get("password_hash", ""))
    
    # Fallback check: CR/LR default password is their roll number
    if not pwd_valid and user.get("roll_number"):
        clean_user_roll = user.get("roll_number", "").strip().upper()
        if clean_user_roll and login_data.password.strip().upper() == clean_user_roll:
            pwd_valid = True
            # Upgrade stored password hash to match their roll number
            await db.users.update_one(
                {"_id": user["_id"]},
                {"$set": {"password_hash": hash_password(clean_user_roll)}}
            )

    # Fallback check for mentors: default password is their mentor_id
    if not pwd_valid and user.get("mentor_id"):
        clean_m_id = user.get("mentor_id", "").strip().upper()
        if clean_m_id and login_data.password.strip().upper() == clean_m_id:
            pwd_valid = True
            await db.users.update_one(
                {"_id": user["_id"]},
                {"$set": {"password_hash": hash_password(clean_m_id)}}
            )

    if not pwd_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials.",
        )

    role = user.get("role")
    if login_data.portal == "ADMIN" and role != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account is not an administrator account.",
        )
    if login_data.portal == "CRLR" and role not in [UserRole.CR.value, UserRole.LR.value]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This portal is strictly for Class & Lateral Representatives.",
        )
    if login_data.portal == "MENTOR" and role != UserRole.MENTOR.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This portal is strictly for Mentors.",
        )

    token_data = {
        "sub": str(user["_id"]),
        "email": user["email"],
        "role": role,
    }
    access_token = create_access_token(data=token_data)

    # Log audit entry
    await db.audit_logs.insert_one(
        {
            "actor_id": str(user["_id"]),
            "actor_email": user["email"],
            "action": "LOGIN",
            "metadata": {"portal": login_data.portal},
            "created_at": datetime.now(timezone.utc),
        }
    )

    user_info = AuthUserInfo(
        id=str(user["_id"]),
        name=user.get("name", ""),
        email=user.get("email", ""),
        role=UserRole(role),
        mentor_id=user.get("mentor_id"),
        phone=user.get("phone"),
        department=user.get("department"),
        designation=user.get("designation"),
        section=user.get("section"),
        year=user.get("year"),
        roll_number=user.get("roll_number"),
    )

    return LoginResponse(access_token=access_token, token_type="bearer", user=user_info)


async def change_user_password(user_id: str, old_pass: str, new_pass: str):
    db = get_database()
    user = await db.users.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    if not verify_password(old_pass, user.get("password_hash", "")):
        raise HTTPException(status_code=400, detail="Current password is incorrect.")

    new_hash = hash_password(new_pass)
    await db.users.update_one(
        {"_id": ObjectId(user_id)},
        {
            "$set": {
                "password_hash": new_hash,
                "updated_at": datetime.now(timezone.utc),
            }
        },
    )
