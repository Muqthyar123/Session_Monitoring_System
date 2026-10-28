import io
from datetime import datetime, timezone

import pytest
from fastapi import HTTPException, UploadFile
from httpx import AsyncClient

from app.core.config import settings
from app.core.security import create_access_token
from app.db.mongodb import get_database
from app.schemas.user import UserRole
from app.services.excel_service import _enforce_import_row_limit
from app.api.upload_utils import read_upload_limited


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("DELETE", "/api/admin/students/reset"),
        ("DELETE", "/api/admin/users/reset"),
        ("DELETE", "/api/admin/mentors/reset"),
        ("POST", "/api/admin/timetable/reset"),
        ("DELETE", "/api/admin/timetable"),
    ],
)
async def test_data_resets_require_authentication(client: AsyncClient, method, path):
    response = await client.request(method, path)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_upload_file_size_is_bounded(monkeypatch):
    monkeypatch.setattr(settings, "MAX_UPLOAD_SIZE_MB", 1)
    upload = UploadFile(filename="too-large.csv", file=io.BytesIO(b"x" * (1024 * 1024 + 1)))
    with pytest.raises(HTTPException) as exc:
        await read_upload_limited(upload)
    assert exc.value.status_code == 413


def test_import_row_limit_is_enforced(monkeypatch):
    monkeypatch.setattr(settings, "MAX_IMPORT_ROWS", 4)
    with pytest.raises(ValueError, match="limit is 4"):
        _enforce_import_row_limit(5)


@pytest.mark.asyncio
async def test_upload_history_is_persisted_and_admin_only(client: AsyncClient):
    db = get_database()
    await db.audit_logs.insert_one({
        "actor_id": "uploader-test",
        "action": "IMPORT_STUDENTS_EXCEL",
        "metadata": {"filename": "roster.xlsx", "created": 2, "updated": 1, "failed": 3},
        "created_at": datetime.now(timezone.utc),
    })

    unauthorized = await client.get("/api/admin/uploads/history")
    assert unauthorized.status_code == 401

    admin = await db.users.insert_one({
        "name": "Upload History Admin",
        "email": "upload-history-admin@example.invalid",
        "role": UserRole.ADMIN.value,
        "is_active": True,
    })
    token = create_access_token({"sub": str(admin.inserted_id), "role": UserRole.ADMIN.value})
    response = await client.get(
        "/api/admin/uploads/history?limit=10",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200, response.text
    history = response.json()["data"]
    record = next(item for item in history if item["metadata"].get("filename") == "roster.xlsx")
    assert record["action"] == "IMPORT_STUDENTS_EXCEL"
    assert record["metadata"]["failed"] == 3
