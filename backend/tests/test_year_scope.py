import pytest
from fastapi import HTTPException

from app.core.dependencies import enforce_assigned_branch, enforce_assigned_year, get_assigned_years


def test_hod_can_have_multiple_assigned_years():
    hod = {"role": "ADMIN", "branch": "ENG", "department": "CSE", "academic_years": ["2nd Year", "3rd Year"]}
    assert get_assigned_years(hod) == ["2nd Year", "3rd Year"]
    assert enforce_assigned_year(hod, "3rd Year") == "3rd Year"
    assert enforce_assigned_branch(hod, "ENG") == "ENG"


def test_hod_direct_requests_for_unassigned_year_are_forbidden():
    hod = {"role": "ADMIN", "branch": "ENG", "department": "CSE", "academic_years": ["1st Year"]}
    with pytest.raises(HTTPException) as error:
        enforce_assigned_year(hod, "4th Year")
    assert error.value.status_code == 403


def test_hod_with_no_year_assignment_is_denied():
    with pytest.raises(HTTPException) as error:
        enforce_assigned_year({"role": "ADMIN", "branch": "ENG"}, None)
    assert error.value.status_code == 403


def test_superadmin_is_not_limited_to_one_branch_or_year():
    admin = {"role": "SUPER_ADMIN"}
    assert enforce_assigned_branch(admin, "ECE") == "ECE"
    assert enforce_assigned_year(admin, "4th Year") == "4th Year"
