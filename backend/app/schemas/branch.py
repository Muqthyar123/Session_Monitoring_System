from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, ConfigDict, Field, model_validator, computed_field


class BranchBase(BaseModel):
    code: str = Field(..., min_length=1, max_length=20, description="Branch Code e.g. CSE, ECE")
    name: str = Field(..., min_length=1, max_length=100, description="Branch Name e.g. Computer Science & Engineering")
    site_id: Optional[str] = Field(None, alias="siteId")
    site_name: Optional[str] = Field(None, alias="siteName")
    site_code: Optional[str] = Field(None, alias="siteCode")
    hod_id: Optional[str] = Field(None, alias="hodId")
    hod_name: Optional[str] = Field(None, alias="hodName")
    hod_email: Optional[str] = Field(None, alias="hodEmail")
    hod_phone: Optional[str] = Field(None, alias="hodPhone")
    description: Optional[str] = Field(None, max_length=500)
    is_active: bool = Field(True, alias="isActive")
    student_count: Optional[int] = Field(0, alias="studentCount")
    mentor_count: Optional[int] = Field(0, alias="mentorCount")
    section_count: Optional[int] = Field(0, alias="sectionCount")

    model_config = ConfigDict(populate_by_name=True)


class BranchCreate(BaseModel):
    code: str = Field(..., min_length=1, max_length=20)
    name: str = Field(..., min_length=1, max_length=100)
    site_id: Optional[str] = Field(None, alias="siteId")
    site_name: Optional[str] = Field(None, alias="siteName")
    site_code: Optional[str] = Field(None, alias="siteCode")
    hod_id: Optional[str] = Field(None, alias="hodId")
    description: Optional[str] = Field(None, max_length=500)
    is_active: bool = Field(True, alias="isActive")

    model_config = ConfigDict(populate_by_name=True)


class BranchUpdate(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None
    site_id: Optional[str] = Field(None, alias="siteId")
    site_name: Optional[str] = Field(None, alias="siteName")
    site_code: Optional[str] = Field(None, alias="siteCode")
    hod_id: Optional[str] = Field(None, alias="hodId")
    description: Optional[str] = None
    is_active: Optional[bool] = Field(None, alias="isActive")

    model_config = ConfigDict(populate_by_name=True)


class BranchResponse(BranchBase):
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
