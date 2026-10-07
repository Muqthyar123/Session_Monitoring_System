from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator, computed_field


class PlannedAbsenceCreateRequest(BaseModel):
    student_id: Optional[str] = Field(None, alias="studentId")
    roll_number: Optional[str] = Field(None, alias="rollNumber")
    start_date: str = Field(..., alias="startDate", description="Start date in YYYY-MM-DD format")
    end_date: str = Field(..., alias="endDate", description="End date in YYYY-MM-DD format")
    reason: str = Field(..., min_length=3, description="Detailed reason for planned absence")

    model_config = ConfigDict(populate_by_name=True)


class PlannedAbsenceUpdateRequest(BaseModel):
    start_date: Optional[str] = Field(None, alias="startDate")
    end_date: Optional[str] = Field(None, alias="endDate")
    reason: Optional[str] = None
    status: Optional[str] = None  # "ACTIVE" | "CANCELLED"

    model_config = ConfigDict(populate_by_name=True)


class PlannedAbsenceCancelRequest(BaseModel):
    cancellation_reason: Optional[str] = Field(None, alias="cancellationReason")

    model_config = ConfigDict(populate_by_name=True)


class PlannedAbsenceResponse(BaseModel):
    id: str = Field(..., alias="_id")
    student_id: str = Field(..., alias="studentId")
    roll_number: str = Field(..., alias="rollNumber")
    student_name: str = Field(..., alias="studentName")
    year: str
    section: str
    mentor_id: str = Field(..., alias="mentorId")
    mentor_name: str = Field(..., alias="mentorName")
    start_date: str = Field(..., alias="startDate")
    end_date: str = Field(..., alias="endDate")
    reason: str
    status: str = "ACTIVE"
    is_active_today: bool = Field(False, alias="isActiveToday")
    created_by: Optional[str] = Field(None, alias="createdBy")
    created_by_id: Optional[str] = Field(None, alias="createdById")
    cancelled_by: Optional[str] = Field(None, alias="cancelledBy")
    cancelled_at: Optional[datetime] = Field(None, alias="cancelledAt")
    cancellation_reason: Optional[str] = Field(None, alias="cancellationReason")
    created_at: datetime = Field(default_factory=datetime.utcnow, alias="createdAt")
    updated_at: datetime = Field(default_factory=datetime.utcnow, alias="updatedAt")

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
