import asyncio
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Response, status
from app.core.dependencies import enforce_assigned_branch, enforce_assigned_department, enforce_assigned_year, get_assigned_department, get_assigned_years, get_current_user, is_legacy_unscoped_admin, require_roles
from app.api.upload_utils import read_upload_limited
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
    current_user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.DEPARTMENT_COORDINATOR, UserRole.COORDINATOR])),
):
    user_role = current_user.get("role")
    branch = enforce_assigned_branch(current_user, branch)
    year = enforce_assigned_year(current_user, year)
    years = get_assigned_years(current_user)
    if user_role in (UserRole.ADMIN.value, UserRole.MENTOR.value):
        branch = enforce_assigned_department(current_user, None)

    if page is not None or page_size is not None:
        data = await get_students_page(
            year=year, section=section, search=search, branch=branch,
            page=page or 1, page_size=page_size or 25, years=years if not year else None,
        )
        return ApiResponse(success=True, data=data)
    students = await get_students(year=year, section=section, search=search, branch=branch, years=years if not year else None)
    return ApiResponse(success=True, data=students)


@router.get("/filters", response_model=ApiResponse[Dict[str, List[str]]])
async def get_student_filter_options_api(
    admin: dict = Depends(require_roles([UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.DEPARTMENT_COORDINATOR, UserRole.COORDINATOR])),
):
    from app.db.mongodb import get_database

    db = get_database()
    enforce_assigned_branch(admin, None)
    assigned_branch = get_assigned_department(admin) if admin.get("role") == UserRole.ADMIN.value else enforce_assigned_branch(admin, None)
    assigned_years = get_assigned_years(admin)
    filters = {}
    if assigned_branch:
        filters["$or"] = [{"branch": assigned_branch}, {"department": assigned_branch}]
    if assigned_years is not None:
        filters["year"] = {"$in": assigned_years}
    years, branches, student_sections, timetable_sections = await asyncio.gather(
        db.students.distinct("year", filters),
        db.students.distinct("branch", filters),
        db.students.distinct("section", filters),
        db.timetables.distinct("section", filters),
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
    admin: dict = Depends(require_roles([UserRole.ADMIN, UserRole.SUPER_ADMIN])),
):
    admin_branch = admin.get("branch") or admin.get("department")
    if admin.get("role") == UserRole.ADMIN.value and admin_branch:
        data.branch = get_assigned_department(admin) or admin_branch
    enforce_assigned_branch(admin, data.branch)
    enforce_assigned_year(admin, data.year)
    new_student = await create_student(data, actor_id=admin["id"])
    return ApiResponse(success=True, data=new_student, message="Student created successfully.")


@router.get("/template")
async def download_student_template_api(
    admin: dict = Depends(require_roles([UserRole.ADMIN, UserRole.SUPER_ADMIN])),
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
    admin: dict = Depends(get_current_user),
):
    if admin.get("role") != UserRole.SUPER_ADMIN.value and not is_legacy_unscoped_admin(admin):
        raise HTTPException(status_code=403, detail="Only Super Admin can import a global student roster.")
    fn_lower = (file.filename or "").lower()
    if not (fn_lower.endswith(".xlsx") or fn_lower.endswith(".xls") or fn_lower.endswith(".csv")):
        raise HTTPException(
            status_code=400,
            detail="Invalid file format. Only .xlsx, .xls, or .csv files are accepted for Students upload.",
        )

    file_bytes = await read_upload_limited(file)
    try:
        summary = await parse_and_import_student_excel(
            file_bytes, filename=file.filename, actor_id=admin["id"]
        )
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))
    except Exception as err:
        raise HTTPException(status_code=500, detail="Failed to process Student file due to a server error.") from None

    return ApiResponse(
        success=True,
        data=summary,
        message=f"Import complete: {summary['created']} created, {summary['updated']} updated, {summary['failed']} failed.",
    )



@router.patch("/{student_id}", response_model=ApiResponse[StudentResponse])
async def update_student_api(
    student_id: str,
    data: StudentUpdate,
    admin: dict = Depends(require_roles([UserRole.ADMIN, UserRole.SUPER_ADMIN])),
):
    from bson import ObjectId
    from fastapi import HTTPException
    from app.db.mongodb import get_database
    if admin.get("role") != UserRole.SUPER_ADMIN.value:
        db = get_database()
        query = {"_id": ObjectId(student_id)} if ObjectId.is_valid(student_id) else {"roll_number": student_id.strip().upper()}
        existing = await db.students.find_one(query)
        if not existing:
            raise HTTPException(status_code=404, detail="Student not found.")
        enforce_assigned_branch(admin, admin.get("branch_code") or admin.get("branch"))
        enforce_assigned_department(admin, existing.get("department") or existing.get("branch"))
        enforce_assigned_year(admin, existing.get("year"))
        if data.branch and data.branch.strip().casefold() not in {str(existing.get("branch", "")).casefold(), str(existing.get("department", "")).casefold()}:
            raise HTTPException(status_code=403, detail="You cannot move a student outside your assigned branch.")
        if data.year:
            enforce_assigned_year(admin, data.year)
    updated = await update_student(student_id, data, actor_id=admin["id"])
    return ApiResponse(success=True, data=updated, message="Student updated successfully.")


@router.delete("/reset", response_model=ApiResponse[dict])
async def reset_students_api(
    admin: dict = Depends(require_roles([UserRole.SUPER_ADMIN])),
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
    admin: dict = Depends(require_roles([UserRole.ADMIN, UserRole.SUPER_ADMIN])),
):
    from bson import ObjectId
    from fastapi import HTTPException
    from app.db.mongodb import get_database
    if admin.get("role") != UserRole.SUPER_ADMIN.value:
        db = get_database()
        query = {"_id": ObjectId(student_id)} if ObjectId.is_valid(student_id) else {"roll_number": student_id.strip().upper()}
        existing = await db.students.find_one(query)
        if not existing:
            raise HTTPException(status_code=404, detail="Student not found.")
        enforce_assigned_branch(admin, admin.get("branch_code") or admin.get("branch"))
        enforce_assigned_department(admin, existing.get("department") or existing.get("branch"))
        enforce_assigned_year(admin, existing.get("year"))
    await delete_student(student_id, actor_id=admin["id"])
    return ApiResponse(success=True, message="Student deleted successfully.")


