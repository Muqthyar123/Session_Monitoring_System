from uuid import uuid4
import pytest
from pydantic import ValidationError

from app.schemas.user import UserRole
from app.schemas.site import SiteCreate, SiteUpdate, SiteResponse
from app.schemas.branch import BranchCreate, BranchUpdate, BranchResponse
from app.schemas.hod import HODCreate, HODUpdate, HODResponse
from app.core.dependencies import get_branch_filter
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from fastapi import HTTPException


def test_super_admin_role_enum():
    """Verify SUPER_ADMIN is a recognized UserRole enum value."""
    assert UserRole.SUPER_ADMIN.value == "SUPER_ADMIN"
    assert "SUPER_ADMIN" in [r.value for r in UserRole]


def test_site_schemas():
    """Verify Site validation schema."""
    site = SiteCreate(
        code="HYD_MAIN",
        name="Hyderabad Main Campus",
        location="Hyderabad",
        address="Survey No. 123",
        contactEmail="admin@campus.edu",
        contactPhone="+919876543210",
        description="Main college campus",
        isActive=True,
    )
    assert site.code == "HYD_MAIN"
    assert site.name == "Hyderabad Main Campus"
    assert site.is_active is True

    # Code and name are required
    with pytest.raises(ValidationError):
        SiteCreate(code="", name="")


def test_branch_schemas():
    """Verify Branch validation schema."""
    branch = BranchCreate(
        code="CSE",
        name="Computer Science and Engineering",
        siteId="site-123",
        siteName="Hyderabad Main Campus",
        description="Core computing department",
        isActive=True,
    )
    assert branch.code == "CSE"
    assert branch.name == "Computer Science and Engineering"
    assert branch.site_id == "site-123"
    assert branch.is_active is True

    # Code and name required
    with pytest.raises(ValidationError):
        BranchCreate(code="", name="")


def test_hod_schemas():
    """Verify HOD creation schema."""
    hod = HODCreate(
        name="Dr. Ramanathan",
        email="hod.cse@college.edu",
        phone="+919876543210",
        branchCode="CSE",
        password="SecurePassword@123",
        isActive=True,
    )
    assert hod.name == "Dr. Ramanathan"
    assert hod.email == "hod.cse@college.edu"
    assert hod.branch_code == "CSE"
    assert hod.password == "SecurePassword@123"

    # Password length must be at least 6 characters
    with pytest.raises(ValidationError):
        HODCreate(
            name="Dr. Short",
            email="short@college.edu",
            branchCode="CSE",
            password="123",
        )


def test_jwt_token_includes_branch():
    """Verify JWT token payload preserves branch information."""
    token = create_access_token({
        "sub": "user-123",
        "email": "hod.cse@college.edu",
        "role": "ADMIN",
        "branch": "CSE",
        "branch_id": "branch-uuid-456",
    })
    payload = decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == "user-123"
    assert payload["role"] == "ADMIN"
    assert payload["branch"] == "CSE"
    assert payload["branch_id"] == "branch-uuid-456"


def test_branch_filter_enforcement_super_admin():
    """Super Admin can access any requested branch, or all branches when omitted."""
    super_admin_user = {
        "role": "SUPER_ADMIN",
        "email": "superadmin@college.edu",
    }
    # When requesting all branches (requested_branch=None) -> returns None (no branch filter)
    assert get_branch_filter(super_admin_user, None) is None

    # When requesting specific branch CSE -> returns "CSE"
    assert get_branch_filter(super_admin_user, "CSE") == "CSE"
    assert get_branch_filter(super_admin_user, "ECE") == "ECE"


def test_branch_filter_enforcement_branch_hod():
    """Branch HOD (ADMIN with assigned branch) is strictly locked to their branch."""
    hod_user = {
        "role": "ADMIN",
        "email": "hod.cse@college.edu",
        "branch": "CSE",
        "branch_id": "b-cse",
    }
    # When requesting None -> scoped to "CSE"
    assert get_branch_filter(hod_user, None) == "CSE"

    # When requesting their own branch "CSE" -> allowed
    assert get_branch_filter(hod_user, "CSE") == "CSE"

    # When attempting URL parameter tampering to access "ECE" -> blocked with 403 Forbidden!
    with pytest.raises(HTTPException) as exc_info:
        get_branch_filter(hod_user, "ECE")
    assert exc_info.value.status_code == 403
    assert "restricted to your assigned branch" in exc_info.value.detail


def test_password_hashing_security():
    """Verify secure bcrypt password hashing and verification."""
    raw_pwd = "SuperSecretPassword@2026"
    hashed = hash_password(raw_pwd)
    assert hashed != raw_pwd
    assert hashed.startswith("$2")  # bcrypt hash format
    assert verify_password(raw_pwd, hashed) is True
    assert verify_password("WrongPassword@2026", hashed) is False
