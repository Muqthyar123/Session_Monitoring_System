from typing import List, Optional
from bson import ObjectId
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from app.core.security import decode_access_token
from app.db.mongodb import get_database
from app.schemas.user import UserRole

security_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
):
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token missing or invalid.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if not user_id or not ObjectId.is_valid(user_id):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload.",
        )

    db = get_database()
    user = await db.users.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User associated with token not found.",
        )

    if not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled.",
        )

    # Attach string id for easy access
    user["id"] = str(user["_id"])
    return user


def require_roles(allowed_roles: List[UserRole]):
    async def role_checker(current_user: dict = Depends(get_current_user)):
        user_role = current_user.get("role")
        if user_role not in [r.value for r in allowed_roles]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access forbidden: requires one of roles {[r.value for r in allowed_roles]}",
            )
        return current_user

    return role_checker


def get_branch_filter(current_user: dict, requested_branch: Optional[str] = None) -> Optional[str]:
    """
    Returns the branch code to filter by:
    - If user is SUPER_ADMIN: returns requested_branch (can access all branches).
    - If user is ADMIN with an assigned branch: strictly forces their assigned branch.
      If requested_branch is provided and differs from their assigned branch, raises HTTP 403 Forbidden.
    - If user is DEPARTMENT_COORDINATOR or COORDINATOR: strictly forces their assigned branch.
    - If user is ADMIN without an assigned branch: returns requested_branch.
    """
    user_role = current_user.get("role")
    if user_role == UserRole.SUPER_ADMIN.value:
        return requested_branch.strip().upper() if requested_branch and requested_branch.upper() != "ALL" else None

    assigned_branch = current_user.get("branch") or current_user.get("department")
    if user_role in [UserRole.DEPARTMENT_COORDINATOR.value, UserRole.COORDINATOR.value]:
        if not assigned_branch:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Department Coordinator has no assigned branch.",
            )
        return assigned_branch.strip().upper()

    if user_role == UserRole.ADMIN.value and assigned_branch:
        assigned_branch_upper = assigned_branch.strip().upper()
        if requested_branch and requested_branch.upper() != "ALL":
            if requested_branch.strip().upper() != assigned_branch_upper:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Access denied: You are restricted to your assigned branch ({assigned_branch_upper}).",
                )
        return assigned_branch_upper

    return requested_branch.strip().upper() if requested_branch and requested_branch.upper() != "ALL" else None


def get_department_filter(current_user: dict, requested_dept: Optional[str] = None) -> Optional[str]:
    """
    Backward-compatible department filter alias using get_branch_filter.
    """
    return get_branch_filter(current_user, requested_dept)

