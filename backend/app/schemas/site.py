from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, ConfigDict, Field, model_validator, computed_field


class SiteBase(BaseModel):
    code: str = Field(..., min_length=1, max_length=20, description="Site Code e.g. MAIN, CITY")
    name: str = Field(..., min_length=1, max_length=100, description="Full Site / Campus Name")
    location: Optional[str] = Field(None, max_length=200, description="City / Location")
    address: Optional[str] = Field(None, max_length=300)
    contact_email: Optional[str] = Field(None, alias="contactEmail")
    contact_phone: Optional[str] = Field(None, alias="contactPhone")
    description: Optional[str] = Field(None, max_length=500)
    is_active: bool = Field(True, alias="isActive")
    branch_count: Optional[int] = Field(0, alias="branchCount")

    model_config = ConfigDict(populate_by_name=True)


class SiteCreate(BaseModel):
    code: str = Field(..., min_length=1, max_length=20)
    name: str = Field(..., min_length=1, max_length=100)
    location: Optional[str] = Field(None, max_length=200)
    address: Optional[str] = Field(None, max_length=300)
    contact_email: Optional[str] = Field(None, alias="contactEmail")
    contact_phone: Optional[str] = Field(None, alias="contactPhone")
    description: Optional[str] = Field(None, max_length=500)
    is_active: bool = Field(True, alias="isActive")

    model_config = ConfigDict(populate_by_name=True)


class SiteUpdate(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None
    location: Optional[str] = None
    address: Optional[str] = None
    contact_email: Optional[str] = Field(None, alias="contactEmail")
    contact_phone: Optional[str] = Field(None, alias="contactPhone")
    description: Optional[str] = None
    is_active: Optional[bool] = Field(None, alias="isActive")

    model_config = ConfigDict(populate_by_name=True)


class SiteResponse(SiteBase):
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
