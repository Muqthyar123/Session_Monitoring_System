import asyncio
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Response, status
from app.core.dependencies import require_roles
from app.schemas.common import ApiResponse
from app.schemas.student import StudentCreate, StudentResponse, StudentUpdate
from app.schemas.user import UserRole
from app.services.excel_service import (
    generate_student_excel_template,
    parse_and_import_student_excel,
)
from app.services.student_service import (
    create_student,
    delete_all_students,
    delete_student,
    get_students,
    get_students_page,
    update_student,
)

router = APIRouter(prefix="/admin/students", tags=["Admin Student Management"])


@router.get("", response_model=ApiResponse[Any])
async def list_students_api(
    year: Optional[str] = Query(None),
    section: Optional[str] = Query(None),
    branch: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: Optional[int] = Query(None, ge=1),
    page_size: Optional[int] = Query(None, ge=1, le=200),
    current_user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.DEPARTMENT_COORDINATOR, UserRole.COORDINATOR])),
):
    user_role = current_user.get("role")
    if user_role in [UserRole.DEPARTMENT_COORDINATOR.value, UserRole.COORDINATOR.value]:
        user_dept = current_user.get("department") or current_user.get("branch")
        if user_dept:
            branch = user_dept

    if page is not None or page_size is not None:
        data = await get_students_page(
            year=year, section=section, search=search, branch=branch,
            page=page or 1, page_size=page_size or 25,
        )
        return ApiResponse(success=True, data=data)
    students = await get_students(year=year, section=section, search=search, branch=branch)
    return ApiResponse(success=True, data=students)


@router.get("/filters", response_model=ApiResponse[Dict[str, List[str]]])
async def get_student_filter_options_api(
    admin: dict = Depends(require_roles([UserRole.ADMIN, UserRole.DEPARTMENT_COORDINATOR, UserRole.COORDINATOR])),
):
    from app.db.mongodb import get_database

    db = get_database()
    years, branches, student_sections, timetable_sections = await asyncio.gather(
        db.students.distinct("year"),
        db.students.distinct("branch"),
        db.students.distinct("section"),
        db.timetables.distinct("section"),
    )
    sections = timetable_sections or student_sections
    return ApiResponse(success=True, data={
        "years": sorted(str(value) for value in years if value),
        "branches": sorted(str(value).upper() for value in branches if value),
        "sections": sorted(str(value) for value in sections if value),
    })


@router.post("", response_model=ApiResponse[StudentResponse], status_code=status.HTTP_201_CREATED)
async def create_student_api(
    data: StudentCreate,
    admin: dict = Depends(require_roles([UserRole.ADMIN])),
):
    new_student = await create_student(data, actor_id=admin["id"])
    return ApiResponse(success=True, data=new_student, message="Student created successfully.")


@router.get("/template")
async def download_student_template_api(
    admin: dict = Depends(require_roles([UserRole.ADMIN])),
):
    excel_bytes = generate_student_excel_template()
    return Response(
        content=excel_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=Student_Import_Template.xlsx"},
    )


@router.post("/import", response_model=ApiResponse[dict])
async def import_student_excel_api(
    file: UploadFile = File(...),
    admin: dict = Depends(require_roles([UserRole.ADMIN])),
):
    fn_lower = (file.filename or "").lower()
    if not (fn_lower.endswith(".xlsx") or fn_lower.endswith(".xls") or fn_lower.endswith(".csv")):
        raise HTTPException(
            status_code=400,
            detail="Invalid file format. Only .xlsx, .xls, or .csv files are accepted for Students upload.",
        )

    file_bytes = await file.read()
    # Archive file to disk
    try:
        from pathlib import Path
        from app.core.config import settings
        from app.db.mongodb import save_mock_db_to_disk_sync
        upload_dir = Path(settings.UPLOAD_DIR)
        upload_dir.mkdir(parents=True, exist_ok=True)
        archive_path = upload_dir / (file.filename or "students.csv")
        with open(archive_path, "wb") as f_out:
            f_out.write(file_bytes)
    except Exception:
        pass

    try:
        summary = await parse_and_import_student_excel(
            file_bytes, filename=file.filename, actor_id=admin["id"]
        )
        save_mock_db_to_disk_sync()
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))
    except Exception as err:
        raise HTTPException(status_code=400, detail=f"Failed to process Student file: {str(err)}")

    if summary.get("failed", 0) > 0 and summary.get("created", 0) == 0 and summary.get("updated", 0) == 0:
        first_err = summary["errors"][0]["errors"][0] if summary.get("errors") else "Invalid student file contents."
        raise HTTPException(status_code=400, detail=f"Student import failed: {first_err}")

    return ApiResponse(
        success=True,
        data=summary,
        message=f"Import complete: {summary['created']} created, {summary['updated']} updated, {summary['failed']} failed.",
    )



@router.patch("/{student_id}", response_model=ApiResponse[StudentResponse])
async def update_student_api(
    student_id: str,
    data: StudentUpdate,
    admin: dict = Depends(require_roles([UserRole.ADMIN])),
):
    updated = await update_student(student_id, data, actor_id=admin["id"])
    return ApiResponse(success=True, data=updated, message="Student updated successfully.")


@router.delete("/reset", response_model=ApiResponse[dict])
async def reset_students_api(
    admin: dict = Depends(require_roles([UserRole.ADMIN])),
):
    deleted_count = await delete_all_students(actor_id=admin["id"])
    return ApiResponse(
        success=True,
        data={"deleted_count": deleted_count},
        message=f"Successfully reset student roster ({deleted_count} students deleted).",
    )


@router.delete("/{student_id}", response_model=ApiResponse[dict])
async def delete_student_api(
    student_id: str,
    admin: dict = Depends(require_roles([UserRole.ADMIN])),
):
    await delete_student(student_id, actor_id=admin["id"])
    return ApiResponse(success=True, message="Student deleted successfully.")


