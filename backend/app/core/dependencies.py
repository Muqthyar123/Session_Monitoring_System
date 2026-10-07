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


def get_department_filter(current_user: dict, requested_dept: Optional[str] = None) -> Optional[str]:
    """
    Returns the department code to filter by:
    - If user is DEPARTMENT_COORDINATOR, strictly forces their assigned department.
    - If user is ADMIN, returns requested_dept if specified.
    """
    user_role = current_user.get("role")
    if user_role in [UserRole.DEPARTMENT_COORDINATOR.value, UserRole.COORDINATOR.value]:
        assigned_dept = current_user.get("department") or current_user.get("branch")
        if not assigned_dept:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Department Coordinator has no assigned department.",
            )
        return assigned_dept.strip().upper()
    return requested_dept.strip().upper() if requested_dept and requested_dept.upper() != "ALL" else None

