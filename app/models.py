from datetime import datetime, timezone

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from app import db, login_manager


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    created_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    goals = db.relationship(
        "Goal",
        back_populates="user",
        cascade="all, delete-orphan"
    )


    def set_password(self, password):
        self.password_hash = generate_password_hash(
            password,
            method="pbkdf2:sha256"
        )

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Goal(db.Model):
    __tablename__ = "goals"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text)

    category = db.Column(db.String(50))

    # Examples:
    # target, habit, project
    goal_type = db.Column(db.String(30), nullable=False)

    target_value = db.Column(db.Float)
    unit = db.Column(db.String(30))

    start_date = db.Column(db.Date, nullable=False)
    deadline = db.Column(db.Date)

    # active, paused, completed, archived
    status = db.Column(
        db.String(20),
        nullable=False,
        default="active"
    )

    created_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    user = db.relationship("User", back_populates="goals")

    activities = db.relationship(
        "Activity",
        back_populates="goal",
        cascade="all, delete-orphan"
    )


class Activity(db.Model):
    __tablename__ = "activities"

    id = db.Column(db.Integer, primary_key=True)
    start_date = db.Column(db.Date, nullable=False)

    goal_id = db.Column(
        db.Integer,
        db.ForeignKey("goals.id"),
        nullable=False
    )

    title = db.Column(db.String(150), nullable=False)

    # boolean, numeric, duration
    measurement_type = db.Column(db.String(30), nullable=False)

    target_value = db.Column(db.Float)
    unit = db.Column(db.String(30))

    # daily, weekly, custom
    frequency = db.Column(
        db.String(30),
        nullable=False,
        default="daily"
    )

    is_active = db.Column(
        db.Boolean,
        nullable=False,
        default=True
    )

    created_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    goal = db.relationship("Goal", back_populates="activities")

    daily_entries = db.relationship(
        "DailyEntry",
        back_populates="activity",
        cascade="all, delete-orphan"
    )

    def completion_percentage(self, entry):
        if entry is None:
            return 0

        if self.measurement_type == "boolean":
            return 100 if entry.value >= 1 else 0

        if not self.target_value or self.target_value <= 0:
            return 0

        percentage = (entry.value / self.target_value) * 100

        return min(round(percentage), 100)


    def is_completed(self, entry):
        return self.completion_percentage(entry) >= 100

    def is_scheduled_for(self, check_date):
        if check_date < self.start_date:
            return False

        if self.frequency == "daily":
            return True

        if self.frequency == "weekdays":
            return check_date.weekday() < 5

        if self.frequency == "weekends":
            return check_date.weekday() >= 5

        return False

    def current_streak(self, today=None):
        from datetime import date, timedelta

        if today is None:
            today = date.today()

        entries = {
            entry.entry_date: entry
            for entry in self.daily_entries
            if entry.entry_date <= today
        }

        streak = 0

        # If today is scheduled and completed, start from today.
        # Otherwise search backward for the most recent scheduled day.
        today_entry = entries.get(today)

        if (
            self.is_scheduled_for(today)
            and today_entry
            and self.is_completed(today_entry)
        ):
            check_date = today
        else:
            check_date = today - timedelta(days=1)

        while check_date >= self.start_date:

            # Unscheduled days neither count nor break the streak.
            if not self.is_scheduled_for(check_date):
                check_date -= timedelta(days=1)
                continue

            entry = entries.get(check_date)

            if not entry or not self.is_completed(entry):
                break

            streak += 1
            check_date -= timedelta(days=1)

        return streak

    def consistency(self, days=7, today=None):
        from datetime import date, timedelta

        if today is None:
            today = date.today()

        entries = {
            entry.entry_date: entry
            for entry in self.daily_entries
            if entry.entry_date <= today
        }

        today_entry = entries.get(today)

        # Include today only when today's scheduled target
        # has already been completed.
        if (
            self.is_scheduled_for(today)
            and today_entry
            and self.is_completed(today_entry)
        ):
            end_date = today
        else:
            end_date = today - timedelta(days=1)

        window_start = end_date - timedelta(days=days - 1)

        start_date = max(
            self.start_date,
            window_start
        )

        if end_date < start_date:
            return {
                "completed": 0,
                "eligible": 0,
                "percentage": 0
            }

        eligible = 0
        completed = 0

        check_date = start_date

        while check_date <= end_date:

            # Only scheduled days belong in the denominator.
            if self.is_scheduled_for(check_date):
                eligible += 1

                entry = entries.get(check_date)

                if entry and self.is_completed(entry):
                    completed += 1

            check_date += timedelta(days=1)

        percentage = (
            round((completed / eligible) * 100)
            if eligible
            else 0
        )

        return {
            "completed": completed,
            "eligible": eligible,
            "percentage": percentage
        }


class DailyEntry(db.Model):
    __tablename__ = "daily_entries"

    id = db.Column(db.Integer, primary_key=True)

    activity_id = db.Column(
        db.Integer,
        db.ForeignKey("activities.id"),
        nullable=False
    )

    # The day this progress actually belongs to.
    entry_date = db.Column(db.Date, nullable=False)

    value = db.Column(db.Float, nullable=False, default=0)

    created_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    activity = db.relationship(
        "Activity",
        back_populates="daily_entries"
    )

    __table_args__ = (
        db.UniqueConstraint(
            "activity_id",
            "entry_date",
            name="uq_activity_entry_date"
        ),
    )
