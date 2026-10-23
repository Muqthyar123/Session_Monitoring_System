import asyncio
from app.db.mongodb import connect_to_mongo, get_database
from app.schemas.auth import LoginRequest
from app.services.auth_service import authenticate_user

async def main():
    await connect_to_mongo()
    test_ids = ["605101", "705201", "905101", "1005201", "1105101"]
    for eid in test_ids:
        try:
            req = LoginRequest(email=eid, password="mentor@1234", portal="MENTOR")
            resp = await authenticate_user(req)
            print(f"PASS: Mentor {eid} ({resp.user.name}) logged in successfully. Role: {resp.user.role}")
        except Exception as e:
            print(f"FAIL: Mentor {eid} failed with {e}")

if __name__ == "__main__":
    asyncio.run(main())
