from typing import List, Optional
from fastapi import APIRouter, Depends, Query, UploadFile, File, Response, status
from app.core.dependencies import require_roles
from app.schemas.common import ApiResponse
from app.schemas.user import UserCreate, UserResponse, UserRole, UserUpdate
from app.services.excel_service import (
    generate_crlr_excel_template,
    parse_and_import_crlr_excel,
)
from app.services.user_service import (
    create_user,
    delete_user,
    get_user_by_id,
    get_users,
    update_user,
)

router = APIRouter(prefix="/admin/users", tags=["Admin User Management"])


@router.get("", response_model=ApiResponse[List[UserResponse]])
async def list_users_api(
    role: Optional[UserRole] = Query(None),
    section: Optional[str] = Query(None),
    year: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    admin: dict = Depends(require_roles([UserRole.ADMIN])),
):
    users = await get_users(role=role, section=section, year=year, search=search, skip=skip, limit=limit)
    return ApiResponse(success=True, data=users)


@router.post("", response_model=ApiResponse[UserResponse], status_code=status.HTTP_201_CREATED)
async def create_user_api(
    data: UserCreate,
    admin: dict = Depends(require_roles([UserRole.ADMIN])),
):
    new_user = await create_user(data, actor_id=admin["id"])
    return ApiResponse(success=True, data=new_user, message="User created successfully.")


@router.get("/template")
async def download_crlr_template_api(
    admin: dict = Depends(require_roles([UserRole.ADMIN])),
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
    admin: dict = Depends(require_roles([UserRole.ADMIN])),
):
    file_bytes = await file.read()
    summary = await parse_and_import_crlr_excel(
        file_bytes, filename=file.filename, actor_id=admin["id"]
    )
    return ApiResponse(
        success=True,
        data=summary,
        message=f"Import complete: {summary['created']} created, {summary['updated']} updated, {summary['failed']} failed.",
    )


@router.get("/{user_id}", response_model=ApiResponse[UserResponse])
async def get_user_api(
    user_id: str,
    admin: dict = Depends(require_roles([UserRole.ADMIN])),
):
    user = await get_user_by_id(user_id)
    return ApiResponse(success=True, data=user)


@router.patch("/{user_id}", response_model=ApiResponse[UserResponse])
async def update_user_api(
    user_id: str,
    data: UserUpdate,
    admin: dict = Depends(require_roles([UserRole.ADMIN])),
):
    updated = await update_user(user_id, data, actor_id=admin["id"])
    return ApiResponse(success=True, data=updated, message="User updated successfully.")


@router.delete("/{user_id}", response_model=ApiResponse[dict])
async def delete_user_api(
    user_id: str,
    admin: dict = Depends(require_roles([UserRole.ADMIN])),
):
    await delete_user(user_id, actor_id=admin["id"])
    return ApiResponse(success=True, message="User deleted successfully.")
