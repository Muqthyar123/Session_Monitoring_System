import logging
from typing import Dict, List, Optional
from datetime import datetime, timezone
from bson import ObjectId
from app.core.config import settings
from app.db.mongodb import get_database

logger = logging.getLogger("fams.push")

# Lazy Firebase initialization
_firebase_initialized = False


def _init_firebase():
    global _firebase_initialized
    if _firebase_initialized:
        return True
    if settings.FIREBASE_PROJECT_ID and settings.FIREBASE_PRIVATE_KEY and settings.FIREBASE_CLIENT_EMAIL:
        try:
            import firebase_admin
            from firebase_admin import credentials

            if not firebase_admin._apps:
                cred_dict = {
                    "type": "service_account",
                    "project_id": settings.FIREBASE_PROJECT_ID,
                    "private_key": settings.FIREBASE_PRIVATE_KEY.replace("\\n", "\n"),
                    "client_email": settings.FIREBASE_CLIENT_EMAIL,
                }
                cred = credentials.Certificate(cred_dict)
                firebase_admin.initialize_app(cred)
            _firebase_initialized = True
            logger.info("Firebase Admin SDK successfully initialized.")
            return True
        except Exception as e:
            logger.error("Failed to initialize Firebase Admin SDK: %s", str(e))
            return False
    else:
        logger.info("Firebase credentials not set in environment. Push notifications running in dry-run mode.")
        return False


async def register_push_token(user_id: str, token: str, device_info: Optional[str] = None):
    db = get_database()
    now = datetime.now(timezone.utc)
    await db.push_subscriptions.update_one(
        {"token": token},
        {
            "$set": {
                "user_id": user_id,
                "token": token,
                "device_info": device_info,
                "updated_at": now,
            },
            "$setOnInsert": {"created_at": now},
        },
        upsert=True,
    )


async def remove_push_token(token: str):
    db = get_database()
    await db.push_subscriptions.delete_one({"token": token})


async def send_push_notification_to_users(
    user_ids: List[str], title: str, body: str, data: Optional[Dict[str, str]] = None
):
    """Sends browser push notification to given users via FCM if credentials exist."""
    db = get_database()
    # Find all tokens for these user IDs
    object_user_ids = [u for u in user_ids]
    cursor = db.push_subscriptions.find({"user_id": {"$in": object_user_ids}})
    tokens = [doc["token"] async for doc in cursor]

    if not tokens:
        logger.info("No push notification tokens found for targeted users: %s", user_ids)
        return

    is_fb_active = _init_firebase()

    if is_fb_active:
        try:
            from firebase_admin import messaging

            message = messaging.MulticastMessage(
                tokens=tokens,
                notification=messaging.Notification(title=title, body=body),
                data=data or {},
            )
            response = messaging.send_multicast(message)
            logger.info("FCM push notification sent. Success count: %d", response.success_count)
        except Exception as e:
            logger.error("Failed to send FCM push notification: %s", str(e))
    else:
        logger.info(
            "[PUSH DRY-RUN] Title: '%s', Body: '%s', Targeted Tokens: %d",
            title,
            body,
            len(tokens),
        )
