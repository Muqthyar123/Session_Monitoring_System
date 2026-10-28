import re
from datetime import datetime, timezone

from bson import ObjectId

from app.core.security import hash_password, verify_password
from app.schemas.user import UserRole


def normalize_admin_email(email: str) -> str:
    clean = email.strip().lower()
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", clean):
        raise ValueError("Enter a valid administrator email address.")
    return clean


def validate_admin_password(password: str) -> None:
    if not 8 <= len(password) <= 12:
        raise ValueError("Administrator password must be between 8 and 12 characters.")


def _email_query(email: str) -> dict:
    clean = normalize_admin_email(email)
    return {"email": {"$regex": f"^{re.escape(clean)}$", "$options": "i"}}


async def create_first_admin(db, email: str, name: str, password: str) -> str:
    """Create the first admin only; never duplicate or silently elevate an account."""
    clean_email = normalize_admin_email(email)
    validate_admin_password(password)

    existing = await db.users.find_one(_email_query(clean_email))
    if existing:
        if existing.get("role") == UserRole.ADMIN.value:
            raise ValueError("This administrator account already exists. Use verify or reset-password.")
        raise ValueError("This email already belongs to a non-administrator account.")

    if await db.users.count_documents({"role": UserRole.ADMIN.value}):
        raise ValueError("An administrator already exists. Create additional admins through the authenticated admin workflow.")

    now = datetime.now(timezone.utc)
    await db.users.insert_one({
        "_id": ObjectId(),
        "name": name.strip() or "System Administrator",
        "email": clean_email,
        "password_hash": hash_password(password),
        "role": UserRole.ADMIN.value,
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    })
    return "created"


async def verify_admin_credentials(db, email: str, password: str) -> bool:
    clean_email = normalize_admin_email(email)
    user = await db.users.find_one(_email_query(clean_email))
    if not user or user.get("role") != UserRole.ADMIN.value or not user.get("is_active", True):
        return False
    return verify_password(password, user.get("password_hash", ""))


async def reset_admin_password(db, email: str, password: str) -> None:
    clean_email = normalize_admin_email(email)
    validate_admin_password(password)
    user = await db.users.find_one(_email_query(clean_email))
    if not user or user.get("role") != UserRole.ADMIN.value:
        raise ValueError("An administrator account with this email was not found.")

    result = await db.users.update_one(
        {"_id": user["_id"]},
        {"$set": {"password_hash": hash_password(password), "updated_at": datetime.now(timezone.utc)}},
    )
    if result.matched_count != 1:
        raise RuntimeError("Administrator password could not be updated.")
