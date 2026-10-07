from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from app.core.dependencies import require_roles
from app.schemas.common import ApiResponse
from app.schemas.planned_absence import (
    PlannedAbsenceCancelRequest,
    PlannedAbsenceCreateRequest,
    PlannedAbsenceResponse,
    PlannedAbsenceUpdateRequest,
)
from app.schemas.user import UserRole
from app.services.planned_absence_service import (
    cancel_planned_absence,
    create_planned_absence,
    get_planned_absences,
    update_planned_absence,
)

router = APIRouter(tags=["Planned Absence Management"])


@router.post(
    "/mentor/planned-absences",
    response_model=ApiResponse[PlannedAbsenceResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_planned_absence_api(
    data: PlannedAbsenceCreateRequest,
    current_user: dict = Depends(require_roles([UserRole.MENTOR, UserRole.ADMIN])),
):
    """Record a planned absence period for a student."""
    record = await create_planned_absence(data, current_user)
    return ApiResponse(
        success=True,
        data=record,
        message="Planned absence recorded successfully.",
    )


@router.get(
    "/mentor/planned-absences",
    response_model=ApiResponse[List[PlannedAbsenceResponse]],
)
async def get_mentor_planned_absences_api(
    student_id: Optional[str] = Query(None),
    roll_number: Optional[str] = Query(None),
    year: Optional[str] = Query(None),
    section: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    active_only: bool = Query(False, alias="activeOnly"),
    current_user: dict = Depends(require_roles([UserRole.MENTOR, UserRole.ADMIN])),
):
    """Retrieve planned absences scoped by mentor assignment."""
    records = await get_planned_absences(
        current_user=current_user,
        student_id=student_id,
        roll_number=roll_number,
        year=year,
        section=section,
        status_filter=status_filter,
        active_only=active_only,
    )
    return ApiResponse(success=True, data=records)


@router.patch(
    "/mentor/planned-absences/{absence_id}",
    response_model=ApiResponse[PlannedAbsenceResponse],
)
async def update_planned_absence_api(
    absence_id: str,
    data: PlannedAbsenceUpdateRequest,
    current_user: dict = Depends(require_roles([UserRole.MENTOR, UserRole.ADMIN])),
):
    """Update dates or reason for an active planned absence."""
    record = await update_planned_absence(absence_id, data, current_user)
    return ApiResponse(
        success=True,
        data=record,
        message="Planned absence updated successfully.",
    )


@router.post(
    "/mentor/planned-absences/{absence_id}/cancel",
    response_model=ApiResponse[PlannedAbsenceResponse],
)
async def cancel_planned_absence_api(
    absence_id: str,
    data: PlannedAbsenceCancelRequest,
    current_user: dict = Depends(require_roles([UserRole.MENTOR, UserRole.ADMIN])),
):
    """Cancel a planned absence record."""
    record = await cancel_planned_absence(absence_id, data, current_user)
    return ApiResponse(
        success=True,
        data=record,
        message="Planned absence cancelled successfully.",
    )


@router.get(
    "/admin/planned-absences",
    response_model=ApiResponse[List[PlannedAbsenceResponse]],
)
async def get_admin_planned_absences_api(
    student_id: Optional[str] = Query(None),
    roll_number: Optional[str] = Query(None),
    year: Optional[str] = Query(None),
    section: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    active_only: bool = Query(False, alias="activeOnly"),
    current_user: dict = Depends(require_roles([UserRole.ADMIN])),
):
    """Admin endpoint to retrieve all planned absences across all mentors and students."""
    records = await get_planned_absences(
        current_user=current_user,
        student_id=student_id,
        roll_number=roll_number,
        year=year,
        section=section,
        status_filter=status_filter,
        active_only=active_only,
    )
    return ApiResponse(success=True, data=records)
