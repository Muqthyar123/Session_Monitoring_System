from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class NotificationType(str, Enum):
    FACULTY_ATTENDANCE_REQUIRED = "FACULTY_ATTENDANCE_REQUIRED"
    FACULTY_ABSENT_ALERT = "FACULTY_ABSENT_ALERT"
    NO_RESPONSE_ALERT = "NO_RESPONSE_ALERT"
    ATTENDANCE_RECORDED = "ATTENDANCE_RECORDED"
    SYSTEM_NOTIFICATION = "SYSTEM_NOTIFICATION"


class NotificationResponse(BaseModel):
    id: str = Field(..., alias="_id")
    recipient_user_id: str
    type: NotificationType
    title: str
    message: str
    section: Optional[str] = None
    subject: Optional[str] = None
    time: Optional[str] = None
    session_id: Optional[str] = None
    is_read: bool = Field(False, alias="read")
    created_at: datetime

    model_config = ConfigDict(populate_by_name=True)


class PushSubscriptionRegisterRequest(BaseModel):
    token: str
    device_info: Optional[str] = None
