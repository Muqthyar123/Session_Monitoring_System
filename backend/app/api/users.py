from typing import List, Optional
from fastapi import APIRouter, Depends, Query, UploadFile, File, Response, status, HTTPException
from app.core.dependencies import enforce_assigned_department, enforce_assigned_year, get_assigned_years, get_current_user, is_legacy_unscoped_admin, require_roles
from app.api.upload_utils import read_upload_limited
from app.schemas.common import ApiResponse
from app.schemas.user import UserCreate, UserResponse, UserRole, UserUpdate
from app.services.excel_service import (
    generate_crlr_excel_template,
    parse_and_import_crlr_excel,
)
from app.services.user_service import (
    create_user,
    delete_all_crlrs,
    delete_user,
    get_user_by_id,
    get_users,
    update_user,
)

router = APIRouter(prefix="/admin/users", tags=["Admin User Management"])


@router.get("", response_model=ApiResponse[List[UserResponse]])
async def list_users_api(
    role: Optional[UserRole] = Query(None),
    crlr_only: bool = Query(False),
    section: Optional[str] = Query(None),
    year: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(10000, ge=1, le=10000),
    admin: dict = Depends(require_roles([UserRole.ADMIN, UserRole.SUPER_ADMIN])),
):
    years = None
    branch = None
    if admin.get("role") == UserRole.ADMIN.value:
        if year:
            enforce_assigned_year(admin, year)
        branch = enforce_assigned_department(admin, None)
        years = get_assigned_years(admin)
        if section and branch and branch.casefold() not in section.casefold():
            raise HTTPException(status_code=403, detail="Access denied for this department's section.")
    users = await get_users(role=role, crlr_only=crlr_only, section=section, year=year,
                            years=years if not year else None, branch=branch,
                            search=search, skip=skip, limit=limit)
    return ApiResponse(success=True, data=users)


@router.post("", response_model=ApiResponse[UserResponse], status_code=status.HTTP_201_CREATED)
async def create_user_api(
    data: UserCreate,
    admin: dict = Depends(require_roles([UserRole.ADMIN, UserRole.SUPER_ADMIN])),
):
    if admin.get("role") == UserRole.ADMIN.value:
        if is_legacy_unscoped_admin(admin):
            new_user = await create_user(data, actor_id=admin["id"])
            return ApiResponse(success=True, data=new_user, message="User created successfully.")
        if data.role not in [UserRole.CR, UserRole.LR]:
            raise HTTPException(status_code=403, detail="HOD accounts may create only CR/LR accounts.")
        department = enforce_assigned_department(admin, None)
        enforce_assigned_year(admin, data.year)
        if not data.section or (department and department.casefold() not in data.section.casefold()):
            raise HTTPException(status_code=403, detail="CR/LR section must belong to your department.")
        data.department = department
        data.department_code = department
        data.branch = admin.get("branch") or department
        data.branch_code = admin.get("branch_code") or admin.get("branch") or department
        data.branch_id = admin.get("branch_id")
        data.department_id = admin.get("department_id")
    new_user = await create_user(data, actor_id=admin["id"])
    return ApiResponse(success=True, data=new_user, message="User created successfully.")


@router.get("/template")
async def download_crlr_template_api(
    admin: dict = Depends(require_roles([UserRole.ADMIN, UserRole.SUPER_ADMIN])),
):
    excel_bytes = generate_crlr_excel_template()
    return Response(
        content=excel_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=CR_LR_Import_Template.xlsx"},
    )


@router.post("/import", response_model=ApiResponse[dict])
async def import_crlr_excel_api(
    file: UploadFile = File(...),
    admin: dict = Depends(get_current_user),
):
    if admin.get("role") != UserRole.SUPER_ADMIN.value and not is_legacy_unscoped_admin(admin):
        raise HTTPException(status_code=403, detail="Only Super Admin can import a global CR/LR roster.")
    try:
        file_bytes = await read_upload_limited(file)
        summary = await parse_and_import_crlr_excel(
            file_bytes, filename=file.filename, actor_id=admin["id"]
        )
        return ApiResponse(
            success=True,
            data=summary,
            message=f"Import complete: {summary['created']} created, {summary['updated']} updated, {summary['failed']} failed.",
        )
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to process CR/LR file due to a server error.") from None


@router.get("/{user_id}", response_model=ApiResponse[UserResponse])
async def get_user_api(
    user_id: str,
    admin: dict = Depends(require_roles([UserRole.ADMIN, UserRole.SUPER_ADMIN])),
):
    user = await get_user_by_id(user_id)
    if admin.get("role") == UserRole.ADMIN.value:
        if user.role not in [UserRole.CR, UserRole.LR]:
            raise HTTPException(status_code=404, detail="CR/LR account not found.")
        enforce_assigned_department(admin, user.department or user.branch)
        enforce_assigned_year(admin, user.year)
    return ApiResponse(success=True, data=user)


@router.patch("/{user_id}", response_model=ApiResponse[UserResponse])
async def update_user_api(
    user_id: str,
    data: UserUpdate,
    admin: dict = Depends(require_roles([UserRole.ADMIN, UserRole.SUPER_ADMIN])),
):
    if admin.get("role") == UserRole.ADMIN.value:
        existing = await get_user_by_id(user_id)
        if existing.role not in [UserRole.CR, UserRole.LR]:
            raise HTTPException(status_code=404, detail="CR/LR account not found.")
        enforce_assigned_department(admin, existing.department or existing.branch)
        enforce_assigned_year(admin, existing.year)
        if data.role is not None and data.role not in [UserRole.CR, UserRole.LR]:
            raise HTTPException(status_code=403, detail="HOD accounts may assign only CR/LR roles.")
        if data.year is not None:
            enforce_assigned_year(admin, data.year)
        data.department = enforce_assigned_department(admin, None)
        data.department_code = data.department
        data.branch = admin.get("branch") or data.department
        data.branch_code = admin.get("branch_code") or admin.get("branch") or data.department
        data.branch_id = admin.get("branch_id")
        data.department_id = admin.get("department_id")
    updated = await update_user(user_id, data, actor_id=admin["id"])
    return ApiResponse(success=True, data=updated, message="User updated successfully.")


@router.delete("/reset", response_model=ApiResponse[dict])
async def reset_crlrs_api(
    admin: dict = Depends(require_roles([UserRole.SUPER_ADMIN])),
):
    deleted_count = await delete_all_crlrs(actor_id=admin["id"])
    return ApiResponse(
        success=True,
        data={"deleted_count": deleted_count},
        message=f"Successfully reset CR/LR directory ({deleted_count} representatives deleted).",
    )


@router.delete("/{user_id}", response_model=ApiResponse[dict])
async def delete_user_api(
    user_id: str,
    admin: dict = Depends(require_roles([UserRole.ADMIN, UserRole.SUPER_ADMIN])),
):
    if admin.get("role") == UserRole.ADMIN.value:
        existing = await get_user_by_id(user_id)
        if existing.role not in [UserRole.CR, UserRole.LR]:
            raise HTTPException(status_code=404, detail="CR/LR account not found.")
        enforce_assigned_department(admin, existing.department or existing.branch)
        enforce_assigned_year(admin, existing.year)
    await delete_user(user_id, actor_id=admin["id"])
    return ApiResponse(success=True, message="User deleted successfully.")
