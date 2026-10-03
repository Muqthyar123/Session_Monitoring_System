from typing import List, Optional, Any, Dict
from pydantic import BaseModel, ConfigDict, Field


class MentorYearCard(BaseModel):
    year: str
    student_count: int = Field(0, alias="studentCount")
    absentee_count: int = Field(0, alias="absenteeCount")

    model_config = ConfigDict(populate_by_name=True)


class MentorSectionCard(BaseModel):
    section: str
    year: str
    student_count: int = Field(0, alias="studentCount")
    absentee_count: int = Field(0, alias="absenteeCount")

    model_config = ConfigDict(populate_by_name=True)


class MentorInfo(BaseModel):
    id: str
    name: str
    email: Optional[str] = None
    mentor_id: Optional[str] = Field(None, alias="mentorId")
    phone: Optional[str] = None
    department: Optional[str] = None
    designation: Optional[str] = None
    role: str = "MENTOR"

    model_config = ConfigDict(populate_by_name=True)


class MentorDashboardResponse(BaseModel):
    mentor_info: MentorInfo = Field(..., alias="mentorInfo")
    total_students: int = Field(..., alias="totalStudents")
    total_absentees_today: int = Field(..., alias="totalAbsenteesToday")
    year_counts: List[MentorYearCard] = Field(..., alias="yearCounts")
    section_counts: List[MentorSectionCard] = Field(..., alias="sectionCounts")

    model_config = ConfigDict(populate_by_name=True)


class MentorCommentRequest(BaseModel):
    comment: str = Field(..., min_length=1, max_length=500)
