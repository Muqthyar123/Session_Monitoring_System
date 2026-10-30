from datetime import datetime, timedelta, timezone
from html import escape
import hashlib
import os
import secrets
import re
import httpx
import logging
from urllib.parse import urlsplit
import time
from typing import Optional
from bson import ObjectId
from fastapi import HTTPException, status
from app.core.security import create_access_token, hash_password, verify_password
from app.core.config import settings
from app.db.mongodb import get_database
from app.schemas.auth import AuthUserInfo, LoginRequest, LoginResponse
from app.schemas.user import UserRole


RESET_GENERIC_MESSAGE = "If an account exists, a reset email will be sent when mail delivery is available. Check your spam folder or contact the administrator if it does not arrive."
logger = logging.getLogger("fams.auth")
_brevo_diagnostics_checked = False
_brevo_configuration_ready = False
_brevo_diagnostics_checked_at = 0.0
_BREVO_DIAGNOSTICS_TTL_SECONDS = 60
PRODUCTION_FRONTEND_URL = "https://session-monitoring-system.vercel.app"


def _reset_token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _reset_frontend_url() -> str:
    """Use the deployed application for production reset links, never localhost."""
    configured_url = (settings.FRONTEND_URL or "").strip().rstrip("/")
    if os.getenv("RENDER", "").casefold() == "true":
        hostname = (urlsplit(configured_url).hostname or "").casefold()
        if hostname in {"localhost", "127.0.0.1", "::1"} or not hostname:
            return PRODUCTION_FRONTEND_URL
    return configured_url or PRODUCTION_FRONTEND_URL


async def diagnose_brevo_configuration() -> bool:
    """Check Brevo credentials and sender, caching the result briefly per worker."""
    global _brevo_diagnostics_checked, _brevo_configuration_ready, _brevo_diagnostics_checked_at
    if _brevo_diagnostics_checked and time.monotonic() - _brevo_diagnostics_checked_at < _BREVO_DIAGNOSTICS_TTL_SECONDS:
        return _brevo_configuration_ready

    api_key = (settings.BREVO_API_KEY or "").strip()
    sender_email = (settings.BREVO_SENDER_MAIL or "").strip()
    key_kind = (
        "api_v3_prefix" if api_key.startswith("xkeysib-")
        else "smtp_prefix" if api_key.startswith("xsmtpsib-")
        else "unknown_prefix"
    ) if api_key else "missing"
    production_reset_url = _reset_frontend_url().casefold() == PRODUCTION_FRONTEND_URL
    logger.info(
        "Brevo config loaded: api_key_present=%s key_kind=%s sender_configured=%s production_frontend_url=%s",
        bool(api_key), key_kind, bool(sender_email), production_reset_url,
    )
    if not api_key or not sender_email:
        _brevo_diagnostics_checked = True
        _brevo_diagnostics_checked_at = time.monotonic()
        _brevo_configuration_ready = False
        return False

    headers = {"api-key": api_key, "accept": "application/json"}
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            account_response = await client.get("https://api.brevo.com/v3/account", headers=headers)
            logger.info("Brevo account authentication check: HTTP %s.", account_response.status_code)
            if account_response.status_code != 200:
                _brevo_diagnostics_checked = True
                _brevo_diagnostics_checked_at = time.monotonic()
                _brevo_configuration_ready = False
                return False

            sender_response = await client.get("https://api.brevo.com/v3/senders", headers=headers)
            _brevo_diagnostics_checked = True
            _brevo_diagnostics_checked_at = time.monotonic()
            if sender_response.status_code != 200:
                logger.warning("Brevo sender verification lookup returned HTTP %s.", sender_response.status_code)
                _brevo_configuration_ready = False
                return False
            senders = sender_response.json().get("senders", [])
            configured_sender_is_active = any(
                str(item.get("email", "")).casefold() == sender_email.casefold()
                and item.get("active") is True
                for item in senders
            )
            _brevo_configuration_ready = configured_sender_is_active
            logger.info("Configured Brevo sender is listed as active: %s.", configured_sender_is_active)
            return _brevo_configuration_ready
    except httpx.RequestError as exc:
        logger.warning("Brevo configuration check could not reach the provider (%s).", type(exc).__name__)
    except Exception as exc:
        logger.warning("Brevo configuration check failed (%s).", type(exc).__name__)
    _brevo_diagnostics_checked = False
    _brevo_configuration_ready = False
    return False


async def verify_password_reset_token(token: str) -> Optional[str]:
    db = get_database()
    record = await db.password_reset_tokens.find_one({
        "token_hash": _reset_token_hash(token), "used_at": None,
        "expires_at": {"$gt": datetime.now(timezone.utc)},
    })
    return record.get("role") if record else None


async def request_password_reset(email: str) -> None:
    if not await diagnose_brevo_configuration():
        raise HTTPException(
            status_code=503,
            detail="Password reset email is temporarily unavailable. Please contact the administrator.",
        )
    db = get_database()
    email_clean = email.strip().lower()
    user = await db.users.find_one({"email": email_clean, "is_active": {"$ne": False}})
    if not user:
        return
    # Don't create a discoverable token if email delivery is not configured.
    api_key = (settings.BREVO_API_KEY or "").strip()
    sender_email = (settings.BREVO_SENDER_MAIL or "").strip()
    if not api_key or not sender_email:
        missing = []
        if not api_key:
            missing.append("BREVO_API_KEY")
        if not sender_email:
            missing.append("BREVO_SENDER_MAIL")
        logger.error("Password reset email is not configured; missing %s.", ", ".join(missing))
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
    reset_url = _reset_frontend_url() + "/reset-password?token=" + token
    recipient_name = escape(str(user.get("name") or "there"))
    safe_reset_url = escape(reset_url, quote=True)
    payload = {
        "sender": {"email": sender_email, "name": settings.BREVO_SENDER_NAME},
        "to": [{"email": email_clean, "name": user.get("name", "")[:100]}],
        "subject": "Password Reset Request — College Session Monitoring System",
        "textContent": (
            f"Hello {user.get('name') or 'there'},\n\n"
            "We received a request to reset your password for your College Session Monitoring System account.\n\n"
            f"Set a new password using this link (it expires in 20 minutes):\n{reset_url}\n\n"
            "If you did not request a password reset, you can safely ignore this email."
        ),
        "htmlContent": f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;background:#f3f6fb;font-family:Arial,Helvetica,sans-serif;color:#263445;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#f3f6fb;padding:32px 12px;">
    <tr><td align="center">
      <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:600px;background:#ffffff;border:1px solid #dce4ef;border-radius:12px;">
        <tr><td style="padding:36px 32px 28px;">
          <p style="margin:0 0 8px;color:#1d4f91;font-size:26px;line-height:1.3;font-weight:700;">Password Reset Request</p>
          <p style="margin:20px 0 12px;font-size:16px;line-height:1.6;">Hello <strong>{recipient_name}</strong>,</p>
          <p style="margin:0 0 18px;font-size:16px;line-height:1.6;">We received a request to reset the password for your College Session Monitoring System account.</p>
          <p style="margin:0 0 22px;font-size:16px;line-height:1.6;">Choose a new password by using the button below. This secure link expires in <strong>20 minutes</strong>.</p>
          <p style="margin:0 0 26px;"><a href="{safe_reset_url}" style="display:inline-block;padding:14px 24px;border-radius:7px;background:#1d4f91;color:#ffffff;text-decoration:none;font-size:16px;font-weight:700;">Reset Password</a></p>
          <p style="margin:0 0 8px;font-size:14px;line-height:1.6;color:#526273;">If the button does not work, copy and paste this link into your browser:</p>
          <p style="margin:0 0 24px;font-size:14px;line-height:1.6;word-break:break-all;"><a href="{safe_reset_url}" style="color:#1d4f91;">{escape(reset_url)}</a></p>
          <hr style="border:0;border-top:1px solid #e4eaf2;margin:24px 0;">
          <p style="margin:0;font-size:13px;line-height:1.6;color:#667587;">If you did not request a password reset, you can safely ignore this email. Your password will remain unchanged.</p>
          <p style="margin:18px 0 0;font-size:13px;color:#667587;">College Session Monitoring System</p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body></html>""",
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post("https://api.brevo.com/v3/smtp/email", json=payload,
                headers={"api-key": api_key, "accept": "application/json", "content-type": "application/json"})
            response.raise_for_status()
        logger.info("Brevo accepted a password reset email request (HTTP %s).", response.status_code)
    except httpx.HTTPStatusError as exc:
        await db.password_reset_tokens.update_one({"token_hash": _reset_token_hash(token)}, {"$set": {"used_at": now}})
        logger.error("Brevo rejected a password reset email request (HTTP %s).", exc.response.status_code)
        if exc.response.status_code in {401, 403}:
            global _brevo_diagnostics_checked, _brevo_configuration_ready, _brevo_diagnostics_checked_at
            _brevo_diagnostics_checked = False
            _brevo_configuration_ready = False
            _brevo_diagnostics_checked_at = 0.0
        raise HTTPException(
            status_code=503,
            detail="Password reset email is temporarily unavailable. Please contact the administrator.",
        ) from None
    except httpx.RequestError as exc:
        await db.password_reset_tokens.update_one({"token_hash": _reset_token_hash(token)}, {"$set": {"used_at": now}})
        logger.error("Brevo password reset email request could not reach the provider (%s).", type(exc).__name__)
        raise HTTPException(
            status_code=503,
            detail="Password reset email is temporarily unavailable. Please contact the administrator.",
        ) from None
    except Exception as exc:
        await db.password_reset_tokens.update_one({"token_hash": _reset_token_hash(token)}, {"$set": {"used_at": now}})
        logger.error("Password reset email processing failed (%s).", type(exc).__name__)
        raise HTTPException(
            status_code=503,
            detail="Password reset email is temporarily unavailable. Please contact the administrator.",
        ) from None


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
