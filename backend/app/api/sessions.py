from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from app.core.dependencies import get_current_user
from app.schemas.common import ApiResponse
from app.schemas.session import ClassSessionResponse
from app.schemas.user import UserRole
from app.services.session_service import (
    get_active_sessions_for_section,
    get_session_by_id,
    get_sessions,
)

router = APIRouter(prefix="/sessions", tags=["Class Sessions"])


@router.get("/today", response_model=ApiResponse[List[ClassSessionResponse]])
async def get_today_sessions_api(
    section: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user),
):
    user_role = current_user.get("role")
    user_sec = current_user.get("section")

    # If user is CR or LR, force section restriction
    if user_role in [UserRole.CR.value, UserRole.LR.value]:
        section = user_sec

    data = await get_sessions(section=section)
    return ApiResponse(success=True, data=data)


@router.get("/active", response_model=ApiResponse[List[ClassSessionResponse]])
async def get_active_sessions_api(
    section: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user),
):
    user_role = current_user.get("role")
    user_sec = current_user.get("section")

    if user_role in [UserRole.CR.value, UserRole.LR.value]:
        section = user_sec
    elif not section:
        raise HTTPException(
            status_code=400, detail="Section query parameter is required for administrators."
        )

    data = await get_active_sessions_for_section(section)
    return ApiResponse(success=True, data=data)


@router.get("/{session_id}", response_model=ApiResponse[ClassSessionResponse])
async def get_session_details_api(
    session_id: str,
    current_user: dict = Depends(get_current_user),
):
    session = await get_session_by_id(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    user_role = current_user.get("role")
    user_sec = current_user.get("section")
    if user_role in [UserRole.CR.value, UserRole.LR.value] and session.section != user_sec:
        raise HTTPException(
            status_code=403, detail="Access denied. You can only view sessions for your assigned section."
        )

    return ApiResponse(success=True, data=session)
