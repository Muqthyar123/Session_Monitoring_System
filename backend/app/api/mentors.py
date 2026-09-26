from typing import List, Optional
from fastapi import APIRouter, Depends, Query, UploadFile, File, Response, status, HTTPException
from app.core.dependencies import require_roles
from app.core.security import hash_password
from app.schemas.common import ApiResponse
from app.schemas.user import UserCreate, UserResponse, UserRole, UserUpdate
from app.services.excel_service import (
    generate_mentor_excel_template,
    parse_and_import_mentor_excel,
)
from app.services.user_service import (
    create_user,
    delete_user,
    get_user_by_id,
    get_users,
    update_user,
)
from app.db.mongodb import get_database
from bson import ObjectId

router = APIRouter(prefix="/admin/mentors", tags=["Admin Mentor Management"])


@router.get("", response_model=ApiResponse[List[UserResponse]])
async def list_mentors_api(
    search: Optional[str] = Query(None),
    admin: dict = Depends(require_roles([UserRole.ADMIN])),
):
    users = await get_users(role=UserRole.MENTOR, search=search, limit=500)
    return ApiResponse(success=True, data=users)


@router.post("", response_model=ApiResponse[UserResponse], status_code=status.HTTP_201_CREATED)
async def create_mentor_api(
    data: UserCreate,
    admin: dict = Depends(require_roles([UserRole.ADMIN])),
):
    db = get_database()
    # Ensure mentor role
    data.role = UserRole.MENTOR

    mentor_id = (data.mentor_id or data.roll_number or "").strip().upper()
    if not mentor_id:
        raise HTTPException(status_code=400, detail="Mentor ID is required.")

    existing_mentor = await db.users.find_one({"mentor_id": mentor_id})
    if existing_mentor:
        raise HTTPException(status_code=400, detail=f"Mentor ID '{mentor_id}' already exists.")

    data.mentor_id = mentor_id
    if not data.email:
        data.email = f"{mentor_id.lower()}@fams.edu"

    new_user = await create_user(data, actor_id=admin["id"])
    return ApiResponse(success=True, data=new_user, message="Mentor created successfully.")


@router.get("/template")
async def download_mentor_template_api(
    admin: dict = Depends(require_roles([UserRole.ADMIN])),
):
    excel_bytes = generate_mentor_excel_template()
    return Response(
        content=excel_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=Mentor_Import_Template.xlsx"},
    )


@router.post("/import", response_model=ApiResponse[dict])
async def import_mentor_excel_api(
    file: UploadFile = File(...),
    admin: dict = Depends(require_roles([UserRole.ADMIN])),
):
    file_bytes = await file.read()
    summary = await parse_and_import_mentor_excel(
        file_bytes, filename=file.filename, actor_id=admin["id"]
    )
    return ApiResponse(
        success=True,
        data=summary,
        message=f"Import complete: {summary['created']} created, {summary['updated']} updated, {summary['failed']} failed.",
    )


@router.patch("/{mentor_id}", response_model=ApiResponse[UserResponse])
async def update_mentor_api(
    mentor_id: str,
    data: UserUpdate,
    admin: dict = Depends(require_roles([UserRole.ADMIN])),
):
    updated = await update_user(mentor_id, data, actor_id=admin["id"])
    return ApiResponse(success=True, data=updated, message="Mentor updated successfully.")


@router.delete("/{mentor_id}", response_model=ApiResponse[dict])
async def delete_mentor_api(
    mentor_id: str,
    admin: dict = Depends(require_roles([UserRole.ADMIN])),
):
    await delete_user(mentor_id, actor_id=admin["id"])
    return ApiResponse(success=True, message="Mentor deleted successfully.")
