from datetime import datetime
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


class AttendanceStatus(str, Enum):
    PRESENT = "PRESENT"
    ABSENT = "ABSENT"
    SUBSTITUTE = "SUBSTITUTE"


class AttendanceSubmitRequest(BaseModel):
    session_id: str = Field(..., alias="sessionId")
    status: AttendanceStatus
    substitute_name: Optional[str] = Field(None, alias="substituteName")

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("status", mode="before")
    @classmethod
    def normalize_status(cls, v: Any) -> Any:
        if isinstance(v, str):
            v_upper = v.strip().upper()
            if v_upper in ["NOT PRESENT", "NOT_PRESENT"]:
                return AttendanceStatus.ABSENT
            return v_upper
        return v


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
