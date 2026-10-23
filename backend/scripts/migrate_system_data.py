import sys
import os
import json
from datetime import datetime, timezone

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.security import hash_password

def migrate_db_store():
    json_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "db_store.json"))
    if not os.path.exists(json_path):
        print("db_store.json not found at", json_path)
        return

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 1. Update Mentors
    users = data.get("users", [])
    mentor_default_hash = hash_password("mentor@1234")
    updated_mentors = 0

    for u in users:
        if u.get("role") == "MENTOR":
            m_id = str(u.get("mentor_id") or u.get("employee_id") or "").strip()
            if not m_id and u.get("email"):
                m_id = u["email"].split("@")[0].upper()
            u["mentor_id"] = m_id
            u["employee_id"] = m_id
            u["roll_number"] = m_id
            u["password_hash"] = mentor_default_hash
            updated_mentors += 1

    print(f"Updated {updated_mentors} mentors with employee_id and password_hash for 'mentor@1234'.")

    # 2. Update Sessions: auto-marked absent -> CRLR Not Marked
    sessions = data.get("sessions", [])
    updated_sessions = 0
    for s in sessions:
        if s.get("auto_marked_absent") or s.get("auto_absence_reason") == "Automatically marked absent after session completion":
            s["faculty_response"] = "CR/LR Not Marked"
            s["session_status"] = "Expired"
            s["auto_marked_absent"] = False
            s["crlr_not_marked"] = True
            s["auto_absence_reason"] = "CR/LR has not marked the attendance for the faculty within scheduled time slot"
            updated_sessions += 1

    print(f"Updated {updated_sessions} sessions to 'CR/LR Not Marked'.")

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print("db_store.json successfully updated and saved.")

if __name__ == "__main__":
    migrate_db_store()
