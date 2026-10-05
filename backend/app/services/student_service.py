import re
from datetime import datetime, timezone
from typing import Any, List, Optional, Tuple
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
    Computes academic year from batch graduation year:
    - 2027 -> 4th Year
    - 2028 -> 3rd Year
    - 2029 -> 2nd Year
    - 2030 -> 1st Year
    - Future batches calculated using standard formula: diff = 2031 - batch
    """
    if not batch_val:
        return "2nd Year"
    try:
        # Check if 4-digit number (e.g. 2027)
        m = re.search(r'\b(20\d{2})\b', str(batch_val))
        if m:
            b_num = int(m.group(1))
            diff = 2031 - b_num
            if diff == 1:
                return "1st Year"
            elif diff == 2:
                return "2nd Year"
            elif diff == 3:
                return "3rd Year"
            elif diff == 4:
                return "4th Year"
            elif diff > 4:
                return "Graduated"
            elif diff <= 0:
                return "1st Year"

        # Check if 2-digit number (e.g. 27, 28, 29, 30)
        m2 = re.search(r'\b(\d{2})\b', str(batch_val))
        if m2:
            yy = int(m2.group(1))
            if 20 <= yy <= 40:
                b_num = 2000 + yy
                diff = 2031 - b_num
                if diff == 1:
                    return "1st Year"
                elif diff == 2:
                    return "2nd Year"
                elif diff == 3:
                    return "3rd Year"
                elif diff == 4:
                    return "4th Year"
                elif diff > 4:
                    return "Graduated"
                elif diff <= 0:
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


async def find_crlr_for_student(db, year: str, section: str) -> Tuple[Optional[str], Optional[str]]:
    """Finds CR/LR user ID and name for a given year and section."""
    clean_sec = section.strip().upper()
    sec_norm = (
        clean_sec.replace("II-", "")
        .replace("I-", "")
        .replace("III-", "")
        .replace("IV-", "")
        .replace("CSE-", "")
        .replace("SECTION", "")
        .strip()
    )

    user = await db.users.find_one(
        {
            "role": {"$in": ["CR", "LR"]},
            "$or": [
                {"section": section},
                {"section": clean_sec},
                {"section": f"II-CSE-{sec_norm}"},
                {"section": f"CSE-{sec_norm}"},
                {"section": sec_norm},
                {"section": {"$regex": f"{sec_norm}$", "$options": "i"}},
            ],
        }
    )

    if user:
        return str(user["_id"]), user.get("name")

    sec_doc = await db.sections.find_one(
        {
            "$or": [
                {"section_name": section},
                {"section_name": clean_sec},
                {"section_name": f"II-CSE-{sec_norm}"},
                {"section_name": f"CSE-{sec_norm}"},
                {"section_name": sec_norm},
            ]
        }
    )
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

    year = compute_year_from_batch(batch)
    branch = (data.branch or "CSE").strip()
    sec_clean = data.section.strip().upper()

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
    Synchronizes batch and academic year for all students in MongoDB:
    - Roll starting with 23... -> Batch 2027 -> 4th Year
    - Roll starting with 24... -> Batch 2028 -> 3rd Year
    - Roll starting with 25... -> Batch 2029 -> 2nd Year
    - Roll starting with 26... -> Batch 2030 -> 1st Year
    """
    cursor = db.students.find({})
    updated_cnt = 0
    async for s in cursor:
        roll = s.get("roll_number")
        batch = s.get("batch")
        inferred = infer_batch_from_roll(roll) if roll else None
        eff_batch = batch if batch else inferred
        if eff_batch:
            eff_year = compute_year_from_batch(eff_batch)
            if s.get("batch") != eff_batch or s.get("year") != eff_year:
                await db.students.update_one(
                    {"_id": s["_id"]},
                    {"$set": {"batch": eff_batch, "year": eff_year, "updated_at": datetime.now(timezone.utc)}}
                )
                updated_cnt += 1
    return updated_cnt


def build_year_filter_clause(year: str) -> dict:
    """Builds a MongoDB filter clause that matches an academic year by year name, batch, or roll prefix."""
    y_clean = year.strip()
    if "4" in y_clean or "iv" in y_clean.lower():
        target_batch = 2027
        roll_prefix = "23"
        aliases = ["4th Year", "4th", "IV", "IV Year", "4", "IV B.Tech", "IV-Year", "4-Year"]
    elif "3" in y_clean or "iii" in y_clean.lower():
        target_batch = 2028
        roll_prefix = "24"
        aliases = ["3rd Year", "3rd", "III", "III Year", "3", "III B.Tech", "III-Year", "3-Year"]
    elif "2" in y_clean or "ii" in y_clean.lower():
        target_batch = 2029
        roll_prefix = "25"
        aliases = ["2nd Year", "2nd", "II", "II Year", "2", "II B.Tech", "II-Year", "2-Year"]
    elif "1" in y_clean or "i" in y_clean.lower():
        target_batch = 2030
        roll_prefix = "26"
        aliases = ["1st Year", "1st", "I", "I Year", "1", "I B.Tech", "I-Year", "1-Year"]
    else:
        return {"year": y_clean}

    return {
        "$or": [
            {"batch": target_batch},
            {"batch": str(target_batch)},
            {"roll_number": {"$regex": f"^{roll_prefix}", "$options": "i"}},
            {"year": {"$in": aliases}},
        ]
    }


async def get_students(
    year: Optional[str] = None,
    section: Optional[str] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 500,
) -> List[StudentResponse]:
    db = get_database()
    query = {}

    if year and year.upper() != "ALL":
        year_clause = build_year_filter_clause(year)
        if "$or" in query:
            existing_or = query.pop("$or")
            query["$and"] = [{"$or": existing_or}, year_clause]
        elif "$and" in query:
            query["$and"].append(year_clause)
        else:
            query.update(year_clause)

    if section and section.upper() != "ALL":
        sec_clean = section.strip().upper()
        sec_norm = (
            sec_clean.replace("II-", "")
            .replace("I-", "")
            .replace("III-", "")
            .replace("IV-", "")
            .replace("CSE-", "")
            .replace("SECTION", "")
            .strip()
        )
        sec_candidates = [section, sec_clean, sec_norm, f"CSE-{sec_norm}", f"II-CSE-{sec_norm}"]
        sec_clause = {"$or": [{"section": c} for c in set(sec_candidates) if c]}
        if "$and" in query:
            query["$and"].append(sec_clause)
        elif "$or" in query:
            existing_or = query.pop("$or")
            query["$and"] = [{"$or": existing_or}, sec_clause]
        else:
            query.update(sec_clause)

    if search:
        search_clause = [
            {"name": {"$regex": search, "$options": "i"}},
            {"roll_number": {"$regex": search, "$options": "i"}},
            {"section": {"$regex": search, "$options": "i"}},
        ]
        if "$and" in query:
            query["$and"].append({"$or": search_clause})
        elif "$or" in query:
            existing_or = query.pop("$or")
            query["$and"] = [{"$or": existing_or}, {"$or": search_clause}]
        else:
            query["$or"] = search_clause

    cursor = db.students.find(query).skip(skip).limit(limit).sort("roll_number", 1)
    students = []
    target_year = None
    if year and year.upper() != "ALL":
        if "4" in year or "iv" in year.lower():
            target_year = "4th Year"
        elif "3" in year or "iii" in year.lower():
            target_year = "3rd Year"
        elif "2" in year or "ii" in year.lower():
            target_year = "2nd Year"
        elif "1" in year or "i" in year.lower():
            target_year = "1st Year"

    async for s in cursor:
        s["_id"] = str(s["_id"])
        if not s.get("batch") and s.get("roll_number"):
            s["batch"] = infer_batch_from_roll(s["roll_number"])
        if s.get("batch"):
            s["year"] = compute_year_from_batch(s["batch"])
        elif not s.get("year"):
            s["year"] = "2nd Year"

        if target_year and s.get("year") != target_year:
            continue
        students.append(StudentResponse(**s))
    return students


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
        updates["branch"] = data.branch.strip()
    if data.section is not None:
        updates["section"] = data.section.strip().upper()
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

