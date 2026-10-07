from datetime import date, datetime, timedelta

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user

from app.models import Goal, Activity, DailyEntry
from app import db


history_bp = Blueprint(
    "history",
    __name__,
    url_prefix="/history"
)


@history_bp.route("/")
@login_required
def index():
    today = date.today()

    date_raw = request.args.get("date")

    if date_raw:
        try:
            selected_date = datetime.strptime(
                date_raw,
                "%Y-%m-%d"
            ).date()
        except ValueError:
            selected_date = today
    else:
        selected_date = today

    # Future history is not allowed.
    if selected_date > today:
        selected_date = today

    activities = (
        Activity.query
        .filter(
            Activity.goal.has(
                user_id=current_user.id
            ),
            Activity.goal.has(
                Goal.start_date <= selected_date
            )
        )
        .all()
    )

    activity_ids = [
        activity.id
        for activity in activities
    ]

    entries = {}

    if activity_ids:
        daily_entries = (
            DailyEntry.query
            .filter(
                DailyEntry.activity_id.in_(activity_ids),
                DailyEntry.entry_date == selected_date
            )
            .all()
        )

        entries = {
            entry.activity_id: entry
            for entry in daily_entries
        }

        activities = [
            activity
            for activity in activities
            if activity.start_date <= selected_date
            and activity.is_scheduled_for(selected_date)
            and (activity.is_active or activity.id in entries)
        ]

    previous_date = selected_date - timedelta(days=1)

    next_date = (
        selected_date + timedelta(days=1)
        if selected_date < today
        else None
    )

    return render_template(
        "history/index.html",
        selected_date=selected_date,
        today=today,
        activities=activities,
        entries=entries,
        previous_date=previous_date,
        next_date=next_date
    )

@history_bp.route(
    "/activities/<int:activity_id>/entry/<entry_date>",
    methods=["POST"]
)
@login_required
def save_entry(activity_id, entry_date):
    today = date.today()

    try:
        selected_date = datetime.strptime(
            entry_date,
            "%Y-%m-%d"
        ).date()
    except ValueError:
        flash("Invalid date.", "danger")
        return redirect(url_for("history.index"))

    if selected_date > today:
        flash("Future progress cannot be recorded.", "danger")
        return redirect(url_for("history.index"))

    activity = (
        Activity.query
        .filter_by(id=activity_id)
        .filter(
            Activity.goal.has(
                user_id=current_user.id
            )
        )
        .first_or_404()
    )

    if selected_date < activity.goal.start_date:
        flash(
            "Progress cannot be recorded before the goal start date.",
            "danger"
        )
        return redirect(
            url_for(
                "history.index",
                date=selected_date.isoformat()
            )
        )

    if not activity.is_scheduled_for(selected_date):
        flash(
            "Progress cannot be recorded on a day when this activity is not scheduled.",
            "danger"
        )
        return redirect(
            url_for(
                "history.index",
                date=selected_date.isoformat()
            )
        )
    
    value_raw = request.form.get("value", "").strip()

    try:
        if activity.measurement_type == "boolean":
            value = 1.0
        else:
            value = float(value_raw)

            if value < 0:
                raise ValueError

    except ValueError:
        flash("Please enter a valid progress value.", "danger")
        return redirect(
            url_for(
                "history.index",
                date=selected_date.isoformat()
            )
        )

    entry = DailyEntry.query.filter_by(
        activity_id=activity.id,
        entry_date=selected_date
    ).first()

    if entry:
        entry.value = value
        message = "Entry updated successfully."
    else:
        entry = DailyEntry(
            activity_id=activity.id,
            entry_date=selected_date,
            value=value
        )

        db.session.add(entry)
        message = "Missing entry added successfully."

    db.session.commit()

    flash(message, "success")

    return redirect(
        url_for(
            "history.index",
            date=selected_date.isoformat()
        )
    )