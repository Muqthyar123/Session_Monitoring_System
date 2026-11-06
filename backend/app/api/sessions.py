from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from app.core.dependencies import enforce_assigned_branch, enforce_assigned_department, enforce_assigned_year, get_assigned_years, get_current_user
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
@router.get("", response_model=ApiResponse[List[ClassSessionResponse]])
async def get_today_sessions_api(
    year: Optional[str] = Query(None, description="Filter by Academic Year"),
    section: Optional[str] = Query(None, description="Filter by Section"),
    branch: Optional[str] = Query(None, description="Filter by Branch / Department"),
    status: Optional[str] = Query(None, description="Filter by Session Status: ALL, ACTIVE, COMPLETED, UPCOMING, EXPIRED, PENDING"),
    date: Optional[str] = Query(None, description="YYYY-MM-DD date string"),
    current_user: dict = Depends(get_current_user),
):
    user_role = current_user.get("role")
    user_sec = current_user.get("section")

    # If user is CR or LR, force section restriction
    years = get_assigned_years(current_user)
    if user_role in [UserRole.CR.value, UserRole.LR.value]:
        section = user_sec
    elif user_role in [UserRole.ADMIN.value, UserRole.MENTOR.value]:
        year = enforce_assigned_year(current_user, year)
        enforce_assigned_branch(current_user, branch)
        branch = enforce_assigned_department(current_user, None)
    elif user_role in [UserRole.DEPARTMENT_COORDINATOR.value, UserRole.COORDINATOR.value]:
        user_dept = current_user.get("department") or current_user.get("branch")
        if user_dept:
            branch = user_dept

    data = await get_sessions(section=section, year=year, branch=branch, status_filter=status, date_str=date,
                              years=years if years is not None and year is None else None)
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
    elif user_role in [UserRole.ADMIN.value, UserRole.MENTOR.value]:
        department = enforce_assigned_department(current_user, None)
        if not section or (department and department.casefold() not in section.casefold()):
            raise HTTPException(status_code=403, detail="Access denied for this department's section.")
    elif not section:
        raise HTTPException(
            status_code=400, detail="Section query parameter is required for administrators."
        )

    data = await get_active_sessions_for_section(section)
    if user_role in [UserRole.ADMIN.value, UserRole.MENTOR.value]:
        years = get_assigned_years(current_user) or []
        data = [item for item in data if item.year in years and
                (not department or department.casefold() in item.section.casefold())]
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
    if user_role in [UserRole.ADMIN.value, UserRole.MENTOR.value]:
        enforce_assigned_year(current_user, session.year)
        department = enforce_assigned_department(current_user, None)
        if department and department.casefold() not in session.section.casefold():
            raise HTTPException(status_code=403, detail="Access denied for this department's session.")

    return ApiResponse(success=True, data=session)
