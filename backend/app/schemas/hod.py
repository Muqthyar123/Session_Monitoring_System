from datetime import datetime
from typing import Optional, Any, List
from pydantic import BaseModel, ConfigDict, Field, model_validator, computed_field


class HODCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: str = Field(..., min_length=3, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    branch_code: Optional[str] = Field(None, alias="branchCode")
    branch_id: Optional[str] = Field(None, alias="branchId")
    department_code: str = Field(..., alias="departmentCode", description="Department Code e.g. CSE")
    department_id: Optional[str] = Field(None, alias="departmentId")
    academic_years: List[str] = Field(default_factory=list, alias="academicYears", description="List of assigned academic years e.g. ['1st Year', '2nd Year']")
    password: str = Field(..., min_length=8, max_length=32)
    is_active: bool = Field(True, alias="isActive")

    model_config = ConfigDict(populate_by_name=True)

    @model_validator(mode="before")
    @classmethod
    def sync_branch_and_dept(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # If departmentCode is omitted but branchCode is given, default department to branchCode
            if not data.get("departmentCode") and data.get("branchCode"):
                data["departmentCode"] = data["branchCode"]
            elif not data.get("branchCode") and data.get("departmentCode"):
                data["branchCode"] = data["departmentCode"]
        return data


class HODUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    branch_code: Optional[str] = Field(None, alias="branchCode")
    branch_id: Optional[str] = Field(None, alias="branchId")
    department_code: Optional[str] = Field(None, alias="departmentCode")
    department_id: Optional[str] = Field(None, alias="departmentId")
    academic_years: Optional[List[str]] = Field(None, alias="academicYears")
    password: Optional[str] = Field(None, min_length=8, max_length=32)
    is_active: Optional[bool] = Field(None, alias="isActive")

    model_config = ConfigDict(populate_by_name=True)


class HODResetPassword(BaseModel):
    new_password: str = Field(..., min_length=8, max_length=32, alias="newPassword")

    model_config = ConfigDict(populate_by_name=True)


class HODResponse(BaseModel):
    id: str = Field(..., alias="_id")
    name: str
    email: str
    phone: Optional[str] = None
    branch_code: Optional[str] = Field(None, alias="branchCode")
    branch_name: Optional[str] = Field(None, alias="branchName")
    branch_id: Optional[str] = Field(None, alias="branchId")
    department_code: Optional[str] = Field(None, alias="departmentCode")
    department_name: Optional[str] = Field(None, alias="departmentName")
    department_id: Optional[str] = Field(None, alias="departmentId")
    academic_years: List[str] = Field(default_factory=list, alias="academicYears")
    role: str = "ADMIN"
    designation: str = "HOD"
    is_active: bool = Field(True, alias="isActive")
    student_count: Optional[int] = Field(0, alias="studentCount")
    mentor_count: Optional[int] = Field(0, alias="mentorCount")
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
            # Fallback departmentCode to branch if missing
            if not data.get("department_code") and data.get("department"):
                data["department_code"] = data.get("department")
            if not data.get("department_code") and data.get("branch"):
                data["department_code"] = data.get("branch")
            if not data.get("academic_years") and data.get("year"):
                data["academic_years"] = [data["year"]]
        return data

    @computed_field(alias="id")
    @property
    def id_prop(self) -> str:
        return self.id

    @computed_field(alias="_id")
    @property
    def underscore_id_prop(self) -> str:
        return self.id
