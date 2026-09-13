from fastapi import APIRouter, Depends, status
from app.core.dependencies import get_current_user
from app.schemas.common import ApiResponse
from app.schemas.notification import PushSubscriptionRegisterRequest
from app.services.push_service import register_push_token, remove_push_token

router = APIRouter(prefix="/push", tags=["Push Notifications"])


@router.post("/register", response_model=ApiResponse[dict])
async def register_push_api(
    data: PushSubscriptionRegisterRequest,
    current_user: dict = Depends(get_current_user),
):
    await register_push_token(
        user_id=current_user["id"], token=data.token, device_info=data.device_info
    )
    return ApiResponse(
        success=True, message="Push notification subscription registered successfully."
    )


@router.delete("/register", response_model=ApiResponse[dict])
async def unregister_push_api(
    data: PushSubscriptionRegisterRequest,
    current_user: dict = Depends(get_current_user),
):
    await remove_push_token(token=data.token)
    return ApiResponse(
        success=True, message="Push notification subscription removed."
    )
