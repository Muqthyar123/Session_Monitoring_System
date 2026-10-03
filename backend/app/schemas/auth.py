from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.user import UserRole, UserResponse


class LoginRequest(BaseModel):
    email: str  # Can be email, mentor ID, or roll number
    password: str
    portal: Optional[str] = None  # "ADMIN", "CRLR", or "MENTOR"


class AuthUserInfo(BaseModel):
    id: str
    name: str
    email: Optional[str] = None
    role: UserRole
    mentor_id: Optional[str] = Field(None, alias="mentorId")
    phone: Optional[str] = None
    department: Optional[str] = None
    designation: Optional[str] = None
    section: Optional[str] = None
    year: Optional[str] = None
    roll_number: Optional[str] = Field(None, alias="rollNumber")

    model_config = ConfigDict(populate_by_name=True)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: AuthUserInfo


class PasswordChangeRequest(BaseModel):
    old_password: str
    new_password: str
