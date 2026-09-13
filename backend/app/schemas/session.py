from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


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
    id: str = Field(..., alias="_id")
    section: str
    year: Optional[str] = None
    subject: str
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
