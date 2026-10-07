from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, ConfigDict, Field, model_validator, computed_field


class SectionBase(BaseModel):
    year: str
    branch: Optional[str] = Field("CSE", alias="department")
    section_name: str = Field(..., alias="sectionName")
    assigned_cr_id: Optional[str] = Field(None, alias="assignedCrId")
    assigned_lr_id: Optional[str] = Field(None, alias="assignedLrId")
    is_active: bool = Field(True, alias="isActive")
    student_count: Optional[int] = Field(0, alias="studentCount")

    model_config = ConfigDict(populate_by_name=True)

    @model_validator(mode="before")
    @classmethod
    def sync_branch_and_section(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # Normalize branch/department
            if "branch" not in data and "department" in data:
                data["branch"] = data["department"]
            elif "department" not in data and "branch" in data:
                data["department"] = data["branch"]
            # Normalize section_name / section
            if "section_name" not in data and "section" in data:
                data["section_name"] = data["section"]
            elif "section" not in data and "section_name" in data:
                data["section"] = data["section_name"]
        return data


class SectionCreate(BaseModel):
    year: str
    branch: Optional[str] = Field("CSE", alias="department")
    section_name: str = Field(..., alias="sectionName")
    assigned_cr_id: Optional[str] = Field(None, alias="assignedCrId")
    assigned_lr_id: Optional[str] = Field(None, alias="assignedLrId")
    is_active: bool = Field(True, alias="isActive")

    model_config = ConfigDict(populate_by_name=True)

    @model_validator(mode="before")
    @classmethod
    def sync_branch_and_section(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "branch" not in data and "department" in data:
                data["branch"] = data["department"]
            elif "department" not in data and "branch" in data:
                data["department"] = data["branch"]
            if "section_name" not in data and "section" in data:
                data["section_name"] = data["section"]
        return data


class SectionUpdate(BaseModel):
    year: Optional[str] = None
    branch: Optional[str] = Field(None, alias="department")
    section_name: Optional[str] = Field(None, alias="sectionName")
    assigned_cr_id: Optional[str] = Field(None, alias="assignedCrId")
    assigned_lr_id: Optional[str] = Field(None, alias="assignedLrId")
    is_active: Optional[bool] = Field(None, alias="isActive")

    model_config = ConfigDict(populate_by_name=True)


class SectionResponse(SectionBase):
    id: str = Field(..., alias="_id")
    cr_name: Optional[str] = Field(None, alias="crName")
    lr_name: Optional[str] = Field(None, alias="lrName")
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
