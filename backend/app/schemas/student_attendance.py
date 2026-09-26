from datetime import datetime
from typing import List, Optional, Any
from pydantic import BaseModel, ConfigDict, Field, model_validator


class AbsenteeItem(BaseModel):
    roll_number: str = Field(..., alias="rollNumber")
    student_id: Optional[str] = Field(None, alias="studentId")
    student_name: str = Field(..., alias="studentName")
    student_phone: Optional[str] = Field(None, alias="studentPhone")
    parent_phone: Optional[str] = Field(None, alias="parentPhone")

    model_config = ConfigDict(populate_by_name=True)


class StudentAttendanceSubmitRequest(BaseModel):
    year: str
    section: str
    absentees: List[AbsenteeItem]

    model_config = ConfigDict(populate_by_name=True)


class AbsenteeReasonSaveRequest(BaseModel):
    reason: str


class StudentAttendanceRecordResponse(BaseModel):
    id: str = Field(..., alias="_id")
    date: str
    year: str
    section: str
    roll_number: str = Field(..., alias="rollNumber")
    student_id: Optional[str] = Field(None, alias="studentId")
    student_name: str = Field(..., alias="studentName")
    student_phone: Optional[str] = Field(None, alias="studentPhone")
    parent_phone: Optional[str] = Field(None, alias="parentPhone")
    submitted_by: Optional[str] = Field(None, alias="submittedBy")
    status: str = "Absent"
    reason: Optional[str] = None
    created_at: Optional[datetime] = None

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


class StudentAnalyticsItem(BaseModel):
    student_id: Optional[str] = Field(None, alias="studentId")
    student_name: str = Field(..., alias="studentName")
    roll_number: str = Field(..., alias="rollNumber")
    year: str
    section: str
    student_phone: Optional[str] = Field(None, alias="studentPhone")
    parent_phone: Optional[str] = Field(None, alias="parentPhone")
    total_absences: int = Field(0, alias="totalAbsences")
    total_days: int = Field(0, alias="totalDays")
    attendance_percentage: float = Field(100.0, alias="attendancePercentage")

    model_config = ConfigDict(populate_by_name=True)
