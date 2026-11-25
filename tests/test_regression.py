
from datetime import date

import pytest

from app import db
from app.models import Activity, DailyEntry


@pytest.mark.parametrize(
    "path",
    [
        "/",
        "/goals/",
        "/dashboard/",
        "/dashboard/?view=week",
        "/dashboard/?view=month",
        "/dashboard/?view=year",
    ],
)
def test_authenticated_page_rendering(
    client, weekly_activity, monkeypatch, path
):
    import app.today as today_module
    import app.dashboard as dashboard_module

    for module in [today_module, dashboard_module]:
        monkeypatch.setattr(
            module,
            "tokyo_today",
            lambda: date(2026, 11, 25),
        )

    response = client.get(path)

    assert response.status_code == 200
    assert response.mimetype == "text/html"
    assert len(response.data) > 0



def test_incomplete_closed_week(
    app, client, weekly_activity, monkeypatch
):
    import app.dashboard as dashboard_module

    with app.app_context():
        db.session.add_all([
            DailyEntry(
                activity_id=weekly_activity,
                entry_date=date(2026, 11, 25),
                value=90,
            ),
            DailyEntry(
                activity_id=weekly_activity,
                entry_date=date(2026, 11, 30),
                value=45,
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

    assert row["total"] == 135
    assert row["weekly_due"] == 1
    assert row["weekly_done"] == 0
    assert row["open_week"] == [45, 180]

# Verify future activities cannot be checked in

def test_future_activity_check_in_rejected(
    app, client, weekly_activity, monkeypatch
):
    import app.today as today_module

    with app.app_context():
        activity = db.session.get(
            Activity, weekly_activity
        )

        activity.start_date = date(2026, 12, 7)

        activity.target_versions[0].effective_from = (
            date(2026, 12, 7)
        )

        db.session.commit()

    monkeypatch.setattr(
        today_module,
        "tokyo_today",
        lambda: date(2026, 11, 25),
    )

    response = client.post(
        f"/activities/{weekly_activity}/check-in",
        data={"value": "60"},
    )

    assert response.status_code == 302

    with app.app_context():
        assert DailyEntry.query.filter_by(
            activity_id=weekly_activity
        ).count() == 0

