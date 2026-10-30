import pytest
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from httpx import AsyncClient
from app.core.security import hash_password, verify_password
from app.db.mongodb import get_database
from app.schemas.user import UserRole
from app.services.auth_service import reset_password
from fastapi import HTTPException


@pytest.mark.asyncio
async def test_valid_admin_and_crlr_login(client: AsyncClient):
    db = get_database()
    pass_hash = hash_password("secret123")

    # Create admin and CR user
    await db.users.insert_one({
        "name": "Admin Test",
        "email": "admin@test.com",
        "password_hash": pass_hash,
        "role": UserRole.ADMIN.value,
        "is_active": True,
    })
    await db.users.insert_one({
        "name": "CR Test",
        "email": "cr@test.com",
        "password_hash": pass_hash,
        "role": UserRole.CR.value,
        "section": "II-A",
        "year": "2nd Year",
        "is_active": True,
    })

    # Test Admin Login
    res = await client.post("/api/auth/login", json={"email": "admin@test.com", "password": "secret123", "portal": "ADMIN"})
    assert res.status_code == 200
    json_data = res.json()
    assert json_data["success"] is True
    assert json_data["data"]["user"]["role"] == "ADMIN"
    assert "access_token" in json_data["data"]

    # Test CR Login
    res2 = await client.post("/api/auth/login", json={"email": "cr@test.com", "password": "secret123", "portal": "CRLR"})
    assert res2.status_code == 200
    json2 = res2.json()
    assert json2["data"]["user"]["role"] == "CR"
    assert json2["data"]["user"]["section"] == "II-A"


@pytest.mark.asyncio
async def test_invalid_password_returns_401(client: AsyncClient):
    db = get_database()
    await db.users.insert_one({
        "name": "User Test",
        "email": "user@test.com",
        "password_hash": hash_password("secret123"),
        "role": UserRole.CR.value,
        "is_active": True,
    })

    res = await client.post("/api/auth/login", json={"email": "user@test.com", "password": "wrongpassword"})
    assert res.status_code == 401
    assert res.json()["success"] is False


@pytest.mark.asyncio
async def test_forgot_password_route_is_registered_and_enumeration_safe(client: AsyncClient, monkeypatch):
    from app.services import auth_service

    async def brevo_ready():
        return True

    monkeypatch.setattr(auth_service, "diagnose_brevo_configuration", brevo_ready)
    res = await client.post("/api/auth/forgot-password", json={"email": "unregistered@example.com"})
    assert res.status_code == 200
    assert "If an account exists" in res.json()["message"]


@pytest.mark.asyncio
async def test_inactive_user_login_fails(client: AsyncClient):
    db = get_database()
    await db.users.insert_one({
        "name": "Disabled User",
        "email": "disabled@test.com",
        "password_hash": hash_password("secret123"),
        "role": UserRole.CR.value,
        "is_active": False,
    })

    res = await client.post("/api/auth/login", json={"email": "disabled@test.com", "password": "secret123"})
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_portal_mismatch_returns_403(client: AsyncClient):
    db = get_database()
    await db.users.insert_one({
        "name": "CR User",
        "email": "cruser@test.com",
        "password_hash": hash_password("secret123"),
        "role": UserRole.CR.value,
        "is_active": True,
    })

    # CR attempting to login via ADMIN portal
    res = await client.post("/api/auth/login", json={"email": "cruser@test.com", "password": "secret123", "portal": "ADMIN"})
    assert res.status_code == 403


@pytest.mark.asyncio
@pytest.mark.parametrize("role", ["ADMIN", "MENTOR", "CR", "LR"])
async def test_password_reset_is_hashed_one_time_and_updates_account(role: str):
    db = get_database()
    user_id = await db.users.insert_one({
        "name": "Reset Test", "email": f"reset-{role.lower()}@test.com",
        "password_hash": hash_password("Oldpass123"), "role": role, "is_active": True,
    })
    token = secrets.token_urlsafe(40)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    await db.password_reset_tokens.insert_one({
        "user_id": str(user_id.inserted_id), "role": role, "token_hash": token_hash,
        "created_at": datetime.now(timezone.utc), "expires_at": datetime.now(timezone.utc) + timedelta(minutes=20), "used_at": None,
    })
    await reset_password(token, "Newpass123")
    updated = await db.users.find_one({"_id": user_id.inserted_id})
    assert verify_password("Newpass123", updated["password_hash"])
    assert not verify_password("Oldpass123", updated["password_hash"])
    stored_token = await db.password_reset_tokens.find_one({"token_hash": token_hash})
    assert stored_token["used_at"] is not None
    with pytest.raises(HTTPException) as exc:
        await reset_password(token, "Againpass123")
    assert exc.value.status_code == 400


@pytest.mark.asyncio
@pytest.mark.parametrize("role", ["ADMIN", "MENTOR", "CR", "LR"])
async def test_brevo_reset_request_stores_only_token_hash(role: str, monkeypatch):
    from app.core.config import settings
    from app.services import auth_service

    db = get_database()
    email = f"mail-{role.lower()}@test.com"
    await db.users.insert_one({"name": "Mail Test", "email": email, "role": role, "is_active": True})
    monkeypatch.setattr(settings, "BREVO_API_KEY", "test-key")
    monkeypatch.setattr(settings, "BREVO_SENDER_MAIL", "verified@example.com")
    monkeypatch.setattr(settings, "FRONTEND_URL", "https://session-monitoring-system.vercel.app")
    captured = []

    async def skip_diagnostics():
        return True

    monkeypatch.setattr(auth_service, "diagnose_brevo_configuration", skip_diagnostics)

    class FakeResponse:
        status_code = 201
        def raise_for_status(self):
            return None

    class FakeClient:
        def __init__(self, *args, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): return None
        async def post(self, url, json, headers):
            captured.append((url, json, headers))
            return FakeResponse()

    monkeypatch.setattr(auth_service.httpx, "AsyncClient", FakeClient)
    await auth_service.request_password_reset(email)
    assert captured[0][0] == "https://api.brevo.com/v3/smtp/email"
    assert captured[0][2]["api-key"] == "test-key"
    assert captured[0][1]["subject"] == "Password Reset Request — College Session Monitoring System"
    assert "Reset Password" in captured[0][1]["htmlContent"]
    assert "College Session Monitoring System" in captured[0][1]["htmlContent"]
    assert "localhost" not in captured[0][1]["textContent"]
    reset_link = next(line for line in captured[0][1]["textContent"].splitlines() if "/reset-password?token=" in line)
    token = reset_link.split("token=", 1)[1]
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    record = await db.password_reset_tokens.find_one({"token_hash": token_hash})
    assert record["role"] == role
    assert token not in str(record)
    assert await auth_service.verify_password_reset_token(token) == role


def test_render_reset_url_never_points_to_localhost(monkeypatch):
    from app.core.config import settings
    from app.services.auth_service import PRODUCTION_FRONTEND_URL, _reset_frontend_url

    monkeypatch.setattr(settings, "FRONTEND_URL", "http://localhost:5173")
    monkeypatch.setenv("RENDER", "true")
    assert _reset_frontend_url() == PRODUCTION_FRONTEND_URL


@pytest.mark.asyncio
async def test_brevo_diagnostics_logs_status_without_secret_or_sender(monkeypatch, caplog):
    from app.core.config import settings
    from app.services import auth_service

    monkeypatch.setattr(settings, "BREVO_API_KEY", "test-brevo-api-key")
    monkeypatch.setattr(settings, "BREVO_SENDER_MAIL", "private-sender@example.com")
    monkeypatch.setattr(settings, "FRONTEND_URL", "https://session-monitoring-system.vercel.app")
    monkeypatch.setattr(auth_service, "_brevo_diagnostics_checked", False)
    requests = []

    class FakeResponse:
        status_code = 200
        def json(self):
            return {"senders": [{"email": "private-sender@example.com", "active": True}]}

    class FakeClient:
        def __init__(self, *args, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): return None
        async def get(self, url, headers):
            requests.append((url, headers))
            return FakeResponse()

    monkeypatch.setattr(auth_service.httpx, "AsyncClient", FakeClient)
    assert await auth_service.diagnose_brevo_configuration() is True

    assert [url for url, _ in requests] == [
        "https://api.brevo.com/v3/account",
        "https://api.brevo.com/v3/senders",
    ]
    assert all(headers["api-key"] == "test-brevo-api-key" for _, headers in requests)
    assert "api_key_present=True" in caplog.text
    assert "key_kind=unknown_prefix" in caplog.text
    assert "Configured Brevo sender is listed as active: True" in caplog.text
    assert "test-brevo-api-key" not in caplog.text
    assert "private-sender@example.com" not in caplog.text


@pytest.mark.asyncio
async def test_forgot_password_fails_closed_when_brevo_is_unavailable(monkeypatch):
    from app.services import auth_service

    async def brevo_unavailable():
        return False

    monkeypatch.setattr(auth_service, "diagnose_brevo_configuration", brevo_unavailable)
    with pytest.raises(HTTPException) as exc:
        await auth_service.request_password_reset("any-address@example.com")
    assert exc.value.status_code == 503
    assert "temporarily unavailable" in exc.value.detail


@pytest.mark.asyncio
async def test_brevo_rejection_returns_unavailable_and_invalidates_reset_token(monkeypatch):
    from app.services import auth_service

    db = get_database()
    email = "brevo-rejected@test.com"
    user = await db.users.insert_one({
        "name": "Brevo Rejected", "email": email, "role": UserRole.ADMIN.value, "is_active": True,
    })

    async def brevo_ready():
        return True

    monkeypatch.setattr(auth_service, "diagnose_brevo_configuration", brevo_ready)

    class FakeResponse:
        status_code = 401

        def raise_for_status(self):
            response = auth_service.httpx.Response(
                401,
                request=auth_service.httpx.Request("POST", "https://api.brevo.com/v3/smtp/email"),
            )
            raise auth_service.httpx.HTTPStatusError("rejected", request=response.request, response=response)

    class FakeClient:
        def __init__(self, *args, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): return None
        async def post(self, *args, **kwargs): return FakeResponse()

    monkeypatch.setattr(auth_service.httpx, "AsyncClient", FakeClient)
    with pytest.raises(HTTPException) as exc:
        await auth_service.request_password_reset(email)
    assert exc.value.status_code == 503

    tokens = await db.password_reset_tokens.find({"user_id": str(user.inserted_id)}).to_list(length=10)
    assert len(tokens) == 1
    assert tokens[0]["used_at"] is not None
