from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, ConfigDict, Field, model_validator, computed_field


class DepartmentBase(BaseModel):
    code: str = Field(..., min_length=1, max_length=20, description="Department Code e.g. CSE, ECE")
    name: str = Field(..., min_length=1, max_length=100, description="Full Department Name")
    coordinator_id: Optional[str] = Field(None, alias="coordinatorId")
    coordinator_name: Optional[str] = Field(None, alias="coordinatorName")
    coordinator_email: Optional[str] = Field(None, alias="coordinatorEmail")
    is_active: bool = Field(True, alias="isActive")
    student_count: Optional[int] = Field(0, alias="studentCount")
    faculty_count: Optional[int] = Field(0, alias="facultyCount")
    section_count: Optional[int] = Field(0, alias="sectionCount")

    model_config = ConfigDict(populate_by_name=True)


class DepartmentCreate(BaseModel):
    code: str = Field(..., min_length=1, max_length=20)
    name: str = Field(..., min_length=1, max_length=100)
    coordinator_id: Optional[str] = Field(None, alias="coordinatorId")
    coordinator_name: Optional[str] = Field(None, alias="coordinatorName")
    coordinator_email: Optional[str] = Field(None, alias="coordinatorEmail")
    is_active: bool = Field(True, alias="isActive")

    model_config = ConfigDict(populate_by_name=True)


class DepartmentUpdate(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None
    coordinator_id: Optional[str] = Field(None, alias="coordinatorId")
    coordinator_name: Optional[str] = Field(None, alias="coordinatorName")
    coordinator_email: Optional[str] = Field(None, alias="coordinatorEmail")
    is_active: Optional[bool] = Field(None, alias="isActive")

    model_config = ConfigDict(populate_by_name=True)


class DepartmentResponse(DepartmentBase):
    id: str = Field(..., alias="_id")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

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
