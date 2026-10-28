import re
from datetime import datetime, timezone

from app.db.mongodb import get_database


def _year_key(value: str):
    token = re.sub(r"[^a-z0-9]", "", (value or "").lower())
    if token.startswith(("4", "iv", "fourth")): return "4th Year"
    if token.startswith(("3", "iii", "third")): return "3rd Year"
    if token.startswith(("2", "ii", "second")): return "2nd Year"
    if token.startswith(("1", "i", "first")): return "1st Year"
    return None


def _identity(year: str, branch: str, name: str):
    clean_name = (name or "").strip().upper()
    parts = clean_name.split("-")
    if len(parts) >= 3 and parts[0] in {"I", "II", "III", "IV"}:
        branch = parts[1]
    return (_year_key(year), (branch or "CSE").strip().upper(), parts[-1] if parts else "")


async def reconcile_sections_with_timetables() -> dict:
    """Keep exactly one section record for each section present in timetables."""
    db = get_database()
    timetable_rows = await db.timetables.find({}, {"year": 1, "section": 1}).to_list(length=20000)
    inventory = {}
    for row in timetable_rows:
        identity = _identity(row.get("year", ""), "CSE", row.get("section", ""))
        if not identity[0] or not identity[2]:
            continue
        inventory.setdefault(identity, {
            "year": identity[0],
            "branch": identity[1],
            "section_name": str(row.get("section") or "").strip().upper(),
        })

    docs = await db.sections.find({}).to_list(length=20000)
    groups = {key: [] for key in inventory}
    stale_ids = []
    for doc in docs:
        key = _identity(doc.get("year", ""), doc.get("branch") or doc.get("department") or "CSE", doc.get("section_name") or "")
        if key in groups:
            groups[key].append(doc)
        else:
            stale_ids.append(doc["_id"])

    stale_deactivated = 0
    duplicates_merged = 0
    if stale_ids:
        result = await db.sections.update_many(
            {"_id": {"$in": stale_ids}},
            {"$set": {
                "is_active": False,
                "deactivated_reason": "Section is absent from the current timetable inventory.",
                "updated_at": datetime.now(timezone.utc),
            }},
        )
        stale_deactivated += result.modified_count
    updated = 0
    now = datetime.now(timezone.utc)
    for key, section in inventory.items():
        matches = groups[key]
        if not matches:
            inserted = await db.sections.insert_one({
                **section,
                "is_active": True,
                "assigned_cr_id": None,
                "assigned_lr_id": None,
                "created_at": now,
                "updated_at": now,
            })
            for role, id_field, name_field in (("CR", "assigned_cr_id", "cr_name"), ("LR", "assigned_lr_id", "lr_name")):
                representative = await db.users.find_one({"role": role, "year": section["year"], "section": section["section_name"]})
                if representative:
                    await db.sections.update_one(
                        {"_id": inserted.inserted_id},
                        {"$set": {id_field: str(representative["_id"]), name_field: representative.get("name"), "updated_at": now}},
                    )
            updated += 1
            continue
        canonical_name = section["section_name"]
        matches.sort(key=lambda d: (
            d.get("section_name", "").strip().upper() != canonical_name,
            not bool(d.get("assigned_cr_id") or d.get("assigned_lr_id")),
            str(d.get("_id")),
        ))
        keeper = matches[0]
        updates = {
            "year": section["year"],
            "branch": section["branch"],
            "department": section["branch"],
            "section_name": canonical_name,
            "updated_at": now,
        }
        for field in ("assigned_cr_id", "cr_name", "assigned_lr_id", "lr_name"):
            if not keeper.get(field):
                source = next((m.get(field) for m in matches[1:] if m.get(field)), None)
                if source:
                    updates[field] = source
        await db.sections.update_one({"_id": keeper["_id"]}, {"$set": updates})
        updated += 1
        duplicate_ids = [m["_id"] for m in matches[1:]]
        if duplicate_ids:
            result = await db.sections.delete_many({"_id": {"$in": duplicate_ids}})
            # Duplicate section documents are only removed after their assignments
            # have been merged into the canonical document above.
            duplicates_merged += result.deleted_count

        # Keep representative account assignments aligned to the canonical section.
        aliases = list({canonical_name, f"{section['branch']}-{key[2]}", key[2]})
        await db.users.update_many(
            {"role": {"$in": ["CR", "LR"]}, "year": section["year"], "section": {"$in": aliases}},
            {"$set": {"section": canonical_name, "updated_at": now}},
        )
        for role, id_field, name_field in (("CR", "assigned_cr_id", "cr_name"), ("LR", "assigned_lr_id", "lr_name")):
            representative = await db.users.find_one({
                "role": role,
                "year": section["year"],
                "section": canonical_name,
            })
            if representative and not keeper.get(id_field):
                await db.sections.update_one(
                    {"_id": keeper["_id"]},
                    {"$set": {id_field: str(representative["_id"]), name_field: representative.get("name"), "updated_at": now}},
                )
    try:
        await db.sections.create_index([("section_name", 1)], unique=True)
    except Exception:
        pass
    return {
        "timetable_sections": len(inventory),
        "sections_updated": updated,
        "stale_sections_deactivated": stale_deactivated,
        "duplicate_sections_merged": duplicates_merged,
    }
