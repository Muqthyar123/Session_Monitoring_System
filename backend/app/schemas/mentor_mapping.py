from datetime import datetime
from typing import Any, List, Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator, computed_field


class MentorMappingRow(BaseModel):
    row_idx: int = Field(..., alias="rowIdx")
    mentor_name: str = Field(..., alias="mentorName")
    mentor_id: Optional[str] = Field(None, alias="mentorId")
    year: str
    section: str
    start_serial: Optional[int] = Field(None, alias="startSerial")
    end_serial: Optional[int] = Field(None, alias="endSerial")
    is_full_section: bool = Field(False, alias="isFullSection")
    status: str = "VALID"  # "VALID" | "ERROR"
    error_message: Optional[str] = Field(None, alias="errorMessage")
    student_count: int = Field(0, alias="studentCount")
    matched_students: List[dict] = Field(default_factory=list, alias="matchedStudents")

    model_config = ConfigDict(populate_by_name=True)


class MentorMappingPreviewResponse(BaseModel):
    total_rows: int = Field(..., alias="totalRows")
    valid_rows: int = Field(..., alias="validRows")
    invalid_rows: int = Field(..., alias="invalidRows")
    students_to_assign: int = Field(..., alias="studentsToAssign")
    conflicts_count: int = Field(0, alias="conflictsCount")
    rows: List[MentorMappingRow] = Field(default_factory=list)

    model_config = ConfigDict(populate_by_name=True)


class MentorMappingConfirmRequest(BaseModel):
    mode: str = Field("ADD_UPDATE", description="ADD_UPDATE or REPLACE")
    rows: Optional[List[dict]] = None

    model_config = ConfigDict(populate_by_name=True)


class MentorMappingResponse(BaseModel):
    id: str = Field(..., alias="_id")
    mentor_id: str = Field(..., alias="mentorId")
    mentor_name: str = Field(..., alias="mentorName")
    mentor_email: Optional[str] = Field(None, alias="mentorEmail")
    year: str
    section: str
    start_serial: Optional[int] = Field(None, alias="startSerial")
    end_serial: Optional[int] = Field(None, alias="endSerial")
    is_full_section: bool = Field(False, alias="isFullSection")
    student_count: int = Field(0, alias="studentCount")
    student_ids: List[str] = Field(default_factory=list, alias="studentIds")
    source: str = "excel_import"
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
