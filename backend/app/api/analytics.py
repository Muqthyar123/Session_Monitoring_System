from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from app.core.dependencies import get_current_user, require_roles
from app.core.dependencies import enforce_assigned_year
from app.schemas.common import ApiResponse
from app.schemas.user import UserRole
from app.services.analytics_service import (
    get_admin_dashboard_analytics,
    get_crlr_dashboard_analytics,
    get_faculty_analytics,
    get_faculty_history,
)

router = APIRouter(tags=["Analytics & Dashboards"])


@router.get("/admin/analytics", response_model=ApiResponse[dict])
async def get_admin_analytics_api(
    admin: dict = Depends(require_roles([UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.DEPARTMENT_COORDINATOR, UserRole.COORDINATOR])),
):
    data = await get_admin_dashboard_analytics(admin)
    return ApiResponse(success=True, data=data)


@router.get("/crlr/analytics", response_model=ApiResponse[dict])
async def get_crlr_analytics_api(
    current_user: dict = Depends(get_current_user),
):
    user_role = current_user.get("role")
    user_sec = current_user.get("section")

    if user_role not in [UserRole.CR.value, UserRole.LR.value] or not user_sec:
        raise HTTPException(
            status_code=403, detail="CR/LR analytics requires an assigned section."
        )

    data = await get_crlr_dashboard_analytics(user_sec)
    return ApiResponse(success=True, data=data)


@router.get("/analytics/faculty", response_model=ApiResponse[list])
async def get_faculty_analytics_api(
    section: Optional[str] = Query(None, description="Section name or ALL"),
    current_user: dict = Depends(get_current_user),
):
    if current_user.get("role") not in [UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value]:
        raise HTTPException(status_code=403, detail="Faculty analytics is restricted to administrators.")
    if current_user.get("role") == UserRole.ADMIN.value:
        from app.core.dependencies import enforce_assigned_branch, enforce_assigned_department, get_assigned_years
        enforce_assigned_branch(current_user, None)
        if section and section.upper() != "ALL":
            department = enforce_assigned_department(current_user, None)
            if department and department.casefold() not in section.casefold():
                raise HTTPException(status_code=403, detail="Access denied for this department's section.")
        years = get_assigned_years(current_user) or []
        department = enforce_assigned_department(current_user, None)
        data = await get_faculty_analytics(section, years=years, department=department)
    else:
        data = await get_faculty_analytics(section)
    return ApiResponse(success=True, data=data)


@router.get("/analytics/faculty/{faculty_name}/history", response_model=ApiResponse[dict])
@router.get("/admin/faculty/{faculty_name}/history", response_model=ApiResponse[dict])
async def get_faculty_history_api(
    faculty_name: str,
    period: Optional[str] = Query("this_month", description="today, this_week, this_month, custom"),
    start_date: Optional[str] = Query(None, description="YYYY-MM-DD for custom range"),
    end_date: Optional[str] = Query(None, description="YYYY-MM-DD for custom range"),
    section: Optional[str] = Query(None),
    year: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user),
):
    if current_user.get("role") not in [UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value]:
        raise HTTPException(status_code=403, detail="Faculty history is restricted to administrators.")
    years = None
    department = None
    if current_user.get("role") == UserRole.ADMIN.value:
        from app.core.dependencies import enforce_assigned_department, get_assigned_years
        if not year:
            raise HTTPException(status_code=403, detail="Choose an assigned academic year to view faculty history.")
        enforce_assigned_year(current_user, year)
        years = get_assigned_years(current_user) or []
        department = enforce_assigned_department(current_user, None)
        if section and department and department.casefold() not in section.casefold():
            raise HTTPException(status_code=403, detail="Access denied for this department's section.")
    data = await get_faculty_history(
        faculty_name=faculty_name,
        period=period,
        start_date=start_date,
        end_date=end_date,
        section=section,
        year=year,
        years=years,
        department=department,
    )
    return ApiResponse(success=True, data=data)

