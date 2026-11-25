
from datetime import date

from app import db
from app.models import Activity


def update_target(client, activity_id, target):
    return client.post(
        f"/goals/activities/{activity_id}/edit",
        data={
            "title": "Japanese Study",
            "start_date": "2026-11-23",
            "measurement_type": "duration",
            "frequency": "weekly",
            "target_value": str(target),
            "unit": "minutes",
        },
    )


def test_weekly_target_edit_effective_next_monday(
    app, client, weekly_activity, monkeypatch
):
    import app.goals as goals_module

    monkeypatch.setattr(
        goals_module,
        "tokyo_today",
        lambda: date(2026, 11, 25),
    )

    response = update_target(
        client, weekly_activity, 300
    )

    assert response.status_code == 302

    with app.app_context():
        activity = db.session.get(
            Activity, weekly_activity
        )

        assert len(activity.target_versions) == 2

        assert activity.target_on(
            date(2026, 11, 25)
        ).target_value == 180

        assert activity.target_on(
            date(2026, 11, 29)
        ).target_value == 180

        assert activity.target_on(
            date(2026, 11, 30)
        ).target_value == 300

        assert activity.target_versions[-1].effective_from == (
            date(2026, 11, 30)
        )

# Test repeated target editing

def test_repeated_weekly_target_edit(
    app, client, weekly_activity, monkeypatch
):
    import app.goals as goals_module

    monkeypatch.setattr(
        goals_module,
        "tokyo_today",
        lambda: date(2026, 11, 25),
    )

    for target in [300, 240]:
        response = update_target(
            client, weekly_activity, target
        )

        assert response.status_code == 302

    with app.app_context():
        activity = db.session.get(
            Activity, weekly_activity
        )

        assert len(activity.target_versions) == 2

        assert activity.target_on(
            date(2026, 11, 29)
        ).target_value == 180

        assert activity.target_on(
            date(2026, 11, 30)
        ).target_value == 240

# Test cancellation of a pending target

def test_cancel_pending_weekly_target(
    app, client, weekly_activity, monkeypatch
):
    import app.goals as goals_module

    monkeypatch.setattr(
        goals_module,
        "tokyo_today",
        lambda: date(2026, 11, 25),
    )

    for target in [300, 180]:
        response = update_target(
            client, weekly_activity, target
        )

        assert response.status_code == 302

    with app.app_context():
        activity = db.session.get(
            Activity, weekly_activity
        )

        assert len(activity.target_versions) == 1

        assert activity.target_on(
            date(2026, 11, 30)
        ).target_value == 180


def update_daily_target(client, activity_id, target):
    return client.post(
        f"/goals/activities/{activity_id}/edit",
        data={
            "title": "Reading Books",
            "start_date": "2026-11-23",
            "measurement_type": "numeric",
            "frequency": "daily",
            "target_value": str(target),
            "unit": "pages",
        },
    )


def test_daily_target_effective_tomorrow(
    app, client, daily_activity, monkeypatch
):
    import app.goals as goals_module

    monkeypatch.setattr(
        goals_module,
        "tokyo_today",
        lambda: date(2026, 11, 25),
    )

    response = update_daily_target(
        client, daily_activity, 20
    )

    assert response.status_code == 302

    with app.app_context():
        activity = db.session.get(
            Activity, daily_activity
        )

        assert len(activity.target_versions) == 2

        assert activity.target_on(
            date(2026, 11, 24)
        ).target_value == 10

        assert activity.target_on(
            date(2026, 11, 25)
        ).target_value == 10

        assert activity.target_on(
            date(2026, 11, 26)
        ).target_value == 20

        assert activity.target_versions[-1].effective_from == (
            date(2026, 11, 26)
        )
# Verify historical completion after editing


def test_daily_edit_preserves_historical_completion(
    app, client, daily_activity, monkeypatch
):
    import app.goals as goals_module
    from app.models import DailyEntry

    with app.app_context():
        db.session.add(
            DailyEntry(
                activity_id=daily_activity,
                entry_date=date(2026, 11, 24),
                value=10,
            )
        )

        db.session.commit()

    monkeypatch.setattr(
        goals_module,
        "tokyo_today",
        lambda: date(2026, 11, 25),
    )

    response = update_daily_target(
        client, daily_activity, 20
    )

    assert response.status_code == 302

    with app.app_context():
        activity = db.session.get(
            Activity, daily_activity
        )

        old_entry = DailyEntry.query.filter_by(
            activity_id=daily_activity,
            entry_date=date(2026, 11, 24),
        ).one()

        new_entry = DailyEntry(
            entry_date=date(2026, 11, 26),
            value=10,
        )

        assert old_entry.value == 10

        assert activity.completion_percentage(
            old_entry
        ) == 100

        assert activity.is_completed(old_entry) is True

        assert activity.completion_percentage(
            new_entry
        ) == 50

        assert activity.is_completed(new_entry) is False
