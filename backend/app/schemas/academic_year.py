from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, ConfigDict, Field, model_validator, computed_field


class AcademicYearBase(BaseModel):
    code: str = Field(..., min_length=1, max_length=20, description="Year code e.g. '1', '2', '3', '4'")
    name: str = Field(..., min_length=1, max_length=50, description="Year label e.g. '1st Year', '2nd Year'")
    order: int = Field(1, ge=1, le=10, description="Display order")
    is_active: bool = Field(True, alias="isActive")
    description: Optional[str] = Field(None, max_length=200)

    model_config = ConfigDict(populate_by_name=True)


class AcademicYearCreate(AcademicYearBase):
    pass


class AcademicYearUpdate(BaseModel):
    name: Optional[str] = None
    order: Optional[int] = None
    is_active: Optional[bool] = Field(None, alias="isActive")
    description: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True)


class AcademicYearResponse(AcademicYearBase):
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
