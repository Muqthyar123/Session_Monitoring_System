from datetime import datetime, timezone
from bson import ObjectId
from fastapi import HTTPException, status
from app.core.security import create_access_token, hash_password, verify_password
from app.db.mongodb import get_database
from app.schemas.auth import AuthUserInfo, LoginRequest, LoginResponse
from app.schemas.user import UserRole


async def authenticate_user(login_data: LoginRequest) -> LoginResponse:
    db = get_database()
    email_clean = login_data.email.strip().lower()
    user = await db.users.find_one({"email": email_clean})

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    if not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled. Please contact administrator.",
        )

    if not verify_password(login_data.password, user.get("password_hash", "")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    role = user.get("role")
    if login_data.portal == "ADMIN" and role != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account is not an administrator account.",
        )
    if login_data.portal == "CRLR" and role == UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrators must use the Admin login page.",
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
