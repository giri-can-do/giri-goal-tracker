
from datetime import date

import pytest

from app import db
from app.models import (
    User,
    Goal,
    Activity,
    DailyEntry,
    ActivityTargetVersion,
)

@pytest.fixture
def weekly_activity(app, client):
    with app.app_context():
        user = User(
            username="test_user",
            email="test@example.com",
        )
        user.set_password("test-password")

        goal = Goal(
            user=user,
            title="Learn Japanese",
            goal_type="habit",
            start_date=date(2026, 11, 23),
            status="active",
        )

        activity = Activity(
            goal=goal,
            title="Japanese Study",
            measurement_type="duration",
            frequency="weekly",
            target_value=180,
            unit="minutes",
            start_date=date(2026, 11, 23),
            is_active=True,
        )

        activity.target_versions.append(
            ActivityTargetVersion(
                effective_from=date(2026, 11, 23),
                frequency="weekly",
                measurement_type="duration",
                target_value=180,
                unit="minutes",
            )
        )

        db.session.add(user)
        db.session.commit()

        user_id = user.id
        activity_id = activity.id

    with client.session_transaction() as session:
        session["_user_id"] = str(user_id)
        session["_fresh"] = True

    return activity_id

# Test weekly check-ins

def test_weekly_progress_accumulation(
    app, client, weekly_activity, monkeypatch
):
    import app.today as today_module

    sessions = [
        (date(2026, 11, 23), 30),
        (date(2026, 11, 25), 60),
        (date(2026, 11, 27), 90),
    ]

    for day, value in sessions:
        monkeypatch.setattr(
            today_module,
            "tokyo_today",
            lambda day=day: day,
        )

        response = client.post(
            f"/activities/{weekly_activity}/check-in",
            data={"value": str(value)},
        )

        assert response.status_code == 302

    with app.app_context():
        entries = DailyEntry.query.filter_by(
            activity_id=weekly_activity
        ).all()

        assert len(entries) == 3
        assert sum(entry.value for entry in entries) == 180

# Test same-day replacement

def test_same_day_check_in_replaces_value(
    app, client, weekly_activity, monkeypatch
):
    import app.today as today_module

    monkeypatch.setattr(
        today_module,
        "tokyo_today",
        lambda: date(2026, 11, 25),
    )

    for value in [30, 50]:
        response = client.post(
            f"/activities/{weekly_activity}/check-in",
            data={"value": str(value)},
        )

        assert response.status_code == 302

    with app.app_context():
        entries = DailyEntry.query.filter_by(
            activity_id=weekly_activity
        ).all()

        assert len(entries) == 1
        assert entries[0].value == 50

# Reject invalid progress values

@pytest.mark.parametrize(
    "invalid_value",
    ["-10", "abc", "nan", "inf"],
)
def test_invalid_progress_is_rejected(
    app, client, weekly_activity,
    monkeypatch, invalid_value
):
    import app.today as today_module

    monkeypatch.setattr(
        today_module,
        "tokyo_today",
        lambda: date(2026, 11, 25),
    )

    response = client.post(
        f"/activities/{weekly_activity}/check-in",
        data={"value": invalid_value},
    )

    assert response.status_code == 302

    with app.app_context():
        count = DailyEntry.query.filter_by(
            activity_id=weekly_activity
        ).count()

        assert count == 0
