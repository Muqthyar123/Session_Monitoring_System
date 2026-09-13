from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class AttendanceStatus(str, Enum):
    PRESENT = "PRESENT"
    ABSENT = "ABSENT"
    SUBSTITUTE = "SUBSTITUTE"


class AttendanceSubmitRequest(BaseModel):
    session_id: str
    status: AttendanceStatus
    substitute_name: Optional[str] = None


class AttendanceRecordResponse(BaseModel):
    id: str = Field(..., alias="_id")
    session_id: str
    user_id: str
    user_name: str
    user_role: str
    section: str
    status: AttendanceStatus
    substitute_name: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(populate_by_name=True)


class AdminAlertResponse(BaseModel):
    id: str = Field(..., alias="_id")
    section: str
    subject: str
    session: str
    time: str
    reported_by: str = Field(..., alias="reportedBy")
    reason: str
    status: str = "New"
    created_at: datetime

    model_config = ConfigDict(populate_by_name=True)
