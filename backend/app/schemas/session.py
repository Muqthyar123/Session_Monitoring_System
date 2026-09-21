from datetime import datetime
from enum import Enum
from typing import Any, List, Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator


class SessionStatus(str, Enum):
    UPCOMING = "Upcoming"
    ACTIVE = "Active"
    COMPLETED = "Completed"
    EXPIRED = "Expired"


class FacultyResponseStatus(str, Enum):
    PENDING = "Pending"
    PRESENT = "Present"
    ABSENT = "Not Present"
    SUBSTITUTE = "Substitute"


class ClassSessionResponse(BaseModel):
    id: str
    _id: Optional[str] = None
    section: str
    year: Optional[str] = None
    subject: str
    faculty: Optional[str] = None
    period: str
    periods_included: List[int]
    start_time: str = Field(..., alias="startTime")
    end_time: str = Field(..., alias="endTime")
    date: str
    crlr_name: Optional[str] = Field(None, alias="crlrName")
    crlr_role: Optional[str] = Field(None, alias="crlrRole")
    assigned_cr_id: Optional[str] = None
    assigned_lr_id: Optional[str] = None
    session_status: SessionStatus = Field(SessionStatus.UPCOMING, alias="sessionStatus")
    faculty_response: FacultyResponseStatus = Field(
        FacultyResponseStatus.PENDING, alias="facultyResponse"
    )
    response_time: Optional[str] = Field(None, alias="responseTime")
    substitute_name: Optional[str] = Field(None, alias="substituteName")
    response_window_seconds_remaining: Optional[int] = Field(
        None, alias="responseWindowSecondsRemaining"
    )
    response_window_expired: bool = Field(False, alias="responseWindowExpired")

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
