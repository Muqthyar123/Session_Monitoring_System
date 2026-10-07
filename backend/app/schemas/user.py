from datetime import datetime
from enum import Enum
from typing import Optional, Any
from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator, computed_field


class UserRole(str, Enum):
    ADMIN = "ADMIN"
    CR = "CR"
    LR = "LR"
    MENTOR = "MENTOR"
    DEPARTMENT_COORDINATOR = "DEPARTMENT_COORDINATOR"
    COORDINATOR = "COORDINATOR"


class UserBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: Optional[str] = None
    role: UserRole
    roll_number: Optional[str] = Field(None, alias="rollNumber")
    mentor_id: Optional[str] = Field(None, alias="mentorId")
    phone: Optional[str] = None
    year: Optional[str] = None
    section: Optional[str] = None
    designation: Optional[str] = None
    department: Optional[str] = None
    profile: Optional[str] = None
    is_active: bool = True

    model_config = ConfigDict(populate_by_name=True)


class UserCreate(UserBase):
    password: Optional[str] = Field(None, min_length=6)


class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    role: Optional[UserRole] = None
    roll_number: Optional[str] = Field(None, alias="rollNumber")
    mentor_id: Optional[str] = Field(None, alias="mentorId")
    phone: Optional[str] = None
    year: Optional[str] = None
    section: Optional[str] = None
    designation: Optional[str] = None
    department: Optional[str] = None
    profile: Optional[str] = None
    is_active: Optional[bool] = None
    password: Optional[str] = Field(None, min_length=6)

    model_config = ConfigDict(populate_by_name=True)


class UserResponse(UserBase):
    id: str = Field(..., alias="_id")
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(populate_by_name=True)

    @model_validator(mode="before")
    @classmethod
    def sync_id_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            val = data.get("id") or data.get("_id")
            if val is not None:
                str_val = str(val)
                data["id"] = str_val
                data["_id"] = str_val
        return data

    @computed_field(alias="id")
    @property
    def id_prop(self) -> str:
        return self.id

    @computed_field(alias="_id")
    @property
    def underscore_id_prop(self) -> str:
        return self.id


