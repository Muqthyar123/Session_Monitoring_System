from datetime import datetime
from typing import Optional, Any, List, Dict
from pydantic import BaseModel, ConfigDict, Field, model_validator, computed_field


DEFAULT_ACADEMIC_YEARS = ["1st Year", "2nd Year", "3rd Year", "4th Year"]


class DepartmentHODSummary(BaseModel):
    id: str
    name: str
    email: str
    phone: Optional[str] = None
    academic_years: List[str] = Field(default_factory=list, alias="academicYears")
    is_active: bool = Field(True, alias="isActive")

    model_config = ConfigDict(populate_by_name=True)


class DepartmentBase(BaseModel):
    code: str = Field(..., min_length=1, max_length=20, description="Department Code e.g. CSE, ECE")
    name: str = Field(..., min_length=1, max_length=100, description="Full Department Name")
    branch_id: Optional[str] = Field(None, alias="branchId")
    branch_code: Optional[str] = Field(None, alias="branchCode")
    branch_name: Optional[str] = Field(None, alias="branchName")
    description: Optional[str] = Field(None, max_length=500)
    academic_years: List[str] = Field(default_factory=lambda: list(DEFAULT_ACADEMIC_YEARS), alias="academicYears")
    coordinator_id: Optional[str] = Field(None, alias="coordinatorId")
    coordinator_name: Optional[str] = Field(None, alias="coordinatorName")
    coordinator_email: Optional[str] = Field(None, alias="coordinatorEmail")
    is_active: bool = Field(True, alias="isActive")
    student_count: Optional[int] = Field(0, alias="studentCount")
    faculty_count: Optional[int] = Field(0, alias="facultyCount")
    mentor_count: Optional[int] = Field(0, alias="mentorCount")
    section_count: Optional[int] = Field(0, alias="sectionCount")

    model_config = ConfigDict(populate_by_name=True)


class DepartmentCreate(BaseModel):
    code: str = Field(..., min_length=1, max_length=20)
    name: str = Field(..., min_length=1, max_length=100)
    branch_id: Optional[str] = Field(None, alias="branchId")
    branch_code: Optional[str] = Field(None, alias="branchCode")
    branch_name: Optional[str] = Field(None, alias="branchName")
    description: Optional[str] = Field(None, max_length=500)
    academic_years: Optional[List[str]] = Field(None, alias="academicYears")
    coordinator_id: Optional[str] = Field(None, alias="coordinatorId")
    coordinator_name: Optional[str] = Field(None, alias="coordinatorName")
    coordinator_email: Optional[str] = Field(None, alias="coordinatorEmail")
    is_active: bool = Field(True, alias="isActive")

    model_config = ConfigDict(populate_by_name=True)


class DepartmentUpdate(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None
    branch_id: Optional[str] = Field(None, alias="branchId")
    branch_code: Optional[str] = Field(None, alias="branchCode")
    branch_name: Optional[str] = Field(None, alias="branchName")
    description: Optional[str] = None
    academic_years: Optional[List[str]] = Field(None, alias="academicYears")
    coordinator_id: Optional[str] = Field(None, alias="coordinatorId")
    coordinator_name: Optional[str] = Field(None, alias="coordinatorName")
    coordinator_email: Optional[str] = Field(None, alias="coordinatorEmail")
    is_active: Optional[bool] = Field(None, alias="isActive")

    model_config = ConfigDict(populate_by_name=True)


class DepartmentResponse(DepartmentBase):
    id: str = Field(..., alias="_id")
    hods: List[DepartmentHODSummary] = Field(default_factory=list)
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

    @computed_field(alias="studentCount")
    @property
    def student_count_alias(self) -> int:
        return self.student_count or 0

    @computed_field(alias="sectionCount")
    @property
    def section_count_alias(self) -> int:
        return self.section_count or 0

    @computed_field(alias="facultyCount")
    @property
    def faculty_count_alias(self) -> int:
        return self.faculty_count or 0

    @computed_field(alias="mentorCount")
    @property
    def mentor_count_alias(self) -> int:
        return self.mentor_count or 0

    @computed_field(alias="coordinatorName")
    @property
    def coordinator_name_alias(self) -> Optional[str]:
        return self.coordinator_name

    @computed_field(alias="coordinatorEmail")
    @property
    def coordinator_email_alias(self) -> Optional[str]:
        return self.coordinator_email

    @computed_field(alias="isActive")
    @property
    def is_active_alias(self) -> bool:
        return self.is_active
