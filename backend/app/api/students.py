from typing import List, Optional
from fastapi import APIRouter, Depends, Query, UploadFile, File, Response, status
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
    delete_student,
    get_students,
    update_student,
)

router = APIRouter(prefix="/admin/students", tags=["Admin Student Management"])


@router.get("", response_model=ApiResponse[List[StudentResponse]])
async def list_students_api(
    year: Optional[str] = Query(None),
    section: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    admin: dict = Depends(require_roles([UserRole.ADMIN])),
):
    students = await get_students(year=year, section=section, search=search, limit=500)
    return ApiResponse(success=True, data=students)


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
    file_bytes = await file.read()
    summary = await parse_and_import_student_excel(
        file_bytes, filename=file.filename, actor_id=admin["id"]
    )
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


@router.delete("/{student_id}", response_model=ApiResponse[dict])
async def delete_student_api(
    student_id: str,
    admin: dict = Depends(require_roles([UserRole.ADMIN])),
):
    await delete_student(student_id, actor_id=admin["id"])
    return ApiResponse(success=True, message="Student deleted successfully.")
