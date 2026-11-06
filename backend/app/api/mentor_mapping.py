from typing import List, Optional
from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from app.core.dependencies import enforce_assigned_department, enforce_assigned_year, get_assigned_years, require_roles
from app.api.upload_utils import read_upload_limited
from app.schemas.common import ApiResponse
from app.schemas.mentor_mapping import (
    MentorMappingConfirmRequest,
    MentorMappingPreviewResponse,
    MentorMappingResponse,
)
from app.schemas.user import UserRole
from app.services.mentor_mapping_service import (
    commit_mentor_mappings,
    delete_mentor_mapping,
    generate_mentor_mapping_excel_template,
    get_mentor_mappings,
    preview_mentor_mapping_file,
)

router = APIRouter(prefix="/admin/mentor-student-mapping", tags=["Admin Mentor Student Mapping"])


@router.get("/template")
async def download_mentor_mapping_template_api(
    current_user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.SUPER_ADMIN])),
):
    """Download clean Excel template (.xlsx) for Mentor-to-Student mapping."""
    content = generate_mentor_mapping_excel_template()
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": "attachment; filename=Mentor_Student_Mapping_Template.xlsx"
        },
    )


@router.post("/preview", response_model=ApiResponse[MentorMappingPreviewResponse])
async def preview_mentor_mapping_api(
    file: UploadFile = File(...),
    current_user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.SUPER_ADMIN])),
):
    """Parse uploaded Excel file and return structured validation preview before DB commit."""
    if not ((file.filename or "").lower().endswith(".xlsx") or (file.filename or "").lower().endswith(".xls")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file format. Please upload an Excel file (.xlsx or .xls).",
        )

    content = await read_upload_limited(file)
    preview = await preview_mentor_mapping_file(content, file.filename, current_user)
    return ApiResponse(
        success=True,
        data=preview,
        message=f"Parsed {preview.total_rows} row(s): {preview.valid_rows_count} valid, {preview.invalid_rows_count} invalid.",
    )


@router.post("/import", response_model=ApiResponse[dict])
async def commit_mentor_mapping_api(
    data: MentorMappingConfirmRequest,
    current_user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.SUPER_ADMIN])),
):
    """Commit verified mentor-to-student mappings into MongoDB."""
    result = await commit_mentor_mappings(data, current_user)
    return ApiResponse(
        success=True,
        data=result,
        message=result.get("message", "Mentor-to-student mappings applied successfully."),
    )


@router.get("", response_model=ApiResponse[List[MentorMappingResponse]])
async def list_mentor_mappings_api(
    year: Optional[str] = None,
    section: Optional[str] = None,
    mentor_id: Optional[str] = None,
    current_user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.SUPER_ADMIN])),
):
    """List all current mentor-student mappings."""
    years = None
    department = None
    if current_user.get("role") == UserRole.ADMIN.value:
        if year:
            enforce_assigned_year(current_user, year)
        years = get_assigned_years(current_user) or []
        department = enforce_assigned_department(current_user, None)
        if section and department and department.casefold() not in section.casefold():
            raise HTTPException(status_code=403, detail="Access denied for this department's section.")
    mappings = await get_mentor_mappings(year=year, section=section, mentor_id=mentor_id)
    if years is not None:
        mappings = [m for m in mappings if m.year in years and department and department.casefold() in m.section.casefold()]
    return ApiResponse(success=True, data=mappings)


@router.delete("/{mapping_id}", response_model=ApiResponse[dict])
async def delete_mentor_mapping_api(
    mapping_id: str,
    current_user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.SUPER_ADMIN])),
):
    """Remove a mentor mapping and unlink assigned students."""
    if current_user.get("role") == UserRole.ADMIN.value:
        from bson import ObjectId
        from app.db.mongodb import get_database
        if not ObjectId.is_valid(mapping_id):
            raise HTTPException(status_code=400, detail="Invalid mapping ID.")
        mapping = await get_database().mentor_student_mappings.find_one({"_id": ObjectId(mapping_id)})
        if not mapping:
            raise HTTPException(status_code=404, detail="Mapping not found.")
        enforce_assigned_year(current_user, mapping.get("year"))
        department = enforce_assigned_department(current_user, None)
        if department and department.casefold() not in str(mapping.get("section", "")).casefold():
            raise HTTPException(status_code=403, detail="Access denied for this mapping.")
    result = await delete_mentor_mapping(mapping_id, current_user)
    return ApiResponse(
        success=True,
        data=result,
        message="Mentor mapping removed successfully.",
    )
