
from datetime import date

import pytest

from app import create_app, db
from app.models import (
    User,
    Goal,
    Activity,
    ActivityTargetVersion,
)


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setenv("TRUST_PROXY", "false")

    application = create_app({
        "TESTING": True,
        "SECRET_KEY": "goal-tracker-test-key",
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        "WTF_CSRF_ENABLED": False,
        "SESSION_COOKIE_SECURE": False,
        "RATELIMIT_ENABLED": False,
        "RATELIMIT_STORAGE_URI": "memory://",
    })

    with application.app_context():
        assert db.engine.url.get_backend_name() == "sqlite"
        assert db.engine.url.database == ":memory:"

        db.create_all()

    yield application

    with application.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


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


@pytest.fixture
def daily_activity(app, weekly_activity):
    with app.app_context():
        activity = db.session.get(
            Activity, weekly_activity
        )

        activity.title = "Reading Books"
        activity.frequency = "daily"
        activity.measurement_type = "numeric"
        activity.target_value = 10
        activity.unit = "pages"

        version = activity.target_versions[0]

        version.frequency = "daily"
        version.measurement_type = "numeric"
        version.target_value = 10
        version.unit = "pages"

        db.session.commit()

    return weekly_activity
