from fastapi import APIRouter, Depends, status
from app.core.dependencies import get_current_user
from app.schemas.auth import (
    AuthUserInfo,
    LoginRequest,
    LoginResponse,
    PasswordChangeRequest,
)
from app.schemas.common import ApiResponse
from app.schemas.user import UserRole
from app.services.auth_service import authenticate_user, change_user_password

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=ApiResponse[LoginResponse])
async def login_api(data: LoginRequest):
    result = await authenticate_user(data)
    return ApiResponse(
        success=True, data=result, message="Login successful."
    )


@router.get("/me", response_model=ApiResponse[AuthUserInfo])
async def get_me_api(current_user: dict = Depends(get_current_user)):
    user_info = AuthUserInfo(
        id=current_user["id"],
        name=current_user.get("name", ""),
        email=current_user.get("email", ""),
        role=UserRole(current_user.get("role")),
        section=current_user.get("section"),
        year=current_user.get("year"),
        roll_number=current_user.get("roll_number"),
    )
    return ApiResponse(success=True, data=user_info)


@router.post("/change-password", response_model=ApiResponse[dict])
async def change_password_api(
    data: PasswordChangeRequest, current_user: dict = Depends(get_current_user)
):
    await change_user_password(current_user["id"], data.old_password, data.new_password)
    return ApiResponse(success=True, message="Password successfully changed.")
