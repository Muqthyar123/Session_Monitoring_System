from typing import List
from fastapi import APIRouter, Depends, Query, status
from app.core.dependencies import get_current_user
from app.schemas.common import ApiResponse
from app.schemas.notification import NotificationResponse
from app.services.notification_service import (
    get_unread_count,
    get_user_notifications,
    mark_all_notifications_read,
    mark_notification_read,
)

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("", response_model=ApiResponse[List[NotificationResponse]])
async def list_notifications_api(
    limit: int = Query(50, ge=1, le=200),
    current_user: dict = Depends(get_current_user),
):
    items = await get_user_notifications(current_user["id"], limit=limit)
    return ApiResponse(success=True, data=items)


@router.get("/unread-count", response_model=ApiResponse[dict])
async def get_unread_count_api(
    current_user: dict = Depends(get_current_user),
):
    count = await get_unread_count(current_user["id"])
    return ApiResponse(success=True, data={"unread_count": count})


@router.patch("/{notification_id}/read", response_model=ApiResponse[dict])
async def mark_read_api(
    notification_id: str,
    current_user: dict = Depends(get_current_user),
):
    await mark_notification_read(notification_id, current_user["id"])
    return ApiResponse(success=True, message="Notification marked as read.")


@router.patch("/read-all", response_model=ApiResponse[dict])
async def mark_all_read_api(
    current_user: dict = Depends(get_current_user),
):
    await mark_all_notifications_read(current_user["id"])
    return ApiResponse(success=True, message="All notifications marked as read.")
