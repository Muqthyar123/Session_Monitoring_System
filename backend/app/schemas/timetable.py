from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class TimetablePeriodResponse(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    year: str
    section: str
    day: str
    period: int
    start_time: str
    end_time: str
    subject: str
    faculty: Optional[str] = None
    room: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True)


class TimetableUploadSummary(BaseModel):
    id: str
    academic_year: str
    section: str
    uploaded_date: str
    status: str
