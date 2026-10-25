import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from bson import ObjectId
from fastapi import HTTPException, status
from app.db.mongodb import get_database
from app.schemas.student import StudentCreate, StudentResponse, StudentUpdate


def infer_batch_from_roll(roll: Optional[str]) -> Optional[int]:
    """Infers graduation batch year from roll number if possible (e.g. 23... -> 2027, 24... -> 2028)."""
    if not roll or not isinstance(roll, str):
        return None
    roll_clean = roll.strip().upper()
    m = re.match(r'^(\d{2})', roll_clean)
    if m:
        yy = int(m.group(1))
        if 18 <= yy <= 40:
            adm_year = 2000 + yy
            # Lateral entry check (e.g., 23LE, 5th char '5' or 'L')
            if re.search(r'^\d{2}[A-Z0-9]{2}[5L]', roll_clean):
                return adm_year + 3
            else:
                return adm_year + 4
    return None


def compute_year_from_batch(batch_val: Any) -> str:
    """
    Computes academic year from batch graduation year dynamically based on current date.
    Academic year runs on a July-June cycle:
    - Current Academic Year starts in Y (July Y to June Y+1).
      senior_batch (4th Year graduating class) = now.year if now.month < 7 else now.year + 1
      academic_base = now.year if now.month >= 7 else now.year - 1
    - 2027 -> 4th Year (diff = 1)
    - 2028 -> 3rd Year (diff = 2)
    - 2029 -> 2nd Year (diff = 3)
    - 2030 -> 1st Year (diff = 4)
    - 2031+ -> 1st Year (diff >= 5)
    - <= 2026 -> Graduated (diff <= 0)
    """
    if not batch_val:
        return "2nd Year"
    try:
        now = datetime.now(timezone.utc)
        academic_base = now.year if now.month >= 7 else now.year - 1

        m = re.search(r'\b(20\d{2})\b', str(batch_val))
        if m:
            b_num = int(m.group(1))
            diff = b_num - academic_base
            if diff <= 0:
                return "Graduated"
            elif diff == 1:
                return "4th Year"
            elif diff == 2:
                return "3rd Year"
            elif diff == 3:
                return "2nd Year"
            else:
                return "1st Year"

        m2 = re.search(r'\b(\d{2})\b', str(batch_val))
        if m2:
            yy = int(m2.group(1))
            if 20 <= yy <= 40:
                b_num = 2000 + yy
                diff = b_num - academic_base
                if diff <= 0:
                    return "Graduated"
                elif diff == 1:
                    return "4th Year"
                elif diff == 2:
                    return "3rd Year"
                elif diff == 3:
                    return "2nd Year"
                else:
                    return "1st Year"
    except Exception:
        pass

    s_val = str(batch_val).strip().lower()
    if "4th" in s_val or "iv" in s_val or s_val == "4":
        return "4th Year"
    if "3rd" in s_val or "iii" in s_val or s_val == "3":
        return "3rd Year"
    if "2nd" in s_val or "ii" in s_val or s_val == "2":
        return "2nd Year"
    if "1st" in s_val or "i" in s_val or s_val == "1":
        return "1st Year"
    return "2nd Year"


def normalize_student_section(value: str, year: str, branch: str = "CSE") -> str:
    raw = (value or "").strip().upper()
    branch = (branch or "CSE").strip().upper()
    roman = {"1st Year": "I", "2nd Year": "II", "3rd Year": "III", "4th Year": "IV"}.get(year, "II")
    raw = re.sub(r"^SECTION\s*[-:]?\s*", "", raw)
    match = re.match(r"^(?:I|II|III|IV)-[A-Z]+-([A-Z0-9]+)$", raw)
    if match:
        label = match.group(1)
    elif "-" in raw:
        label = raw.rsplit("-", 1)[-1]
    else:
        label = raw
    return f"{roman}-{branch}-{label}" if label else f"{roman}-{branch}"


async def find_crlr_for_student(db, year: str, section: str) -> Tuple[Optional[str], Optional[str]]:
    """Finds CR/LR user ID and name for a given year and section."""
    clean_sec = section.strip().upper()
    sec_norm = re.sub(r"^(?:I|II|III|IV)-", "", clean_sec)
    sec_norm = re.sub(r"^[A-Z]+-", "", sec_norm).strip()
    parts = clean_sec.split("-")
    branch = parts[1] if len(parts) >= 3 else "CSE"
    aliases = list({clean_sec, f"{branch}-{sec_norm}", sec_norm})

    user = await db.users.find_one({
        "role": {"$in": ["CR", "LR"]},
        "year": year,
        "section": {"$in": aliases},
    })

    if user:
        return str(user["_id"]), user.get("name")

    sec_doc = await db.sections.find_one({
        "year": year,
        "section_name": {"$in": aliases},
    })
    if sec_doc:
        cr_id = sec_doc.get("assigned_cr_id") or sec_doc.get("assigned_lr_id")
        if cr_id and ObjectId.is_valid(cr_id):
            cr_u = await db.users.find_one({"_id": ObjectId(cr_id)})
            if cr_u:
                return str(cr_u["_id"]), cr_u.get("name")

    return None, None


async def create_student(data: StudentCreate, actor_id: Optional[str] = None) -> StudentResponse:
    db = get_database()
    roll_clean = data.roll_number.strip().upper()

    existing_roll = await db.students.find_one({"roll_number": roll_clean})
    if existing_roll:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Student with roll number '{roll_clean}' already exists.",
        )

    batch = data.batch
    if batch is None and roll_clean:
        batch = infer_batch_from_roll(roll_clean)
    if batch is None:
        batch = 2029

    year = data.year.strip() if data.year else compute_year_from_batch(batch)
    branch = (data.branch or "CSE").strip().upper()
    sec_clean = normalize_student_section(data.section, year, branch)

    crlr_id, crlr_name = await find_crlr_for_student(db, year, sec_clean)

    now = datetime.now(timezone.utc)
    student_doc = {
        "batch": batch,
        "branch": branch,
        "year": year,
        "name": data.name.strip(),
        "roll_number": roll_clean,
        "section": sec_clean,
        "student_phone": data.student_phone.strip() if data.student_phone else None,
        "parent_phone": data.parent_phone.strip() if data.parent_phone else None,
        "crlr_id": crlr_id,
        "crlr_name": crlr_name,
        "created_at": now,
        "updated_at": now,
    }

    res = await db.students.insert_one(student_doc)
    student_id = str(res.inserted_id)
    student_doc["_id"] = student_id

    if actor_id:
        await db.audit_logs.insert_one({
            "actor_id": actor_id,
            "action": "CREATE_STUDENT",
            "target_student_id": student_id,
            "metadata": {"roll_number": roll_clean, "batch": batch, "crlr": crlr_name},
            "created_at": now,
        })

    return StudentResponse(**student_doc)


async def sync_all_students_batch_and_year(db) -> int:
    """
    Synchronizes batch, academic year, and section for all students in MongoDB:
    - Batch 2027 -> 4th Year -> IV-CSE-...
    - Batch 2028 -> 3rd Year -> III-CSE-...
    - Batch 2029 -> 2nd Year -> II-CSE-...
    - Batch 2030 -> 1st Year -> I-CSE-...
    Also guarantees that all respective section documents exist in db.sections.
    """
    cursor = db.students.find({})
    now = datetime.now(timezone.utc)
    needed_sections = set()
    bulk_ops = []

    async for s in cursor:
        roll = s.get("roll_number")
        batch = s.get("batch")
        inferred = infer_batch_from_roll(roll) if roll else None
        eff_batch = batch if batch else inferred
        if eff_batch:
            eff_year = compute_year_from_batch(eff_batch)
            branch = s.get("branch") or "CSE"
            raw_sec = s.get("section") or "A"
            eff_sec = normalize_student_section(raw_sec, eff_year, branch)

            updates = {}
            if s.get("batch") != eff_batch:
                updates["batch"] = eff_batch
            if s.get("year") != eff_year:
                updates["year"] = eff_year
            if s.get("section") != eff_sec:
                updates["section"] = eff_sec

            if updates:
                updates["updated_at"] = now
                bulk_ops.append((s["_id"], updates))

            needed_sections.add((eff_year, eff_sec, branch))

    updated_cnt = 0
    for doc_id, upd in bulk_ops:
        await db.students.update_one({"_id": doc_id}, {"$set": upd})
        updated_cnt += 1

    # Ensure sections exist in db.sections
    existing_sections = await db.sections.find({}, {"year": 1, "section_name": 1}).to_list(length=None)
    existing_pairs = set((d.get("year"), d.get("section_name")) for d in existing_sections)
    for y, sec, b in needed_sections:
        if (y, sec) not in existing_pairs:
            await db.sections.insert_one({
                "year": y,
                "section_name": sec,
                "branch": b,
                "department": b,
                "is_active": True,
                "created_at": now,
                "updated_at": now,
            })
            existing_pairs.add((y, sec))

    return updated_cnt


def build_year_filter_clause(year: str) -> dict:
    """Match year labels as well as matching batches for the given academic year."""
    y_clean = year.strip()
    label = re.sub(r"[^a-z0-9]", "", y_clean.lower())
    alias_groups = {
        "1st Year": {"1styear", "firstyear", "iyear", "i", "1", "1st"},
        "2nd Year": {"2ndyear", "secondyear", "iiyear", "ii", "2", "2nd"},
        "3rd Year": {"3rdyear", "thirdyear", "iiiyear", "iii", "3", "3rd"},
        "4th Year": {"4thyear", "fourthyear", "ivyear", "iv", "4", "4th"},
        "Graduated": {"graduated", "alumni"},
    }
    now = datetime.now(timezone.utc)
    academic_base = now.year if now.month >= 7 else now.year - 1
    batch_map = {
        "4th Year": [academic_base + 1],
        "3rd Year": [academic_base + 2],
        "2nd Year": [academic_base + 3],
        "1st Year": [academic_base + 4, academic_base + 5],
    }
    for canonical, aliases in alias_groups.items():
        if label == re.sub(r"[^a-z0-9]", "", canonical.lower()) or label in aliases:
            labels = {canonical}
            labels.update({"1st Year", "1st", "First Year", "I Year", "I", "1"} if canonical == "1st Year" else set())
            labels.update({"2nd Year", "2nd", "Second Year", "II Year", "II", "2"} if canonical == "2nd Year" else set())
            labels.update({"3rd Year", "3rd", "Third Year", "III Year", "III", "3"} if canonical == "3rd Year" else set())
            labels.update({"4th Year", "4th", "Fourth Year", "IV Year", "IV", "4"} if canonical == "4th Year" else set())
            labels.update({"Graduated", "Alumni"} if canonical == "Graduated" else set())

            target_batches = batch_map.get(canonical, [])
            or_clauses = [{"year": {"$in": sorted(labels)}}]
            for b in target_batches:
                or_clauses.extend([{"batch": b}, {"batch": str(b)}])
            return {"$or": or_clauses} if len(or_clauses) > 1 else or_clauses[0]
    return {"year": y_clean}


def build_students_query(
    year: Optional[str] = None,
    section: Optional[str] = None,
    search: Optional[str] = None,
    branch: Optional[str] = None,
) -> dict:
    clauses: List[dict] = []
    if year and year.upper() != "ALL":
        clauses.append(build_year_filter_clause(year))
    if branch and branch.upper() != "ALL":
        branch_value = re.escape(branch.strip())
        clauses.append({"$or": [
            {"branch": {"$regex": f"^{branch_value}$", "$options": "i"}},
            {"department": {"$regex": f"^{branch_value}$", "$options": "i"}},
        ]})
    if section and section.upper() != "ALL":
        sec_clean = section.strip().upper()
        label = sec_clean.rsplit("-", 1)[-1]
        clauses.append({"$or": [
            {"section": sec_clean},
            {"section": {"$regex": f"-{re.escape(label)}$", "$options": "i"}},
        ]})
    if search and search.strip():
        term = re.escape(search.strip())
        clauses.append({"$or": [
            {"name": {"$regex": term, "$options": "i"}},
            {"roll_number": {"$regex": term, "$options": "i"}},
        ]})
    if not clauses:
        return {}
    return clauses[0] if len(clauses) == 1 else {"$and": clauses}


async def get_students(
    year: Optional[str] = None,
    section: Optional[str] = None,
    search: Optional[str] = None,
    branch: Optional[str] = None,
    skip: int = 0,
    limit: int = 10000,
) -> List[StudentResponse]:
    db = get_database()
    query = build_students_query(year, section, search, branch)
    cursor = db.students.find(query).skip(max(skip, 0)).limit(min(max(limit, 1), 10000)).sort("roll_number", 1)
    students = []
    async for s in cursor:
        s["_id"] = str(s["_id"])
        if not s.get("batch") and s.get("roll_number"):
            s["batch"] = infer_batch_from_roll(s["roll_number"])
        if s.get("batch"):
            s["year"] = compute_year_from_batch(s["batch"])
        elif not s.get("year"):
            s["year"] = "2nd Year"
        students.append(StudentResponse(**s))
    return students


async def get_students_page(
    *, year: Optional[str] = None, section: Optional[str] = None,
    search: Optional[str] = None, branch: Optional[str] = None,
    page: int = 1, page_size: int = 25,
) -> Dict[str, Any]:
    db = get_database()
    safe_page = max(page, 1)
    safe_size = min(max(page_size, 1), 200)
    query = build_students_query(year, section, search, branch)
    total = await db.students.count_documents(query)
    items = await get_students(
        year=year, section=section, search=search, branch=branch,
        skip=(safe_page - 1) * safe_size, limit=safe_size,
    )
    return {
        "items": items,
        "total": total,
        "page": safe_page,
        "page_size": safe_size,
        "total_pages": (total + safe_size - 1) // safe_size,
    }


def _build_student_query(student_id: str) -> dict:
    student_id_clean = student_id.strip()
    clauses = [{"_id": student_id_clean}, {"roll_number": student_id_clean.upper()}]
    if ObjectId.is_valid(student_id_clean):
        clauses.append({"_id": ObjectId(student_id_clean)})
    return {"$or": clauses}


async def update_student(student_id: str, data: StudentUpdate, actor_id: Optional[str] = None) -> StudentResponse:
    if not student_id or not student_id.strip():
        raise HTTPException(status_code=400, detail="Student ID is required.")

    db = get_database()
    s = await db.students.find_one(_build_student_query(student_id))
    if not s:
        raise HTTPException(status_code=404, detail="Student not found.")

    doc_id = s["_id"]

    updates = {}
    if data.name is not None:
        updates["name"] = data.name.strip()
    if data.batch is not None:
        updates["batch"] = data.batch
        updates["year"] = compute_year_from_batch(data.batch)
    elif data.year is not None:
        updates["year"] = data.year.strip()
    if data.branch is not None:
        updates["branch"] = data.branch.strip().upper()
    if data.section is not None or data.year is not None or data.branch is not None or data.batch is not None:
        updates["section"] = normalize_student_section(
            data.section if data.section is not None else s.get("section", "A"),
            updates.get("year", s.get("year") or "2nd Year"),
            updates.get("branch", s.get("branch") or "CSE"),
        )
    if data.student_phone is not None:
        updates["student_phone"] = data.student_phone.strip() if data.student_phone else None
    if data.parent_phone is not None:
        updates["parent_phone"] = data.parent_phone.strip() if data.parent_phone else None

    if data.roll_number is not None:
        roll_clean = data.roll_number.strip().upper()
        existing = await db.students.find_one({"roll_number": roll_clean, "_id": {"$ne": doc_id}})
        if existing:
            raise HTTPException(status_code=400, detail=f"Roll number '{roll_clean}' is already in use.")
        updates["roll_number"] = roll_clean
        if data.batch is None and not s.get("batch"):
            inferred_b = infer_batch_from_roll(roll_clean)
            if inferred_b:
                updates["batch"] = inferred_b
                updates["year"] = compute_year_from_batch(inferred_b)

    target_year = updates.get("year", s.get("year", "2nd Year"))
    target_sec = updates.get("section", s.get("section", "A"))
    crlr_id, crlr_name = await find_crlr_for_student(db, target_year, target_sec)
    updates["crlr_id"] = crlr_id
    updates["crlr_name"] = crlr_name

    updates["updated_at"] = datetime.now(timezone.utc)

    await db.students.update_one({"_id": doc_id}, {"$set": updates})
    updated_doc = await db.students.find_one({"_id": doc_id})
    updated_doc["_id"] = str(updated_doc["_id"])

    if actor_id:
        await db.audit_logs.insert_one({
            "actor_id": actor_id,
            "action": "UPDATE_STUDENT",
            "target_student_id": str(doc_id),
            "created_at": datetime.now(timezone.utc),
        })

    return StudentResponse(**updated_doc)


async def delete_student(student_id: str, actor_id: Optional[str] = None):
    if not student_id or not student_id.strip():
        raise HTTPException(status_code=400, detail="Student ID is required.")

    db = get_database()
    s = await db.students.find_one(_build_student_query(student_id))
    if not s:
        raise HTTPException(status_code=404, detail="Student not found.")

    doc_id = s["_id"]
    await db.students.delete_one({"_id": doc_id})

    if actor_id:
        await db.audit_logs.insert_one({
            "actor_id": actor_id,
            "action": "DELETE_STUDENT",
            "target_student_id": str(doc_id),
            "created_at": datetime.now(timezone.utc),
        })


async def delete_all_students(actor_id: Optional[str] = None) -> int:
    db = get_database()
    res = await db.students.delete_many({})
    if actor_id:
        await db.audit_logs.insert_one({
            "actor_id": actor_id,
            "action": "RESET_STUDENTS",
            "metadata": {"deleted_count": res.deleted_count},
            "created_at": datetime.now(timezone.utc),
        })
    return res.deleted_count

