from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, ConfigDict, Field, model_validator, computed_field


class StudentBase(BaseModel):
    batch: Optional[Any] = None
    branch: Optional[str] = "CSE"
    year: Optional[str] = Field(None, min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=100)
    roll_number: str = Field(..., alias="rollNumber", min_length=1, max_length=50)
    section: str = Field(..., min_length=1, max_length=50)
    student_phone: Optional[str] = Field(None, alias="studentPhone")
    parent_phone: Optional[str] = Field(None, alias="parentPhone")
    crlr_id: Optional[str] = Field(None, alias="crlrId")
    crlr_name: Optional[str] = Field(None, alias="crlrName")
    mentor_id: Optional[str] = Field(None, alias="mentorId")
    mentor_name: Optional[str] = Field(None, alias="mentorName")
    is_planned_absence: Optional[bool] = Field(False, alias="isPlannedAbsence")
    planned_absence_reason: Optional[str] = Field(None, alias="plannedAbsenceReason")
    planned_absence_range: Optional[str] = Field(None, alias="plannedAbsenceRange")
    planned_absence_id: Optional[str] = Field(None, alias="plannedAbsenceId")

    model_config = ConfigDict(populate_by_name=True)


class StudentCreate(StudentBase):
    pass


class StudentUpdate(BaseModel):
    batch: Optional[Any] = None
    branch: Optional[str] = None
    year: Optional[str] = None
    name: Optional[str] = None
    roll_number: Optional[str] = Field(None, alias="rollNumber")
    section: Optional[str] = None
    student_phone: Optional[str] = Field(None, alias="studentPhone")
    parent_phone: Optional[str] = Field(None, alias="parentPhone")
    crlr_id: Optional[str] = Field(None, alias="crlrId")
    crlr_name: Optional[str] = Field(None, alias="crlrName")

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

    @computed_field(alias="id")
    @property
    def id_prop(self) -> str:
        return self.id

    @computed_field(alias="_id")
    @property
    def underscore_id_prop(self) -> str:
        return self.id

