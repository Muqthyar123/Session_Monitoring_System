from typing import List, Optional
from fastapi import APIRouter, Depends, Query, UploadFile, File, Response, status, HTTPException
from app.core.dependencies import get_current_user, is_legacy_unscoped_admin, require_roles
from app.core.dependencies import enforce_assigned_branch, enforce_assigned_department, get_assigned_years
from app.api.upload_utils import read_upload_limited
from app.core.security import hash_password
from app.schemas.common import ApiResponse
from app.schemas.user import UserCreate, UserResponse, UserRole, UserUpdate
from app.services.excel_service import (
    generate_mentor_excel_template,
    parse_and_import_mentor_excel,
)
from app.services.user_service import (
    create_user,
    delete_all_mentors,
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
    branch: Optional[str] = Query(None),
    admin: dict = Depends(require_roles([UserRole.ADMIN, UserRole.SUPER_ADMIN])),
):
    admin_branch = admin.get("branch") or admin.get("department")
    effective_branch = (enforce_assigned_department(admin, None) if admin.get("role") == UserRole.ADMIN.value else branch)
    users = await get_users(role=UserRole.MENTOR, branch=effective_branch, search=search, limit=10000,
                            years=get_assigned_years(admin) if admin.get("role") == UserRole.ADMIN.value else None)
    return ApiResponse(success=True, data=users)


@router.post("", response_model=ApiResponse[UserResponse], status_code=status.HTTP_201_CREATED)
async def create_mentor_api(
    data: UserCreate,
    admin: dict = Depends(require_roles([UserRole.ADMIN, UserRole.SUPER_ADMIN])),
):
    db = get_database()
    # Ensure mentor role
    data.role = UserRole.MENTOR

    admin_branch = admin.get("branch") or admin.get("department")
    if admin.get("role") == UserRole.ADMIN.value and admin_branch:
        data.branch = admin_branch
        data.department = enforce_assigned_department(admin, None)
        data.branch_id = admin.get("branch_id")
        data.branch_code = admin.get("branch_code") or admin_branch
        data.department_id = admin.get("department_id")
        data.department_code = data.department
        years = data.academic_years or ([data.year] if data.year else [])
        allowed_years = get_assigned_years(admin) or []
        if not years or set(years) - set(allowed_years):
            raise HTTPException(status_code=403, detail="Mentor academic years must be selected from your assigned years.")
        data.academic_years = years
        data.year = years[0] if len(years) == 1 else None

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
    admin: dict = Depends(require_roles([UserRole.ADMIN, UserRole.SUPER_ADMIN])),
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
    admin: dict = Depends(get_current_user),
):
    if admin.get("role") != UserRole.SUPER_ADMIN.value and not is_legacy_unscoped_admin(admin):
        raise HTTPException(status_code=403, detail="Only Super Admin can import a global mentor roster.")
    fn_lower = (file.filename or "").lower()
    if not (fn_lower.endswith(".xlsx") or fn_lower.endswith(".xls") or fn_lower.endswith(".csv")):
        raise HTTPException(
            status_code=400,
            detail="Invalid file format. Only .xlsx, .xls, or .csv files are accepted for Mentors upload.",
        )

    file_bytes = await read_upload_limited(file)
    try:
        summary = await parse_and_import_mentor_excel(
            file_bytes, filename=file.filename, actor_id=admin["id"]
        )
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))
    except Exception as err:
        raise HTTPException(status_code=500, detail="Failed to process Mentor file due to a server error.") from None

    return ApiResponse(
        success=True,
        data=summary,
        message=f"Import complete: {summary['created']} created, {summary['updated']} updated, {summary['failed']} failed.",
    )



@router.patch("/{mentor_id}", response_model=ApiResponse[UserResponse])
async def update_mentor_api(
    mentor_id: str,
    data: UserUpdate,
    admin: dict = Depends(require_roles([UserRole.ADMIN, UserRole.SUPER_ADMIN])),
):
    data.role = UserRole.MENTOR
    if admin.get("role") == UserRole.ADMIN.value:
        db = get_database()
        query = {"_id": ObjectId(mentor_id)} if ObjectId.is_valid(mentor_id) else {"email": mentor_id}
        existing = await db.users.find_one({"$and": [query, {"role": UserRole.MENTOR.value}]})
        if not existing:
            raise HTTPException(status_code=404, detail="Mentor not found.")
        enforce_assigned_department(admin, existing.get("department") or existing.get("branch"))
        years = data.academic_years if data.academic_years is not None else ([data.year] if data.year else existing.get("academic_years", []))
        if not years or set(years) - set(get_assigned_years(admin) or []):
            raise HTTPException(status_code=403, detail="Mentor academic years must remain within your assigned years.")
        data.academic_years = years
        data.department = enforce_assigned_department(admin, None)
        data.branch = admin.get("branch") or admin.get("branch_code")
        data.department_code = data.department
        data.department_id = admin.get("department_id")
        data.branch_id = admin.get("branch_id")
        data.branch_code = data.branch
    updated = await update_user(mentor_id, data, actor_id=admin["id"])
    return ApiResponse(success=True, data=updated, message="Mentor updated successfully.")


@router.delete("/reset", response_model=ApiResponse[dict])
async def reset_mentors_api(
    admin: dict = Depends(require_roles([UserRole.SUPER_ADMIN])),
):
    deleted_count = await delete_all_mentors(actor_id=admin["id"])
    return ApiResponse(
        success=True,
        data={"deleted_count": deleted_count},
        message=f"Successfully reset mentor directory ({deleted_count} mentors deleted).",
    )


@router.delete("/{mentor_id}", response_model=ApiResponse[dict])
async def delete_mentor_api(
    mentor_id: str,
    admin: dict = Depends(require_roles([UserRole.ADMIN, UserRole.SUPER_ADMIN])),
):
    if admin.get("role") == UserRole.ADMIN.value:
        db = get_database()
        query = {"_id": ObjectId(mentor_id)} if ObjectId.is_valid(mentor_id) else {"mentor_id": mentor_id.strip().upper()}
        existing = await db.users.find_one({"$and": [query, {"role": UserRole.MENTOR.value}]})
        if not existing:
            raise HTTPException(status_code=404, detail="Mentor not found.")
        enforce_assigned_department(admin, existing.get("department") or existing.get("branch"))
        mentor_years = existing.get("academic_years") or ([existing["year"]] if existing.get("year") else [])
        if set(mentor_years) - set(get_assigned_years(admin) or []):
            raise HTTPException(status_code=403, detail="This mentor is assigned to academic years outside your scope.")
    await delete_user(mentor_id, actor_id=admin["id"])
    return ApiResponse(success=True, message="Mentor deleted successfully.")


