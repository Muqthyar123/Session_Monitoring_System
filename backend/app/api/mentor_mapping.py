from typing import List, Optional
from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from app.core.dependencies import require_roles
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
    current_user: dict = Depends(require_roles([UserRole.ADMIN])),
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
    current_user: dict = Depends(require_roles([UserRole.ADMIN])),
):
    """Parse uploaded Excel file and return structured validation preview before DB commit."""
    if not (file.filename.endswith(".xlsx") or file.filename.endswith(".xls")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file format. Please upload an Excel file (.xlsx or .xls).",
        )

    content = await file.read()
    # Archive file to disk
    try:
        from pathlib import Path
        from app.core.config import settings
        upload_dir = Path(settings.UPLOAD_DIR)
        upload_dir.mkdir(parents=True, exist_ok=True)
        archive_path = upload_dir / (file.filename or "mentor_mappings.xlsx")
        with open(archive_path, "wb") as f_out:
            f_out.write(content)
    except Exception:
        pass

    preview = await preview_mentor_mapping_file(content, file.filename)
    return ApiResponse(
        success=True,
        data=preview,
        message=f"Parsed {preview.total_rows} row(s): {preview.valid_rows_count} valid, {preview.invalid_rows_count} invalid.",
    )


@router.post("/import", response_model=ApiResponse[dict])
async def commit_mentor_mapping_api(
    data: MentorMappingConfirmRequest,
    current_user: dict = Depends(require_roles([UserRole.ADMIN])),
):
    """Commit verified mentor-to-student mappings into MongoDB."""
    from app.db.mongodb import save_mock_db_to_disk_sync
    result = await commit_mentor_mappings(data, current_user)
    save_mock_db_to_disk_sync()
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
    current_user: dict = Depends(require_roles([UserRole.ADMIN])),
):
    """List all current mentor-student mappings."""
    mappings = await get_mentor_mappings(year=year, section=section, mentor_id=mentor_id)
    return ApiResponse(success=True, data=mappings)


@router.delete("/{mapping_id}", response_model=ApiResponse[dict])
async def delete_mentor_mapping_api(
    mapping_id: str,
    current_user: dict = Depends(require_roles([UserRole.ADMIN])),
):
    """Remove a mentor mapping and unlink assigned students."""
    result = await delete_mentor_mapping(mapping_id, current_user)
    return ApiResponse(
        success=True,
        data=result,
        message="Mentor mapping removed successfully.",
    )
