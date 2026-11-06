from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from app.schemas.user import UserRole, UserResponse


class LoginRequest(BaseModel):
    email: str  # Can be email, mentor ID, or roll number
    password: str
    portal: Optional[str] = None  # "SUPER_ADMIN", "ADMIN", "CRLR", or "MENTOR"


class AuthUserInfo(BaseModel):
    id: str
    name: str
    email: Optional[str] = None
    role: UserRole
    mentor_id: Optional[str] = Field(None, alias="mentorId")
    employee_id: Optional[str] = Field(None, alias="employeeId")
    phone: Optional[str] = None
    department: Optional[str] = None
    department_id: Optional[str] = Field(None, alias="departmentId")
    department_code: Optional[str] = Field(None, alias="departmentCode")
    branch: Optional[str] = None
    branch_id: Optional[str] = Field(None, alias="branchId")
    designation: Optional[str] = None
    section: Optional[str] = None
    year: Optional[str] = None
    academic_years: Optional[list[str]] = Field(default_factory=list, alias="academicYears")
    roll_number: Optional[str] = Field(None, alias="rollNumber")

    model_config = ConfigDict(populate_by_name=True)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: AuthUserInfo


class PasswordChangeRequest(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=8, max_length=12)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetTokenRequest(BaseModel):
    token: str = Field(..., min_length=32, max_length=256)


class ResetPasswordRequest(ResetTokenRequest):
    new_password: str = Field(..., min_length=8, max_length=12)
