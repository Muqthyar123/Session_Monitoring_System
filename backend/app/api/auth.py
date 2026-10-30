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
from app.schemas.auth import ForgotPasswordRequest, ResetTokenRequest, ResetPasswordRequest
from app.services.auth_service import request_password_reset, verify_password_reset_token, reset_password

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/forgot-password", response_model=ApiResponse[dict])
async def forgot_password_api(data: ForgotPasswordRequest):
    await request_password_reset(str(data.email))
    return ApiResponse(success=True, data={}, message="If an account exists with this email address, a password reset link has been sent.")


@router.post("/verify-reset-token", response_model=ApiResponse[dict])
async def verify_reset_token_api(data: ResetTokenRequest):
    role = await verify_password_reset_token(data.token)
    if not role:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="This password reset link is invalid or has expired.")
    return ApiResponse(success=True, data={"valid": True, "role": role})


@router.post("/reset-password", response_model=ApiResponse[dict])
async def reset_password_api(data: ResetPasswordRequest):
    await reset_password(data.token, data.new_password)
    return ApiResponse(success=True, data={}, message="Password reset successfully. Please sign in with your new password.")


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
        mentor_id=current_user.get("mentor_id"),
        phone=current_user.get("phone"),
        department=current_user.get("department"),
        designation=current_user.get("designation"),
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
