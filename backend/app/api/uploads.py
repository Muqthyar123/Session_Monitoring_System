from typing import Any, Dict, List

from fastapi import APIRouter, Depends, Query
from app.core.dependencies import require_roles
from app.db.mongodb import get_database
from app.schemas.common import ApiResponse
from app.schemas.user import UserRole

router = APIRouter(prefix="/admin/uploads", tags=["Admin Upload History"])

IMPORT_ACTIONS = [
    "IMPORT_CRLR_EXCEL",
    "IMPORT_MENTORS_EXCEL",
    "IMPORT_STUDENTS_EXCEL",
    "IMPORT_TIMETABLE_EXCEL",
    "IMPORT_MENTOR_STUDENT_MAPPING",
]


@router.get("/history", response_model=ApiResponse[List[Dict[str, Any]]])
async def get_upload_history_api(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    admin: dict = Depends(require_roles([UserRole.ADMIN])),
):
    """Return persisted import summaries from the audit log."""
    db = get_database()
    cursor = (
        db.audit_logs.find(
            {"action": {"$in": IMPORT_ACTIONS}},
            {"actor_id": 1, "action": 1, "metadata": 1, "created_at": 1},
        )
        .sort("created_at", -1)
        .skip(skip)
        .limit(limit)
    )
    records = []
    async for record in cursor:
        record["id"] = str(record.pop("_id"))
        records.append(record)
    return ApiResponse(success=True, data=records)
