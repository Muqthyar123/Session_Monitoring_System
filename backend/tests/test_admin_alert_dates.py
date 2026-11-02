from datetime import datetime, timezone

import pytest
from fastapi import HTTPException

from app.api.attendance import _alert_date_query


def test_kolkata_day_filter_uses_utc_midnight_boundaries():
    query = _alert_date_query({}, "2026-11-02", "2026-11-02")
    assert query["created_at"]["$gte"] == datetime(2026, 11, 1, 18, 30, tzinfo=timezone.utc)
    assert query["created_at"]["$lt"] == datetime(2026, 11, 2, 18, 30, tzinfo=timezone.utc)


def test_custom_range_allows_one_sided_dates_and_rejects_reverse_range():
    assert "$gte" in _alert_date_query({}, "2026-11-01", None)["created_at"]
    assert "$lt" in _alert_date_query({}, None, "2026-11-01")["created_at"]
    with pytest.raises(HTTPException) as exc:
        _alert_date_query({}, "2026-11-02", "2026-11-01")
    assert exc.value.status_code == 422
