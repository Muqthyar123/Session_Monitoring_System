from datetime import datetime, timedelta, timezone
import hashlib
import secrets
import re
import httpx
import logging
from typing import Optional
from bson import ObjectId
from fastapi import HTTPException, status
from app.core.security import create_access_token, hash_password, verify_password
from app.core.config import settings
from app.db.mongodb import get_database
from app.schemas.auth import AuthUserInfo, LoginRequest, LoginResponse
from app.schemas.user import UserRole


RESET_GENERIC_MESSAGE = "If an account exists with this email address, a password reset link has been sent."
logger = logging.getLogger("fams.auth")


def _reset_token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


async def verify_password_reset_token(token: str) -> Optional[str]:
    db = get_database()
    record = await db.password_reset_tokens.find_one({
        "token_hash": _reset_token_hash(token), "used_at": None,
        "expires_at": {"$gt": datetime.now(timezone.utc)},
    })
    return record.get("role") if record else None


async def request_password_reset(email: str) -> None:
    db = get_database()
    email_clean = email.strip().lower()
    user = await db.users.find_one({"email": email_clean, "is_active": {"$ne": False}})
    if not user:
        return
    # Don't create a discoverable token if email delivery is not configured.
    if not settings.BREVO_API_KEY or not settings.BREVO_SENDER_MAIL:
        logger.warning("Password reset email is not configured.")
        return
    token = secrets.token_urlsafe(48)
    now = datetime.now(timezone.utc)
    await db.password_reset_tokens.update_many(
        {"user_id": str(user["_id"]), "used_at": None},
        {"$set": {"used_at": now, "invalidated_at": now}},
    )
    await db.password_reset_tokens.insert_one({
        "user_id": str(user["_id"]), "role": user.get("role"),
        "token_hash": _reset_token_hash(token), "created_at": now,
        "expires_at": now + timedelta(minutes=20), "used_at": None,
    })
    reset_url = settings.FRONTEND_URL.rstrip("/") + "/reset-password?token=" + token
    payload = {
        "sender": {"email": settings.BREVO_SENDER_MAIL, "name": settings.BREVO_SENDER_NAME},
        "to": [{"email": email_clean, "name": user.get("name", "")[:100]}],
        "subject": "Reset your College Session Monitoring System password",
        "textContent": f"Use this link to reset your password. It expires in 20 minutes: {reset_url}",
        "htmlContent": f"<p>We received a request to reset your password.</p><p><a href=\"{reset_url}\">Reset password</a></p><p>This link expires in 20 minutes. If you did not request this, ignore this email.</p>",
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post("https://api.brevo.com/v3/smtp/email", json=payload,
                headers={"api-key": settings.BREVO_API_KEY, "accept": "application/json", "content-type": "application/json"})
            response.raise_for_status()
    except Exception:
        await db.password_reset_tokens.update_one({"token_hash": _reset_token_hash(token)}, {"$set": {"used_at": now}})
        logger.warning("Brevo password reset email request failed.")


async def reset_password(token: str, new_password: str) -> None:
    if not re.search(r"[A-Za-z]", new_password) or not re.search(r"\d", new_password):
        raise HTTPException(status_code=422, detail="Password must contain at least one letter and one number.")
    db = get_database()
    now = datetime.now(timezone.utc)
    record = await db.password_reset_tokens.find_one_and_update(
        {"token_hash": _reset_token_hash(token), "used_at": None, "expires_at": {"$gt": now}},
        {"$set": {"used_at": now}},
    )
    if not record:
        raise HTTPException(status_code=400, detail="This password reset link is invalid or has expired.")
    try:
        user_id = ObjectId(record["user_id"])
    except Exception:
        await db.password_reset_tokens.update_one({"_id": record["_id"]}, {"$set": {"used_at": now, "invalidated_at": now}})
        raise HTTPException(status_code=400, detail="This password reset link is invalid or has expired.") from None
    result = await db.users.update_one({"_id": user_id, "role": record.get("role")}, {"$set": {"password_hash": hash_password(new_password), "updated_at": now}})
    if not result.modified_count:
        raise HTTPException(status_code=400, detail="This password reset link is invalid or has expired.")
    await db.password_reset_tokens.update_many({"user_id": record["user_id"], "used_at": None}, {"$set": {"used_at": now, "invalidated_at": now}})


async def authenticate_user(login_data: LoginRequest) -> LoginResponse:
    db = get_database()
    raw_ident = login_data.email.strip()
    email_clean = raw_ident.lower()
    
    # Try finding user by email, employee_id, mentor_id, or roll_number
    or_clauses = [
        {"email": email_clean},
        {"employee_id": raw_ident},
        {"employee_id": raw_ident.upper()},
        {"mentor_id": raw_ident},
        {"mentor_id": raw_ident.upper()},
        {"roll_number": raw_ident},
        {"roll_number": raw_ident.upper()}
    ]
    if raw_ident.isdigit():
        or_clauses.extend([
            {"employee_id": int(raw_ident)},
            {"mentor_id": int(raw_ident)},
        ])

    user = await db.users.find_one({"$or": or_clauses})

    # Resilient fallback if $or misses in mock or remote DB
    if not user:
        user = (
            await db.users.find_one({"employee_id": raw_ident})
            or await db.users.find_one({"mentor_id": raw_ident})
            or await db.users.find_one({"roll_number": raw_ident.upper()})
            or await db.users.find_one({"email": email_clean})
        )
        if not user and raw_ident.isdigit():
            user = (
                await db.users.find_one({"employee_id": int(raw_ident)})
                or await db.users.find_one({"mentor_id": int(raw_ident)})
            )

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
        mentor_id=user.get("mentor_id") or user.get("employee_id"),
        employee_id=user.get("employee_id") or user.get("mentor_id"),
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
