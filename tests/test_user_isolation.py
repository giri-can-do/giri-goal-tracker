
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
def other_activity(app, weekly_activity):
    with app.app_context():
        user = User(
            username="other_user",
            email="other@example.com",
        )
        user.set_password("other-password")

        goal = Goal(
            user=user,
            title="Read Books",
            goal_type="habit",
            start_date=date(2026, 11, 23),
            status="active",
        )

        activity = Activity(
            goal=goal,
            title="Private Reading Activity",
            measurement_type="numeric",
            frequency="weekly",
            target_value=100,
            unit="pages",
            start_date=date(2026, 11, 23),
            is_active=True,
        )

        activity.target_versions.append(
            ActivityTargetVersion(
                effective_from=date(2026, 11, 23),
                frequency="weekly",
                measurement_type="numeric",
                target_value=100,
                unit="pages",
            )
        )

        db.session.add(user)
        db.session.commit()

        return activity.id

# Prevent unauthorized check-ins


def test_cannot_check_in_other_users_activity(
    app, client, other_activity, monkeypatch
):
    import app.today as today_module

    monkeypatch.setattr(
        today_module,
        "tokyo_today",
        lambda: date(2026, 11, 25),
    )

    response = client.post(
        f"/activities/{other_activity}/check-in",
        data={"value": "50"},
    )

    assert response.status_code == 404

    with app.app_context():
        count = DailyEntry.query.filter_by(
            activity_id=other_activity
        ).count()

        assert count == 0

# Prevent unauthorized target editing


def test_cannot_edit_other_users_activity(
    app, client, other_activity, monkeypatch
):
    import app.goals as goals_module

    monkeypatch.setattr(
        goals_module,
        "tokyo_today",
        lambda: date(2026, 11, 25),
    )

    response = client.post(
        f"/goals/activities/{other_activity}/edit",
        data={
            "title": "Unauthorized Change",
            "start_date": "2026-11-23",
            "measurement_type": "numeric",
            "frequency": "weekly",
            "target_value": "999",
            "unit": "pages",
        },
    )

    assert response.status_code == 404

    with app.app_context():
        activity = db.session.get(
            Activity, other_activity
        )

        assert activity.title == "Private Reading Activity"
        assert activity.target_value == 100
        assert len(activity.target_versions) == 1

# Prevent Dashboard data leakage


def test_dashboard_only_shows_own_activities(
    app, client, other_activity, monkeypatch
):
    import app.dashboard as dashboard_module

    monkeypatch.setattr(
        dashboard_module,
        "tokyo_today",
        lambda: date(2026, 11, 25),
    )

    monkeypatch.setattr(
        dashboard_module,
        "render_template",
        lambda template, **context: context,
    )

    response = client.get("/dashboard/")

    assert response.status_code == 200

    reports = response.get_json()["reports"]

    for period in ["week", "month", "year"]:
        titles = [
            row["title"]
            for row in reports[period]
        ]

        assert "Japanese Study" in titles
        assert "Private Reading Activity" not in titles
        assert len(titles) == 1


# Protect routes from unauthenticated users

@pytest.mark.parametrize(
    "path",
    ["/", "/dashboard/", "/goals/"],
)
def test_anonymous_user_requires_login(client, path):
    response = client.get(
        path,
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]

