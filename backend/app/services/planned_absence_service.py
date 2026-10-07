from datetime import datetime, timezone
import zoneinfo
from typing import Any, Dict, List, Optional
from bson import ObjectId
from fastapi import HTTPException, status

from app.core.config import settings
from app.db.mongodb import get_database
from app.schemas.planned_absence import (
    PlannedAbsenceCancelRequest,
    PlannedAbsenceCreateRequest,
    PlannedAbsenceResponse,
    PlannedAbsenceUpdateRequest,
)
from app.schemas.user import UserRole
from app.services.mentor_mapping_service import (
    get_mentor_assigned_student_ids,
    is_student_assigned_to_mentor,
)

tz_kolkata = zoneinfo.ZoneInfo(settings.TIMEZONE)


def _get_today_ist() -> str:
    return datetime.now(tz_kolkata).strftime("%Y-%m-%d")


def _doc_to_response(doc: dict) -> PlannedAbsenceResponse:
    today_ist = _get_today_ist()
    start_date = doc.get("start_date", "")
    end_date = doc.get("end_date", "")
    doc_status = doc.get("status", "ACTIVE")

    # Dynamic is_active_today
    is_active_today = (
        doc_status == "ACTIVE"
        and bool(start_date and end_date)
        and (start_date <= today_ist <= end_date)
    )

    return PlannedAbsenceResponse(
        id=str(doc["_id"]),
        student_id=str(doc.get("student_id", "")),
        student_name=doc.get("student_name", ""),
        roll_number=doc.get("roll_number", ""),
        year=doc.get("year", ""),
        section=doc.get("section", ""),
        start_date=start_date,
        end_date=end_date,
        reason=doc.get("reason", ""),
        status=doc_status,
        mentor_id=doc.get("mentor_id"),
        mentor_name=doc.get("mentor_name"),
        created_by_id=doc.get("created_by_id"),
        created_by_name=doc.get("created_by_name"),
        created_by_role=doc.get("created_by_role"),
        cancelled_by=doc.get("cancelled_by"),
        cancelled_at=doc.get("cancelled_at"),
        cancellation_reason=doc.get("cancellation_reason"),
        created_at=doc.get("created_at"),
        updated_at=doc.get("updated_at"),
        is_active_today=is_active_today,
    )


async def create_planned_absence(
    data: PlannedAbsenceCreateRequest, current_user: dict
) -> PlannedAbsenceResponse:
    """Create a new planned absence record for a student."""
    db = get_database()
    now_utc = datetime.now(timezone.utc)
    today_ist = _get_today_ist()

    # 1. Resolve student
    student = None
    if data.student_id:
        clean_sid = data.student_id.strip()
        if ObjectId.is_valid(clean_sid):
            student = await db.students.find_one({"_id": ObjectId(clean_sid)})
        if not student:
            student = await db.students.find_one({"_id": clean_sid})

    if not student and data.roll_number:
        clean_roll = data.roll_number.strip().upper()
        student = await db.students.find_one({"roll_number": clean_roll})

    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found in the system.",
        )

    student_id_str = str(student["_id"])
    roll_number = (student.get("roll_number") or data.roll_number or "").strip().upper()
    student_name = student.get("name") or data.student_name or ""
    year = student.get("year") or data.year or ""
    section = (student.get("section") or data.section or "").strip().upper()

    # 2. RBAC: Verify mentor assignment
    user_role = current_user.get("role", "")
    if user_role == UserRole.MENTOR.value or user_role == "MENTOR":
        is_assigned = await is_student_assigned_to_mentor(student_id_str, current_user)
        if not is_assigned:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. You can only record planned absences for students assigned to you.",
            )

    # 3. Validate dates
    start_date = data.start_date.strip()
    end_date = data.end_date.strip()
    if start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Start date cannot be after end date.",
        )

    # 4. Check overlap with existing ACTIVE planned absences for this student
    # Overlap occurs when: existing.start <= new.end AND existing.end >= new.start
    overlap_query = {
        "status": "ACTIVE",
        "$or": [
            {"student_id": student_id_str},
            {"roll_number": roll_number},
        ],
        "start_date": {"$lte": end_date},
        "end_date": {"$gte": start_date},
    }
    existing_overlap = await db.planned_absences.find_one(overlap_query)
    if existing_overlap:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"An active planned absence already exists for this student from "
                f"{existing_overlap.get('start_date')} to {existing_overlap.get('end_date')} "
                f"(Reason: {existing_overlap.get('reason')}). Please edit or cancel the existing record first."
            ),
        )

    # 5. Insert document
    actor_id = str(current_user.get("_id", ""))
    actor_name = current_user.get("name", "Mentor")
    mentor_id = actor_id if user_role in [UserRole.MENTOR.value, "MENTOR"] else str(student.get("mentor_id") or "")
    mentor_name = actor_name if user_role in [UserRole.MENTOR.value, "MENTOR"] else student.get("mentor_name")

    doc = {
        "student_id": student_id_str,
        "student_name": student_name,
        "roll_number": roll_number,
        "year": year,
        "section": section,
        "start_date": start_date,
        "end_date": end_date,
        "reason": data.reason.strip(),
        "status": "ACTIVE",
        "mentor_id": mentor_id,
        "mentor_name": mentor_name,
        "created_by_id": actor_id,
        "created_by_name": actor_name,
        "created_by_role": user_role,
        "created_at": now_utc,
        "updated_at": now_utc,
    }

    result = await db.planned_absences.insert_one(doc)
    doc["_id"] = result.inserted_id

    # 6. Audit log
    await db.audit_logs.insert_one({
        "actor_id": actor_id,
        "actor_email": current_user.get("email"),
        "action": "CREATE_PLANNED_ABSENCE",
        "target_student_id": student_id_str,
        "target_roll_number": roll_number,
        "metadata": {
            "start_date": start_date,
            "end_date": end_date,
            "reason": data.reason.strip(),
            "planned_absence_id": str(result.inserted_id),
        },
        "created_at": now_utc,
    })

    return _doc_to_response(doc)


async def get_planned_absences(
    current_user: dict,
    student_id: Optional[str] = None,
    roll_number: Optional[str] = None,
    year: Optional[str] = None,
    section: Optional[str] = None,
    status_filter: Optional[str] = None,
    active_only: bool = False,
) -> List[PlannedAbsenceResponse]:
    """Retrieve planned absences based on filters and RBAC."""
    db = get_database()
    query: Dict[str, Any] = {}

    user_role = current_user.get("role", "")
    if user_role == UserRole.MENTOR.value or user_role == "MENTOR":
        assigned_ids = await get_mentor_assigned_student_ids(current_user)
        if assigned_ids is not None:
            if not assigned_ids:
                return []
            mentor_user_id = str(current_user.get("_id", ""))
            query["$or"] = [
                {"student_id": {"$in": assigned_ids}},
                {"mentor_id": mentor_user_id},
                {"created_by_id": mentor_user_id},
            ]

    if student_id:
        clean_sid = student_id.strip()
        query["student_id"] = clean_sid

    if roll_number:
        query["roll_number"] = roll_number.strip().upper()

    if year:
        query["year"] = year.strip()

    if section:
        query["section"] = section.strip().upper()

    if status_filter:
        query["status"] = status_filter.strip().upper()

    cursor = db.planned_absences.find(query).sort([
        ("start_date", -1),
        ("created_at", -1),
    ])

    today_ist = _get_today_ist()
    results: List[PlannedAbsenceResponse] = []
    async for doc in cursor:
        resp = _doc_to_response(doc)
        if active_only:
            if not resp.is_active_today:
                continue
        results.append(resp)

    return results


async def update_planned_absence(
    absence_id: str, data: PlannedAbsenceUpdateRequest, current_user: dict
) -> PlannedAbsenceResponse:
    """Update planned absence dates or reason."""
    db = get_database()
    clean_id = absence_id.strip()

    doc = None
    if ObjectId.is_valid(clean_id):
        doc = await db.planned_absences.find_one({"_id": ObjectId(clean_id)})
    if not doc:
        doc = await db.planned_absences.find_one({"_id": clean_id})
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Planned absence record not found.",
        )

    if doc.get("status") == "CANCELLED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot edit a cancelled planned absence.",
        )

    # RBAC check
    user_role = current_user.get("role", "")
    if user_role == UserRole.MENTOR.value or user_role == "MENTOR":
        is_assigned = await is_student_assigned_to_mentor(str(doc.get("student_id")), current_user)
        is_creator = str(doc.get("created_by_id")) == str(current_user.get("_id"))
        if not (is_assigned or is_creator):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. You can only edit planned absences for your assigned students.",
            )

    start_date = (data.start_date or doc.get("start_date", "")).strip()
    end_date = (data.end_date or doc.get("end_date", "")).strip()

    if start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Start date cannot be after end date.",
        )

    # Check overlap with other active absences
    overlap_query = {
        "_id": {"$ne": doc["_id"]},
        "status": "ACTIVE",
        "$or": [
            {"student_id": str(doc.get("student_id"))},
            {"roll_number": doc.get("roll_number")},
        ],
        "start_date": {"$lte": end_date},
        "end_date": {"$gte": start_date},
    }
    existing_overlap = await db.planned_absences.find_one(overlap_query)
    if existing_overlap:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"An overlapping active planned absence exists from "
                f"{existing_overlap.get('start_date')} to {existing_overlap.get('end_date')}."
            ),
        )

    now_utc = datetime.now(timezone.utc)
    update_fields: Dict[str, Any] = {
        "start_date": start_date,
        "end_date": end_date,
        "updated_at": now_utc,
        "updated_by_id": str(current_user.get("_id", "")),
        "updated_by_name": current_user.get("name", "Mentor"),
    }
    if data.reason is not None and data.reason.strip():
        update_fields["reason"] = data.reason.strip()

    await db.planned_absences.update_one({"_id": doc["_id"]}, {"$set": update_fields})

    # Audit log
    await db.audit_logs.insert_one({
        "actor_id": str(current_user.get("_id", "")),
        "actor_email": current_user.get("email"),
        "action": "UPDATE_PLANNED_ABSENCE",
        "target_planned_absence_id": str(doc["_id"]),
        "metadata": update_fields,
        "created_at": now_utc,
    })

    updated_doc = await db.planned_absences.find_one({"_id": doc["_id"]})
    return _doc_to_response(updated_doc)


async def cancel_planned_absence(
    absence_id: str, data: PlannedAbsenceCancelRequest, current_user: dict
) -> PlannedAbsenceResponse:
    """Cancel an existing planned absence record with a cancellation reason."""
    db = get_database()
    clean_id = absence_id.strip()

    doc = None
    if ObjectId.is_valid(clean_id):
        doc = await db.planned_absences.find_one({"_id": ObjectId(clean_id)})
    if not doc:
        doc = await db.planned_absences.find_one({"_id": clean_id})
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Planned absence record not found.",
        )

    if doc.get("status") == "CANCELLED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This planned absence is already cancelled.",
        )

    user_role = current_user.get("role", "")
    if user_role == UserRole.MENTOR.value or user_role == "MENTOR":
        is_assigned = await is_student_assigned_to_mentor(str(doc.get("student_id")), current_user)
        is_creator = str(doc.get("created_by_id")) == str(current_user.get("_id"))
        if not (is_assigned or is_creator):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. You can only cancel planned absences for your assigned students.",
            )

    now_utc = datetime.now(timezone.utc)
    cancel_reason = (data.cancellation_reason or "").strip() or "Cancelled by user"

    update_fields = {
        "status": "CANCELLED",
        "cancellation_reason": cancel_reason,
        "cancelled_by": current_user.get("name", "Mentor"),
        "cancelled_by_id": str(current_user.get("_id", "")),
        "cancelled_at": now_utc,
        "updated_at": now_utc,
    }

    await db.planned_absences.update_one({"_id": doc["_id"]}, {"$set": update_fields})

    await db.audit_logs.insert_one({
        "actor_id": str(current_user.get("_id", "")),
        "actor_email": current_user.get("email"),
        "action": "CANCEL_PLANNED_ABSENCE",
        "target_planned_absence_id": str(doc["_id"]),
        "metadata": update_fields,
        "created_at": now_utc,
    })

    updated_doc = await db.planned_absences.find_one({"_id": doc["_id"]})
    return _doc_to_response(updated_doc)


async def get_active_planned_absence_for_student(
    student_id_or_roll: str, date_str: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """Quick lookup to check if a student has an active planned absence for a given date."""
    if not student_id_or_roll:
        return None
    db = get_database()
    target_date = date_str.strip() if date_str else _get_today_ist()
    clean_val = student_id_or_roll.strip()

    query = {
        "status": "ACTIVE",
        "start_date": {"$lte": target_date},
        "end_date": {"$gte": target_date},
        "$or": [
            {"student_id": clean_val},
            {"roll_number": clean_val.upper()},
        ],
    }
    if ObjectId.is_valid(clean_val):
        query["$or"].append({"student_id": str(ObjectId(clean_val))})

    doc = await db.planned_absences.find_one(query)
    if doc:
        doc["id"] = str(doc["_id"])
        doc["_id"] = str(doc["_id"])
        return doc
    return None


async def batch_get_active_planned_absences_map(
    student_ids_or_rolls: List[str], date_str: Optional[str] = None
) -> Dict[str, Dict[str, Any]]:
    """
    Returns a dictionary mapping student_id and roll_number to their active planned absence dict
    for the specified date (default today in IST).
    """
    if not student_ids_or_rolls:
        return {}

    db = get_database()
    target_date = date_str.strip() if date_str else _get_today_ist()

    clean_vals = [v.strip() for v in student_ids_or_rolls if v and v.strip()]
    clean_rolls = [v.upper() for v in clean_vals]

    query = {
        "status": "ACTIVE",
        "start_date": {"$lte": target_date},
        "end_date": {"$gte": target_date},
        "$or": [
            {"student_id": {"$in": clean_vals}},
            {"roll_number": {"$in": clean_rolls}},
        ],
    }

    cursor = db.planned_absences.find(query)
    result_map: Dict[str, Dict[str, Any]] = {}
    async for doc in cursor:
        doc["id"] = str(doc["_id"])
        doc["_id"] = str(doc["_id"])
        if doc.get("student_id"):
            result_map[str(doc["student_id"])] = doc
        if doc.get("roll_number"):
            result_map[str(doc["roll_number"]).upper()] = doc

    return result_map
