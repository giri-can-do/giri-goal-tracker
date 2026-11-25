
from datetime import date

from app import db
from app.models import Activity, DailyEntry


def test_daily_to_weekly_transition(
    app, client, daily_activity, monkeypatch
):
    import app.goals as goals_module

    monkeypatch.setattr(
        goals_module,
        "tokyo_today",
        lambda: date(2026, 11, 25),
    )

    response = client.post(
        f"/goals/activities/{daily_activity}/edit",
        data={
            "title": "Reading Books",
            "start_date": "2026-11-23",
            "measurement_type": "numeric",
            "frequency": "weekly",
            "target_value": "70",
            "unit": "pages",
        },
    )

    assert response.status_code == 302

    with app.app_context():
        activity = db.session.get(
            Activity, daily_activity
        )

        assert len(activity.target_versions) == 2

        old_target = activity.target_on(
            date(2026, 11, 29)
        )

        new_target = activity.target_on(
            date(2026, 11, 30)
        )

        assert old_target.frequency == "daily"
        assert old_target.target_value == 10

        assert new_target.frequency == "weekly"
        assert new_target.target_value == 70

        assert new_target.effective_from == (
            date(2026, 11, 30)
        )

        old_entry = DailyEntry(
            entry_date=date(2026, 11, 24),
            value=10,
        )

        assert activity.is_completed(old_entry) is True

# Test weekly-to-daily transition

def test_weekly_to_daily_transition(
    app, client, weekly_activity, monkeypatch
):
    import app.goals as goals_module

    monkeypatch.setattr(
        goals_module,
        "tokyo_today",
        lambda: date(2026, 11, 25),
    )

    response = client.post(
        f"/goals/activities/{weekly_activity}/edit",
        data={
            "title": "Japanese Study",
            "start_date": "2026-11-23",
            "measurement_type": "duration",
            "frequency": "daily",
            "target_value": "30",
            "unit": "minutes",
        },
    )

    assert response.status_code == 302

    with app.app_context():
        activity = db.session.get(
            Activity, weekly_activity
        )

        assert len(activity.target_versions) == 2

        old_target = activity.target_on(
            date(2026, 11, 29)
        )

        new_target = activity.target_on(
            date(2026, 11, 30)
        )

        assert old_target.frequency == "weekly"
        assert old_target.target_value == 180

        assert new_target.frequency == "daily"
        assert new_target.target_value == 30

        assert new_target.effective_from == (
            date(2026, 11, 30)
        )

        new_entry = DailyEntry(
            entry_date=date(2026, 11, 30),
            value=30,
        )

        assert activity.is_completed(new_entry) is True

# Verify mixed-frequency Dashboard reporting


def test_dashboard_after_frequency_transition(
    app, client, weekly_activity, monkeypatch
):
    import app.dashboard as dashboard_module

    from app.models import ActivityTargetVersion

    with app.app_context():
        activity = db.session.get(
            Activity, weekly_activity
        )

        activity.frequency = "daily"
        activity.target_value = 30

        activity.target_versions.append(
            ActivityTargetVersion(
                effective_from=date(2026, 11, 30),
                frequency="daily",
                measurement_type="duration",
                target_value=30,
                unit="minutes",
            )
        )

        db.session.add_all([
            DailyEntry(
                activity_id=weekly_activity,
                entry_date=date(2026, 11, 25),
                value=180,
            ),
            DailyEntry(
                activity_id=weekly_activity,
                entry_date=date(2026, 11, 30),
                value=30,
            ),
        ])

        db.session.commit()

    monkeypatch.setattr(
        dashboard_module,
        "tokyo_today",
        lambda: date(2026, 11, 30),
    )

    monkeypatch.setattr(
        dashboard_module,
        "render_template",
        lambda template, **context: context,
    )

    response = client.get("/dashboard/")

    assert response.status_code == 200

    row = response.get_json()["reports"]["month"][0]

    assert row["total"] == 210

    assert row["weekly_due"] == 1
    assert row["weekly_done"] == 1

    assert row["daily_due"] == 1
    assert row["daily_done"] == 1

    assert row["open_week"] is None

