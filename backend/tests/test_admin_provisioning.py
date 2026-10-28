from uuid import uuid4

import pytest

from app.db.mongodb import get_database
from app.schemas.user import UserRole
from app.services.admin_provisioning import (
    create_first_admin,
    reset_admin_password,
    verify_admin_credentials,
)


@pytest.mark.asyncio
async def test_first_admin_is_hashed_and_duplicate_creation_is_refused():
    db = get_database()
    email = f"first-admin-{uuid4().hex}@example.invalid"
    password = f"{uuid4().hex[:8]}A!"

    assert await create_first_admin(db, email, "First Admin", password) == "created"
    saved = await db.users.find_one({"email": email})
    assert saved["role"] == UserRole.ADMIN.value
    assert saved["password_hash"] != password
    assert await verify_admin_credentials(db, email, password)
    assert not await verify_admin_credentials(db, email, f"wrong-{password}")

    with pytest.raises(ValueError, match="already exists"):
        await create_first_admin(db, email, "Duplicate", password)
    assert await db.users.count_documents({"email": email}) == 1


@pytest.mark.asyncio
async def test_first_admin_refuses_to_add_an_admin_when_one_already_exists():
    db = get_database()
    await db.users.insert_one({"email": f"existing-{uuid4().hex}@example.invalid", "role": "ADMIN"})

    with pytest.raises(ValueError, match="administrator already exists"):
        await create_first_admin(
            db,
            f"new-{uuid4().hex}@example.invalid",
            "Second Admin",
            f"{uuid4().hex[:8]}A!",
        )


@pytest.mark.asyncio
async def test_existing_non_admin_email_is_not_elevated_and_reset_is_explicit():
    db = get_database()
    email = f"account-{uuid4().hex}@example.invalid"
    first_password = f"{uuid4().hex[:8]}A!"
    second_password = f"{uuid4().hex[:8]}B!"
    await db.users.insert_one({"email": email, "role": UserRole.MENTOR.value})

    with pytest.raises(ValueError, match="non-administrator"):
        await create_first_admin(db, email, "Do not elevate", first_password)

    await db.users.delete_one({"email": email})
    await create_first_admin(db, email, "First Admin", first_password)
    await reset_admin_password(db, email, second_password)
    assert not await verify_admin_credentials(db, email, first_password)
    assert await verify_admin_credentials(db, email, second_password)
