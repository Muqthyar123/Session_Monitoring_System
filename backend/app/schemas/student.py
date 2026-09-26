from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, ConfigDict, Field, model_validator


class StudentBase(BaseModel):
    year: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=100)
    roll_number: str = Field(..., alias="rollNumber", min_length=1, max_length=50)
    section: str = Field(..., min_length=1, max_length=50)
    student_phone: Optional[str] = Field(None, alias="studentPhone")
    parent_phone: Optional[str] = Field(None, alias="parentPhone")

    model_config = ConfigDict(populate_by_name=True)


class StudentCreate(StudentBase):
    pass


class StudentUpdate(BaseModel):
    year: Optional[str] = None
    name: Optional[str] = None
    roll_number: Optional[str] = Field(None, alias="rollNumber")
    section: Optional[str] = None
    student_phone: Optional[str] = Field(None, alias="studentPhone")
    parent_phone: Optional[str] = Field(None, alias="parentPhone")

    model_config = ConfigDict(populate_by_name=True)


class StudentResponse(StudentBase):
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
