
from datetime import date

import pytest

from app import db
from app.models import DailyEntry


def add_entries(app, activity_id, entries):
    with app.app_context():
        for day, value in entries:
            db.session.add(
                DailyEntry(
                    activity_id=activity_id,
                    entry_date=day,
                    value=value,
                )
            )

        db.session.commit()


def get_dashboard(client, monkeypatch, today):
    import app.dashboard as dashboard_module

    monkeypatch.setattr(
        dashboard_module,
        "tokyo_today",
        lambda: today,
    )

    # Capture the Dashboard data before HTML rendering.
    monkeypatch.setattr(
        dashboard_module,
        "render_template",
        lambda template, **context: context,
    )

    response = client.get("/dashboard/")

    assert response.status_code == 200

    return response.get_json()["reports"]


@pytest.mark.parametrize("amount", [90, 180, 240])
def test_current_week_progress(
    app, client, weekly_activity, monkeypatch, amount
):
    add_entries(
        app,
        weekly_activity,
        [(date(2026, 11, 25), amount)],
    )

    reports = get_dashboard(
        client,
        monkeypatch,
        date(2026, 11, 25),
    )

    row = reports["week"][0]

    assert row["total"] == amount
    assert row["open_week"] == [amount, 180]
    assert row["weekly_due"] == 0
    assert row["weekly_done"] == 0
    assert row["daily_due"] == 0


def test_weekly_progress_resets_on_monday(
    app, client, weekly_activity, monkeypatch
):
    add_entries(
        app,
        weekly_activity,
        [(date(2026, 11, 29), 180)],
    )

    reports = get_dashboard(
        client,
        monkeypatch,
        date(2026, 11, 30),
    )

    row = reports["week"][0]

    assert row["total"] == 0
    assert row["open_week"] == [0, 180]


def test_completed_week_remains_in_monthly_report(
    app, client, weekly_activity, monkeypatch
):
    add_entries(
        app,
        weekly_activity,
        [
            (date(2026, 11, 23), 30),
            (date(2026, 11, 25), 60),
            (date(2026, 11, 27), 90),
        ],
    )

    reports = get_dashboard(
        client,
        monkeypatch,
        date(2026, 11, 30),
    )

    for period in ["month", "year"]:
        row = reports[period][0]

        assert row["total"] == 180
        assert row["weekly_due"] == 1
        assert row["weekly_done"] == 1
        assert row["open_week"] == [0, 180]

# Month-crossing completed week

def test_month_crossing_completed_week(
    app, client, weekly_activity, monkeypatch
):
    add_entries(
        app,
        weekly_activity,
        [
            (date(2026, 11, 30), 30),
            (date(2026, 12, 2), 60),
            (date(2026, 12, 4), 90),
        ],
    )

    reports = get_dashboard(
        client,
        monkeypatch,
        date(2026, 12, 7),
    )

    row = reports["month"][0]

    assert row["total"] == 150
    assert row["weekly_due"] == 1
    assert row["weekly_done"] == 1
    assert row["open_week"] == [0, 180]

# Month-crossing incomplete week

def test_month_crossing_incomplete_week(
    app, client, weekly_activity, monkeypatch
):
    add_entries(
        app,
        weekly_activity,
        [
            (date(2026, 11, 30), 30),
            (date(2026, 12, 2), 60),
        ],
    )

    reports = get_dashboard(
        client,
        monkeypatch,
        date(2026, 12, 7),
    )

    row = reports["month"][0]

    assert row["total"] == 60
    assert row["weekly_due"] == 1
    assert row["weekly_done"] == 0
    assert row["open_week"] == [0, 180]

# Year-crossing completed week

def test_year_crossing_completed_week(
    app, client, weekly_activity, monkeypatch
):
    add_entries(
        app,
        weekly_activity,
        [
            (date(2026, 12, 28), 60),
            (date(2027, 1, 1), 120),
        ],
    )

    reports = get_dashboard(
        client,
        monkeypatch,
        date(2027, 1, 4),
    )

    for period in ["month", "year"]:
        row = reports[period][0]

        assert row["total"] == 120
        assert row["weekly_due"] == 1
        assert row["weekly_done"] == 1
        assert row["open_week"] == [0, 180]

