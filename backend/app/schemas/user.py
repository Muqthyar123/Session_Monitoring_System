from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field, computed_field


class UserRole(str, Enum):
    ADMIN = "ADMIN"
    CR = "CR"
    LR = "LR"
    MENTOR = "MENTOR"


class UserBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    role: UserRole
    roll_number: Optional[str] = Field(None, alias="rollNumber")
    mentor_id: Optional[str] = Field(None, alias="mentorId")
    phone: Optional[str] = None
    year: Optional[str] = None
    section: Optional[str] = None
    is_active: bool = True

    model_config = ConfigDict(populate_by_name=True)


class UserCreate(UserBase):
    password: Optional[str] = Field(None, min_length=6)


class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    role: Optional[UserRole] = None
    roll_number: Optional[str] = Field(None, alias="rollNumber")
    mentor_id: Optional[str] = Field(None, alias="mentorId")
    phone: Optional[str] = None
    year: Optional[str] = None
    section: Optional[str] = None
    is_active: Optional[bool] = None
    password: Optional[str] = Field(None, min_length=6)

    model_config = ConfigDict(populate_by_name=True)


class UserResponse(UserBase):
    id: str = Field(..., alias="_id")
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(populate_by_name=True)

    @computed_field(alias="id")
    @property
    def id_prop(self) -> str:
        return self.id
