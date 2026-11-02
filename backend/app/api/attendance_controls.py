"""Persistent attendance drafts and scoped attendance suspensions."""
from datetime import datetime, timezone
import hashlib
import json
from typing import Literal, Optional
import re
import zoneinfo

from fastapi import APIRouter, Depends, HTTPException, Query
from bson import ObjectId
from pydantic import BaseModel, Field
from pymongo.errors import DuplicateKeyError

from app.core.config import settings
from app.core.dependencies import require_roles
from app.db.mongodb import get_database
from app.schemas.common import ApiResponse
from app.schemas.user import UserRole

router = APIRouter(tags=["Attendance Controls"])
tz = zoneinfo.ZoneInfo(settings.TIMEZONE)


class DraftUpdate(BaseModel):
    year: str = Field(min_length=1, max_length=80)
    section: str = Field(min_length=1, max_length=80)
    date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    session_id: str = Field(alias="sessionId", pattern=r"^SESSION_[12]$")
    absent_rolls: list[str] = Field(alias="absentRolls", max_length=5000)
    version: Optional[int] = Field(None, ge=0)

    model_config = {"populate_by_name": True}


class SuspensionCreate(BaseModel):
    years: list[str] = Field(min_length=1, max_length=30)
    sections_by_year: dict[str, list[str]] = Field(default_factory=dict, alias="sectionsByYear")
    all_sections_years: list[str] = Field(default_factory=list, alias="allSectionsYears")
    start_date: str = Field(alias="startDate", pattern=r"^\d{4}-\d{2}-\d{2}$")
    end_date: str = Field(alias="endDate", pattern=r"^\d{4}-\d{2}-\d{2}$")
    attendance_type: Literal["STUDENT", "FACULTY", "BOTH"] = Field(alias="attendanceType")
    reason: Optional[str] = Field(None, max_length=500)
    request_id: Optional[str] = Field(None, alias="requestId", pattern=r"^[0-9a-fA-F]{24}$")

    model_config = {"populate_by_name": True}


def _actor_id(user: dict) -> str:
    return str(user.get("_id") or user.get("id") or "")


def _local_today() -> str:
    return datetime.now(tz).date().isoformat()


def _valid_date(value: str) -> bool:
    try:
        datetime.strptime(value, "%Y-%m-%d")
        return True
    except ValueError:
        return False


async def _matching_suspensions(db, year: str, section: str, date: str, kind: str):
    query = {
        "status": {"$in": ["ACTIVE", "SCHEDULED"]},
        "cancelled_at": {"$exists": False},
        "start_date": {"$lte": date},
        "end_date": {"$gte": date},
        "$or": [{"years": year}],
        "$and": [{"$or": [{"attendance_type": kind}, {"attendance_type": "BOTH"}]},
                 {"$or": [{"all_sections_years": year}, {f"sections_by_year.{year}": section}]}],
    }
    return await db.attendance_suspensions.find(query).sort("created_at", -1).to_list(length=100)


@router.get("/crlr/attendance-control", response_model=ApiResponse[dict])
async def attendance_control_status(
    year: str = Query(...), section: str = Query(...), date: str = Query(...),
    session_id: str = Query(..., alias="sessionId", pattern=r"^SESSION_[12]$"),
    attendance_type: Literal["STUDENT", "FACULTY"] = Query("STUDENT", alias="attendanceType"),
    user: dict = Depends(require_roles([UserRole.CR, UserRole.LR])),
):
    if year.strip() != (user.get("year") or "").strip() or section.strip().upper() != (user.get("section") or "").strip().upper():
        raise HTTPException(403, "You can only view your assigned section.")
    if not _valid_date(date):
        raise HTTPException(422, "Invalid attendance date.")
    db = get_database()
    await db.attendance_drafts.update_many(
        {"user_id": _actor_id(user), "status": "DRAFT", "date": {"$lt": _local_today()}},
        {"$set": {"status": "EXPIRED", "expired_at": datetime.now(timezone.utc)}},
    )
    suspension = (await _matching_suspensions(db, year.strip(), section.strip().upper(), date, attendance_type))
    draft = await db.attendance_drafts.find_one({"user_id": _actor_id(user), "year": year.strip(), "section": section.strip().upper(), "date": date, "session_id": session_id})
    if draft:
        if date != _local_today() and draft.get("status") == "DRAFT":
            await db.attendance_drafts.update_one({"_id": draft["_id"]}, {"$set": {"status": "EXPIRED", "expired_at": datetime.now(timezone.utc)}})
            draft["status"] = "EXPIRED"
        draft["id"] = str(draft.pop("_id"))
    return ApiResponse(success=True, data={
        "date": date, "sessionId": session_id, "attendanceType": attendance_type,
        "suspended": bool(suspension), "suspensions": [{"startDate": x["start_date"], "endDate": x["end_date"], "reason": x.get("reason")} for x in suspension],
        "draft": draft,
    })


@router.put("/crlr/attendance-draft", response_model=ApiResponse[dict])
async def save_attendance_draft(payload: DraftUpdate, user: dict = Depends(require_roles([UserRole.CR, UserRole.LR]))):
    year, section, date = payload.year.strip(), payload.section.strip().upper(), payload.date
    if year != (user.get("year") or "").strip() or section != (user.get("section") or "").strip().upper():
        raise HTTPException(403, "You can only save drafts for your assigned section.")
    if not _valid_date(date):
        raise HTTPException(422, "Invalid attendance date.")
    if date != _local_today():
        raise HTTPException(409, "This attendance draft has expired and cannot be changed or submitted for another date.")
    rolls = list(dict.fromkeys(r.strip().upper() for r in payload.absent_rolls if r.strip()))
    db = get_database()
    students = await db.students.find({"year": year, "section": section, "roll_number": {"$in": rolls}}, {"roll_number": 1}).to_list(length=5000)
    valid_rolls = {str(s.get("roll_number", "")).strip().upper() for s in students}
    if valid_rolls != set(rolls):
        raise HTTPException(400, "Draft contains students outside the assigned section.")
    key = {"user_id": _actor_id(user), "year": year, "section": section, "date": date, "session_id": payload.session_id}
    draft_id = hashlib.sha256(json.dumps([key[name] for name in ("user_id", "year", "section", "date", "session_id")], ensure_ascii=False).encode("utf-8")).hexdigest()
    existing = await db.attendance_drafts.find_one(key)
    if existing and existing.get("status") != "DRAFT":
        raise HTTPException(409, "This attendance draft is no longer editable.")
    if existing and payload.version is not None and existing.get("version", 0) != payload.version:
        raise HTTPException(409, "This draft changed in another session. Reload before saving.")
    now = datetime.now(timezone.utc)
    update = {"$set": {**key, "absent_rolls": rolls, "status": "DRAFT", "updated_at": now}, "$inc": {"version": 1}, "$setOnInsert": {"_id": draft_id, "created_at": now}}
    try:
        result = await db.attendance_drafts.update_one({**key, **({"version": payload.version} if existing and payload.version is not None else {})}, update, upsert=not bool(existing))
    except DuplicateKeyError:
        # Another tab/process created this exact scoped draft first. Re-read and
        # apply its optimistic version check rather than creating a second draft.
        raise HTTPException(409, "This draft was created in another session. Reload before saving.") from None
    if existing and result.matched_count == 0:
        raise HTTPException(409, "This draft changed in another session. Reload before saving.")
    saved = await db.attendance_drafts.find_one(key)
    saved["id"] = str(saved.pop("_id"))
    return ApiResponse(success=True, data=saved)


@router.get("/admin/attendance-suspensions", response_model=ApiResponse[list])
async def list_suspensions(user: dict = Depends(require_roles([UserRole.ADMIN]))):
    db = get_database()
    today = _local_today()
    records = await db.attendance_suspensions.find({}).sort("created_at", -1).to_list(length=1000)
    result = []
    for row in records:
        row["status"] = "CANCELLED" if row.get("cancelled_at") else "EXPIRED" if row["end_date"] < today else "SCHEDULED" if row["start_date"] > today else "ACTIVE"
        row["id"] = str(row.pop("_id"))
        result.append(row)
    return ApiResponse(success=True, data=result)


@router.post("/admin/attendance-suspensions", response_model=ApiResponse[dict])
async def create_suspension(payload: SuspensionCreate, user: dict = Depends(require_roles([UserRole.ADMIN]))):
    if not _valid_date(payload.start_date) or not _valid_date(payload.end_date) or payload.start_date > payload.end_date:
        raise HTTPException(422, "Suspension dates must be valid and the end date cannot precede the start date.")
    if set(payload.years) != (set(payload.sections_by_year) | set(payload.all_sections_years)):
        raise HTTPException(422, "Choose sections or all sections for every selected academic year.")
    sections_by_year = {y: list(dict.fromkeys(s.strip().upper() for s in payload.sections_by_year.get(y, []) if s.strip())) for y in payload.years}
    if any(not sections_by_year[y] for y in payload.years if y not in payload.all_sections_years):
        raise HTTPException(422, "Each selected year needs at least one section or all sections.")
    db = get_database()
    now = datetime.now(timezone.utc)
    suspension_id = ObjectId(payload.request_id) if payload.request_id else ObjectId()
    doc = {"years": list(dict.fromkeys(payload.years)), "sections_by_year": sections_by_year, "all_sections_years": list(dict.fromkeys(payload.all_sections_years)), "start_date": payload.start_date, "end_date": payload.end_date, "attendance_type": payload.attendance_type, "reason": (payload.reason or "").strip() or None, "created_by_id": _actor_id(user), "created_by": user.get("name"), "created_at": now, "status": "ACTIVE" if payload.start_date <= _local_today() else "SCHEDULED"}
    # Client request IDs make retries safe if the service wakes up slowly or the
    # response is lost after MongoDB accepted the suspension.
    result = await db.attendance_suspensions.update_one(
        {"_id": suspension_id}, {"$setOnInsert": doc}, upsert=True
    )
    saved = await db.attendance_suspensions.find_one({"_id": suspension_id})
    if not result.upserted_id and (
        saved.get("created_by_id") != _actor_id(user)
        or saved.get("years") != list(dict.fromkeys(payload.years))
        or saved.get("sections_by_year") != sections_by_year
        or saved.get("all_sections_years") != list(dict.fromkeys(payload.all_sections_years))
        or saved.get("start_date") != payload.start_date
        or saved.get("end_date") != payload.end_date
        or saved.get("attendance_type") != payload.attendance_type
    ):
        raise HTTPException(409, "This request ID was already used for a different suspension.")
    await db.audit_logs.update_one(
        {"_id": f"attendance-suspension-created:{suspension_id}"},
        {"$setOnInsert": {"action": "ATTENDANCE_SUSPENSION_CREATED", "actor_id": _actor_id(user), "actor_role": "ADMIN", "suspension_id": str(suspension_id), "created_at": saved.get("created_at", now)}},
        upsert=True,
    )
    saved["id"] = str(saved.pop("_id"))
    return ApiResponse(success=True, data=saved)


@router.post("/admin/attendance-suspensions/{suspension_id}/cancel", response_model=ApiResponse[dict])
async def cancel_suspension(suspension_id: str, user: dict = Depends(require_roles([UserRole.ADMIN]))):
    from bson import ObjectId
    if not ObjectId.is_valid(suspension_id):
        raise HTTPException(404, "Suspension not found.")
    db = get_database()
    now = datetime.now(timezone.utc)
    result = await db.attendance_suspensions.update_one({"_id": ObjectId(suspension_id), "cancelled_at": {"$exists": False}}, {"$set": {"cancelled_at": now, "cancelled_by_id": _actor_id(user), "cancelled_by": user.get("name")}})
    if not result.modified_count:
        raise HTTPException(409, "Suspension is missing or already cancelled.")
    await db.audit_logs.insert_one({"action": "ATTENDANCE_SUSPENSION_CANCELLED", "actor_id": _actor_id(user), "actor_role": "ADMIN", "suspension_id": suspension_id, "created_at": now})
    return ApiResponse(success=True, data={"id": suspension_id, "cancelledAt": now})
