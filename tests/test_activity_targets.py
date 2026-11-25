
from app import db


def test_database_is_isolated(app):
    with app.app_context():
        assert app.config["TESTING"] is True
        assert db.engine.url.get_backend_name() == "sqlite"
        assert db.engine.url.database == ":memory:"


def test_application_starts(app):
    assert app is not None
    assert app.config["TESTING"] is True

# Test daily activity calculations
from datetime import date
from app.models import Activity, DailyEntry, ActivityTargetVersion
from app.calendar import monday


def test_daily_target_partial_completion():
    activity = Activity(
        measurement_type="numeric",
        frequency="daily",
        target_value=100,
    )

    entry = DailyEntry(
        entry_date=date(2026, 11, 25),
        value=50,
    )

    assert activity.completion_percentage(entry) == 50
    assert activity.is_completed(entry) is False


def test_daily_target_full_completion():
    activity = Activity(
        measurement_type="numeric",
        frequency="daily",
        target_value=100,
    )

    entry = DailyEntry(
        entry_date=date(2026, 11, 25),
        value=100,
    )

    assert activity.completion_percentage(entry) == 100
    assert activity.is_completed(entry) is True


def test_daily_target_overachievement():
    activity = Activity(
        measurement_type="numeric",
        frequency="daily",
        target_value=100,
    )

    entry = DailyEntry(
        entry_date=date(2026, 11, 25),
        value=150,
    )

    assert activity.completion_percentage(entry) == 100
    assert activity.is_completed(entry) is True
    assert entry.value == 150


def test_daily_target_without_entry():
    activity = Activity(
        measurement_type="numeric",
        frequency="daily",
        target_value=100,
    )

    assert activity.completion_percentage(None) == 0
    assert activity.is_completed(None) is False

# Test weekly calendar boundaries
def test_week_starts_on_monday():
    assert monday(date(2026, 11, 25)) == date(2026, 11, 23)


def test_sunday_and_monday_week_boundary():
    # Sunday belongs to the current week.
    assert monday(date(2026, 11, 29)) == date(2026, 11, 23)

    # Monday begins a new week.
    assert monday(date(2026, 11, 30)) == date(2026, 11, 30)

# Test historical target

def build_versioned_activity():
    activity = Activity(
        measurement_type="duration",
        frequency="weekly",
        target_value=300,
        unit="minutes",
        start_date=date(2026, 11, 16),
    )

    activity.target_versions = [
        ActivityTargetVersion(
            effective_from=date(2026, 11, 16),
            frequency="weekly",
            measurement_type="duration",
            target_value=180,
            unit="minutes",
        ),
        ActivityTargetVersion(
            effective_from=date(2026, 11, 30),
            frequency="weekly",
            measurement_type="duration",
            target_value=300,
            unit="minutes",
        ),
    ]

    return activity


def test_historical_target_is_preserved():
    activity = build_versioned_activity()

    target = activity.target_on(date(2026, 11, 20))

    assert target.target_value == 180


def test_future_target_does_not_apply_early():
    activity = build_versioned_activity()

    target = activity.target_on(date(2026, 11, 29))

    assert target.target_value == 180


def test_new_target_applies_on_effective_date():
    activity = build_versioned_activity()

    target = activity.target_on(date(2026, 11, 30))

    assert target.target_value == 300


def test_new_target_remains_effective():
    activity = build_versioned_activity()

    target = activity.target_on(date(2026, 12, 6))

    assert target.target_value == 300


def test_legacy_activity_without_target_versions():
    activity = Activity(
        measurement_type="numeric",
        frequency="daily",
        target_value=10,
    )

    target = activity.target_on(date(2026, 11, 25))

    assert target.target_value == 10
    assert target.frequency == "daily"
    assert target is activity

# Test historical daily completion

def test_historical_daily_completion():
    activity = Activity(
        measurement_type="numeric",
        frequency="daily",
        target_value=20,
        unit="pages",
    )

    activity.target_versions = [
        ActivityTargetVersion(
            effective_from=date(2026, 11, 16),
            frequency="daily",
            measurement_type="numeric",
            target_value=10,
            unit="pages",
        ),
        ActivityTargetVersion(
            effective_from=date(2026, 11, 25),
            frequency="daily",
            measurement_type="numeric",
            target_value=20,
            unit="pages",
        ),
    ]

    old_entry = DailyEntry(
        entry_date=date(2026, 11, 24),
        value=10,
    )

    new_entry = DailyEntry(
        entry_date=date(2026, 11, 25),
        value=10,
    )

    assert activity.completion_percentage(old_entry) == 100
    assert activity.is_completed(old_entry) is True

    assert activity.completion_percentage(new_entry) == 50
    assert activity.is_completed(new_entry) is False


# Add a boundary test

import pytest


@pytest.mark.parametrize(
    "value, expected",
    [
        (0, False),
        (5000, False),
        (9949, False),
        (9950, False),
        (9999, False),
        (10000, True),
        (10001, True),
    ],
)
def test_daily_completion_boundary(value, expected):
    activity = Activity(
        measurement_type="numeric",
        frequency="daily",
        target_value=10000,
        unit="steps",
    )

    entry = DailyEntry(
        entry_date=date(2026, 11, 25),
        value=value,
    )

    assert activity.is_completed(entry) is expected
