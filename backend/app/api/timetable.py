from typing import List, Optional
from fastapi import APIRouter, Depends, Query, UploadFile, File, Response, status
from app.core.dependencies import get_current_user, require_roles
from app.schemas.common import ApiResponse
from app.schemas.timetable import TimetablePeriodResponse
from app.schemas.user import UserRole
from app.services.excel_service import (
    generate_timetable_excel_template,
    parse_and_import_timetable_excel,
)
from app.services.timetable_service import (
    delete_all_timetables,
    delete_timetable_by_section,
    get_all_timetables,
    get_timetable_by_section,
)

router = APIRouter(prefix="/admin/timetable", tags=["Timetable Management"])


@router.post("/upload", response_model=ApiResponse[dict])
async def upload_timetable_api(
    file: UploadFile = File(...),
    admin: dict = Depends(require_roles([UserRole.ADMIN])),
):
    fn_lower = (file.filename or "").lower()
    if not (fn_lower.endswith(".xlsx") or fn_lower.endswith(".xls")):
        raise HTTPException(
            status_code=400,
            detail="Invalid file format. Only .xlsx or .xls Excel workbooks are accepted for Timetable upload.",
        )

    file_bytes = await file.read()
    try:
        summary = await parse_and_import_timetable_excel(
            file_bytes, filename=file.filename, actor_id=admin["id"]
        )
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))
    except Exception as err:
        raise HTTPException(status_code=400, detail=f"Failed to process Timetable file: {str(err)}")

    if summary.get("inserted", 0) == 0 and summary.get("failed", 0) > 0:
        first_err = summary["errors"][0]["errors"][0] if summary.get("errors") else "Invalid timetable matrix or table format."
        raise HTTPException(status_code=400, detail=f"Timetable upload failed: {first_err}")

    return ApiResponse(
        success=True,
        data=summary,
        message=f"Timetable upload processed: {summary['inserted']} periods inserted/updated.",
    )



@router.get("/template")
async def download_timetable_template_api(
    admin: dict = Depends(require_roles([UserRole.ADMIN])),
):
    excel_bytes = generate_timetable_excel_template()
    return Response(
        content=excel_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=Timetable_Template.xlsx"},
    )


@router.get("", response_model=ApiResponse[List[TimetablePeriodResponse]])
async def get_all_timetables_api(
    admin: dict = Depends(require_roles([UserRole.ADMIN])),
):
    data = await get_all_timetables()
    return ApiResponse(success=True, data=data)


@router.get("/{section}", response_model=ApiResponse[List[TimetablePeriodResponse]])
async def get_section_timetable_api(
    section: str,
    year: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user),
):
    data = await get_timetable_by_section(section, year=year)
    return ApiResponse(success=True, data=data)


@router.delete("", response_model=ApiResponse[dict])
async def delete_all_timetables_api(
    admin: dict = Depends(require_roles([UserRole.ADMIN])),
):
    count = await delete_all_timetables()
    return ApiResponse(
        success=True, message=f"Cleared all {count} timetable records."
    )


@router.post("/reset", response_model=ApiResponse[dict])
async def reset_all_timetables_api(
    admin: dict = Depends(require_roles([UserRole.ADMIN])),
):
    count = await delete_all_timetables()
    return ApiResponse(
        success=True, message=f"Reset successful: Deleted all {count} timetable records from database."
    )


@router.delete("/{section}", response_model=ApiResponse[dict])
async def delete_section_timetable_api(
    section: str,
    admin: dict = Depends(require_roles([UserRole.ADMIN])),
):
    count = await delete_timetable_by_section(section)
    return ApiResponse(
        success=True, message=f"Deleted {count} timetable records for section '{section}'."
    )
