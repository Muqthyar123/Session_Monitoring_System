from typing import Optional
from pydantic import BaseModel, EmailStr
from app.schemas.user import UserRole, UserResponse


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    portal: Optional[str] = None  # Optional portal check e.g. "ADMIN" or "CRLR"


class AuthUserInfo(BaseModel):
    id: str
    name: str
    email: str
    role: UserRole
    section: Optional[str] = None
    year: Optional[str] = None
    roll_number: Optional[str] = None


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: AuthUserInfo


class PasswordChangeRequest(BaseModel):
    old_password: str
    new_password: str
