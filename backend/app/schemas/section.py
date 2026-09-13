from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class SectionBase(BaseModel):
    year: str
    section_name: str
    department: Optional[str] = None
    assigned_cr_id: Optional[str] = None
    assigned_lr_id: Optional[str] = None
    is_active: bool = True


class SectionCreate(SectionBase):
    pass


class SectionUpdate(BaseModel):
    year: Optional[str] = None
    section_name: Optional[str] = None
    department: Optional[str] = None
    assigned_cr_id: Optional[str] = None
    assigned_lr_id: Optional[str] = None
    is_active: Optional[bool] = None


class SectionResponse(SectionBase):
    id: str = Field(..., alias="_id")
    cr_name: Optional[str] = None
    lr_name: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(populate_by_name=True)
